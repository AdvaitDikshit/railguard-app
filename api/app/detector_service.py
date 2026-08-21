"""
Thin singleton wrapper around the existing, unmodified `detector.py`
(CrackDetector) at the project root. We do not re-implement the YOLO /
severity logic here — the trained model and the size/severity rules in
detector.py are proven and reused as-is, only wrapped behind a real API.
"""

import sys

from .config import PROJECT_ROOT, settings

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from detector import CrackDetector  # noqa: E402  (import after sys.path insert, same pattern as scripts/predict.py)

_detector = None


def get_detector() -> CrackDetector:
    global _detector
    if _detector is None:
        model_path = settings.model_path or None
        _detector = CrackDetector(model_path=model_path, conf_threshold=settings.conf_threshold)
    return _detector
