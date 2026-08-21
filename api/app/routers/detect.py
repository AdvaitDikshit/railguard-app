"""
Stateless detection endpoint — mirrors the original /api/detect
behaviour (run the model, return the result, no persistence) but with
real file-content validation and no in-memory session dict.

Use this for a "try it" preview. Use /reports (reports.py) when the
result should be saved as a real, geotagged, persisted report.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from ..config import API_DIR, settings
from ..detector_service import get_detector
from ..ratelimit import limiter
from ..validation import ValidationError, sanitize_image_bytes, validate_image_bytes

router = APIRouter(prefix="/api", tags=["detect"])

TMP_DIR = API_DIR / "storage" / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/detect")
@limiter.limit(settings.rate_limit_detect)
async def api_detect(request: Request, file: UploadFile = File(...)):
    raw = await file.read()
    try:
        fmt = validate_image_bytes(raw, file.filename or "upload")
        sanitized = sanitize_image_bytes(raw, fmt)
    except ValidationError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    ext = Path(file.filename or "upload.jpg").suffix.lower()
    tmp_path = TMP_DIR / f"{uuid.uuid4().hex}{ext}"
    tmp_path.write_bytes(sanitized)

    try:
        detector = get_detector()
        result = detector.detect(str(tmp_path))
    except Exception as e:
        return JSONResponse({"error": f"Detection failed: {e}"}, status_code=500)
    finally:
        tmp_path.unlink(missing_ok=True)

    return result
