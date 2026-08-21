"""
Video upload -> tracked detection -> temporal aggregation -> persisted
report. Reuses detector.py's CrackDetector.detect_video() directly,
same reuse pattern as the image flow in reports.py.

IMPORTANT — this runs SYNCHRONOUSLY inside the request. A real
production deployment should queue this (Redis/RQ or similar) rather
than block a request thread for the duration of video processing —
this project doesn't have that infrastructure yet, so it's a documented
simplification, not an oversight. The hard `max_video_frames` cap
(config.py) exists specifically to bound how long any single request
can take without a queue in front of it.

Also not yet built: duplicate-clustering for video reports (dedup.py
was designed around single-image perceptual hashing) and PDF export
for video reports (pdf_service.py expects a single before/after image
pair, not a multi-timestamp video summary). Both are natural follow-ups
once there's real usage to justify the effort.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import API_DIR, PROJECT_ROOT, settings
from ..database import get_db
from ..detector_service import get_detector
from ..ratelimit import limiter
from ..validation import (
    ValidationError,
    validate_video_extension_and_size,
    validate_video_file,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])

VIDEO_DIR = API_DIR / "storage" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def _to_video_report_out(report: models.Report) -> schemas.VideoReportOut:
    video_media = next((m for m in report.media if m.role == "video"), None)
    return schemas.VideoReportOut(
        id=report.id,
        status=report.status,
        created_at=report.created_at,
        video_url=f"/media/videos/{Path(video_media.storage_path).name}" if video_media else None,
        duration_s=video_media.duration_s if video_media else None,
        fps=video_media.fps if video_media else None,
        frames_analyzed=video_media.frames_analyzed if video_media else None,
        location=schemas.LocationOut.model_validate(report.location) if report.location else None,
        severity=schemas.SeverityOut.model_validate(report.severity) if report.severity else None,
        detections=[
            schemas.VideoDetectionOut(
                track_id=d.track_id, class_name=d.class_name, confidence=d.confidence,
                bbox=[d.x1, d.y1, d.x2, d.y2], size_cat=d.size_cat,
                first_seen_s=d.frame_ts or 0.0, frame_count=1,
            ) for d in report.detections
        ],
    )


@router.post("", response_model=schemas.VideoReportOut)
@limiter.limit(settings.rate_limit_video)
async def create_video_report(
    request: Request,
    file: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    accuracy_m: Optional[float] = Form(None),
    location_source: Optional[str] = Form("gps"),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        validate_video_extension_and_size(raw, file.filename or "upload", settings.max_video_mb)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = Path(file.filename or "upload.mp4").suffix.lower()
    stored_path = VIDEO_DIR / f"{uuid.uuid4().hex}{ext}"
    stored_path.write_bytes(raw)

    try:
        validate_video_file(stored_path)
    except ValidationError as e:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    try:
        detector = get_detector()
        result = detector.detect_video(str(stored_path), max_frames=settings.max_video_frames)
    except Exception as e:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {e}")

    report = models.Report(source="video", original_filename=file.filename)
    db.add(report)
    db.flush()

    db.add(models.Media(
        report_id=report.id, role="video", storage_path=str(stored_path),
        content_type=file.content_type,
        duration_s=result["duration_s"], fps=result["fps"],
        frames_analyzed=result["frames_analyzed"],
    ))

    for d in result["detections"]:
        x1, y1, x2, y2 = d["bbox"]
        db.add(models.Detection(
            report_id=report.id, class_name=d["class_name"], confidence=d["confidence"],
            x1=x1, y1=y1, x2=x2, y2=y2, width_px=d["width_px"], height_px=d["height_px"],
            area_px=d["area_px"], area_frac=d["area_frac"], size_cat=d["size_cat"],
            track_id=d["track_id"], frame_ts=d["first_seen_s"],
        ))

    if lat is not None and lng is not None:
        db.add(models.Location(
            report_id=report.id, lat=lat, lng=lng, accuracy_m=accuracy_m,
            source=location_source, captured_at=datetime.now(timezone.utc),
        ))

    adv = result["advisory"]
    profile = result["crack_profile"]
    db.add(models.SeverityAssessment(
        report_id=report.id,
        ai_severity=result["severity"],
        ai_max_confidence=profile.get("max_conf", 0.0),
        ai_detection_count=result["unique_defect_count"],
        ai_heading=adv.get("heading"),
        ai_risk_summary=adv.get("risk_summary"),
        ai_actions=adv.get("actions"),
        ai_timeline=adv.get("timeline"),
        ai_authority=adv.get("authority"),
        ai_model_path=result["model_used"],
        ai_conf_threshold=result["conf_threshold"],
    ))

    db.commit()
    db.refresh(report)
    return _to_video_report_out(report)


@router.get("", response_model=list[schemas.VideoSummaryOut])
def list_video_reports(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    reports = (
        db.query(models.Report)
        .filter(models.Report.source == "video")
        .order_by(models.Report.created_at.desc())
        .offset(offset).limit(min(limit, 200)).all()
    )
    out = []
    for r in reports:
        video_media = next((m for m in r.media if m.role == "video"), None)
        out.append(schemas.VideoSummaryOut(
            id=r.id, status=r.status, created_at=r.created_at,
            ai_severity=r.severity.ai_severity if r.severity else None,
            duration_s=video_media.duration_s if video_media else None,
            unique_defect_count=r.severity.ai_detection_count if r.severity else None,
        ))
    return out


@router.get("/{report_id}", response_model=schemas.VideoReportOut)
def get_video_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if not report or report.source != "video":
        raise HTTPException(status_code=404, detail="Video report not found")
    return _to_video_report_out(report)
