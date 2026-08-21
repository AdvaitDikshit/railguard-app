"""
Persisted report flow: submit → detect → store (Postgres) → later verify → PDF.

This is the core of the "no in-memory dict / no flat JSON file" upgrade —
every report, its detections, its GPS location, and its AI vs. engineering
severity now live in real DB rows.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_admin
from ..config import API_DIR, PROJECT_ROOT, settings
from ..database import get_db
from ..dedup import compute_phash, find_duplicate_of
from ..detector_service import get_detector
from ..pdf_service import build_report_pdf
from ..ratelimit import limiter
from ..validation import ValidationError, sanitize_image_bytes, validate_image_bytes

router = APIRouter(prefix="/api/reports", tags=["reports"])

UPLOAD_DIR = API_DIR / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# detector.py writes annotated frames into the *original* project's
# static/results directory (relative to its own file location) — reused
# as-is rather than duplicated.
ANNOTATED_DIR = PROJECT_ROOT / "static" / "results"


def _to_report_out(report: models.Report) -> schemas.ReportOut:
    original = next((m for m in report.media if m.role == "original"), None)
    annotated = next((m for m in report.media if m.role == "annotated"), None)
    return schemas.ReportOut(
        id=report.id,
        status=report.status,
        source=report.source,
        created_at=report.created_at,
        original_url=f"/media/uploads/{Path(original.storage_path).name}" if original else None,
        annotated_url=f"/media/results/{Path(annotated.storage_path).name}" if annotated else None,
        location=schemas.LocationOut.model_validate(report.location) if report.location else None,
        severity=schemas.SeverityOut.model_validate(report.severity) if report.severity else None,
        cluster_id=report.cluster_id,
        detections=[
            schemas.DetectionOut(
                class_name=d.class_name, confidence=d.confidence,
                bbox=[d.x1, d.y1, d.x2, d.y2], width_px=d.width_px,
                height_px=d.height_px, area_frac=d.area_frac, size_cat=d.size_cat,
            ) for d in report.detections
        ],
    )


@router.post("", response_model=schemas.ReportOut)
@limiter.limit(settings.rate_limit_report)
async def create_report(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form("upload"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    accuracy_m: Optional[float] = Form(None),
    location_source: Optional[str] = Form("gps"),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        fmt = validate_image_bytes(raw, file.filename or "upload")
        sanitized = sanitize_image_bytes(raw, fmt)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = Path(file.filename or "upload.jpg").suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = UPLOAD_DIR / stored_name
    # Store the sanitized (EXIF-stripped) bytes, never the original —
    # a phone photo's embedded GPS could otherwise leak a location
    # beyond whatever was explicitly submitted in the lat/lng fields.
    stored_path.write_bytes(sanitized)

    try:
        detector = get_detector()
        result = detector.detect(str(stored_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")

    # Duplicate check BEFORE creating this report's row, so the query
    # only sees previously-committed reports — see ../dedup.py for the
    # matching rule (GPS proximity + perceptual hash, or hash-only with
    # a stricter bar when either side lacks GPS).
    phash = compute_phash(sanitized)
    duplicate_of = find_duplicate_of(db, phash, lat, lng)

    report = models.Report(
        source=source,
        original_filename=file.filename,
        status="duplicate" if duplicate_of else "submitted",
        cluster_id=duplicate_of.id if duplicate_of else None,
    )
    db.add(report)
    db.flush()  # obtain report.id before attaching children

    db.add(models.Media(
        report_id=report.id, role="original", storage_path=str(stored_path),
        content_type=file.content_type, width=result["image_size"]["width"],
        height=result["image_size"]["height"], phash=phash,
    ))

    ann_rel = result["annotated_image"]  # e.g. "results/result_xxx.jpg"
    ann_path = PROJECT_ROOT / "static" / ann_rel
    if ann_path.exists():
        db.add(models.Media(report_id=report.id, role="annotated", storage_path=str(ann_path)))

    for d in result["detections"]:
        x1, y1, x2, y2 = d["bbox"]
        db.add(models.Detection(
            report_id=report.id, class_name=d["class_name"], confidence=d["confidence"],
            x1=x1, y1=y1, x2=x2, y2=y2, width_px=d["width_px"], height_px=d["height_px"],
            area_px=d["area_px"], area_frac=d["area_frac"], size_cat=d["size_cat"],
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
        ai_detection_count=result["detection_count"],
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
    return _to_report_out(report)


@router.get("", response_model=list[schemas.ReportSummaryOut])
def list_reports(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    reports = (
        db.query(models.Report)
        .order_by(models.Report.created_at.desc())
        .offset(offset).limit(min(limit, 200)).all()
    )
    out = []
    for r in reports:
        annotated = next((m for m in r.media if m.role == "annotated"), None)
        out.append(schemas.ReportSummaryOut(
            id=r.id, status=r.status, created_at=r.created_at,
            ai_severity=r.severity.ai_severity if r.severity else None,
            detection_count=r.severity.ai_detection_count if r.severity else None,
            annotated_url=f"/media/results/{Path(annotated.storage_path).name}" if annotated else None,
            lat=r.location.lat if r.location else None,
            lng=r.location.lng if r.location else None,
        ))
    return out


@router.get("/{report_id}", response_model=schemas.ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_report_out(report)


@router.get("/{report_id}/cluster", response_model=list[schemas.ReportSummaryOut])
def get_cluster(report_id: str, db: Session = Depends(get_db)):
    """
    All reports believed to be the same physical defect as this one —
    the report itself (whether it's the cluster leader or a duplicate of
    one), plus every other report that matched it. Lets a reviewer see
    "this crack has been reported 6 times" instead of 6 disconnected rows.
    """
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    leader_id = report.cluster_id or report.id
    siblings = (
        db.query(models.Report)
        .filter((models.Report.id == leader_id) | (models.Report.cluster_id == leader_id))
        .order_by(models.Report.created_at.asc())
        .all()
    )

    out = []
    for r in siblings:
        annotated = next((m for m in r.media if m.role == "annotated"), None)
        out.append(schemas.ReportSummaryOut(
            id=r.id, status=r.status, created_at=r.created_at,
            ai_severity=r.severity.ai_severity if r.severity else None,
            detection_count=r.severity.ai_detection_count if r.severity else None,
            annotated_url=f"/media/results/{Path(annotated.storage_path).name}" if annotated else None,
            lat=r.location.lat if r.location else None,
            lng=r.location.lng if r.location else None,
        ))
    return out


@router.post("/{report_id}/verify", response_model=schemas.SeverityOut, dependencies=[Depends(require_admin)])
def verify_report(report_id: str, body: schemas.VerifyIn, db: Session = Depends(get_db)):
    """
    Records a qualified human's engineering assessment. This is the ONLY
    write path for engineering_* fields — the AI pipeline never touches
    them, and this endpoint never touches ai_* fields. Gated by a single
    shared admin token (see ../auth.py) — a real user-account system
    would be overkill for this one endpoint at this project's scale.
    """
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.severity:
        raise HTTPException(status_code=409, detail="Report has no AI severity assessment yet")

    report.severity.engineering_severity = body.engineering_severity
    report.severity.engineering_notes = body.engineering_notes
    report.severity.verified_by = body.verified_by
    report.severity.verified_at = datetime.now(timezone.utc)
    if body.new_status:
        report.status = body.new_status
    else:
        report.status = "verified"

    db.commit()
    db.refresh(report.severity)
    return schemas.SeverityOut.model_validate(report.severity)


@router.get("/{report_id}/pdf")
@limiter.limit(settings.rate_limit_pdf)
def report_pdf(request: Request, report_id: str, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    original = next((m for m in report.media if m.role == "original"), None)
    annotated = next((m for m in report.media if m.role == "annotated"), None)

    pdf_bytes = build_report_pdf(
        report,
        Path(original.storage_path) if original else None,
        Path(annotated.storage_path) if annotated else None,
    )
    headers = {"Content-Disposition": f'attachment; filename="railguard-report-{report.id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
