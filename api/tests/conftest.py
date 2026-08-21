"""
Shared pytest fixtures for the API test suite.

Stubs out `detector.CrackDetector` so tests don't need torch/ultralytics/
the trained weights, and uses a throwaway SQLite DB per test session
instead of Postgres — matching the project's own documented "SQLite for
local testing" path (see api/README.md).

IMPORTANT: PROJECT_ROOT (which contains app.py, a Flask module) must
NOT be added to sys.path before `api.app` is imported, or `app.py`
shadows the `api/app/` package — this bit a manual smoke test earlier
in the project's history. detector_service.py adds PROJECT_ROOT itself
at the correct point (after api.app is already resolving).
"""
import io
import os
import sys
import types
from pathlib import Path

import pytest
from PIL import Image

API_DIR = Path(__file__).parent.parent
PROJECT_ROOT = API_DIR.parent

# A real (throwaway) sqlite FILE, not :memory: — an in-memory sqlite DB
# is tied to a single connection, and SQLAlchemy's default pool opens a
# new connection per request, so different requests would each see an
# empty DB. Deleted and recreated fresh at the start of each test run.
TEST_DB_PATH = API_DIR / "tests" / "_pytest_railguard.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH.as_posix()}")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
# Rate limits key off remote address, and TestClient's requests all
# share one address — the real per-minute limits would make a full
# test run flaky (hitting 429 partway through), so raise them here only.
os.environ.setdefault("RATE_LIMIT_DETECT", "1000/minute")
os.environ.setdefault("RATE_LIMIT_REPORT", "1000/minute")
os.environ.setdefault("RATE_LIMIT_PDF", "1000/minute")

sys.path.insert(0, str(API_DIR))


def _install_stub_detector():
    """Replace the real detector module with a lightweight stand-in."""
    if "detector" in sys.modules:
        return
    fake_module = types.ModuleType("detector")

    class FakeCrackDetector:
        def __init__(self, model_path=None, conf_threshold=0.55):
            self.model_path = "yolov8n.pt (test stub)"
            self.conf_threshold = conf_threshold

        def detect(self, image_path):
            img = Image.open(image_path)
            w, h = img.size
            results_dir = PROJECT_ROOT / "static" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            ann_name = "result_pytest_stub.jpg"
            img.convert("RGB").save(results_dir / ann_name)
            return {
                "id": "pytesttestid01",
                "timestamp": "2026-01-01T00:00:00",
                "original_image": str(image_path),
                "annotated_image": f"results/{ann_name}",
                "image_size": {"width": w, "height": h},
                "severity": "HIGH",
                "detections": [{
                    "class_id": 0, "class_name": "possible defect", "confidence": 0.81,
                    "bbox": [10, 10, 100, 40], "width_px": 90, "height_px": 30,
                    "area_px": 2700, "area_frac": 0.05, "size_cat": "small",
                }],
                "detection_count": 1,
                "advisory": {
                    "icon": "", "color": "#e67e22",
                    "heading": "HIGH — test advisory heading",
                    "risk_summary": "Test risk summary.",
                    "actions": ["Test action one.", "Test action two."],
                    "timeline": "Test timeline.",
                    "authority": "Test authority.",
                },
                "crack_profile": {"count": 1, "size_cat": "small", "max_conf": 0.81,
                                   "max_area_pct": 5.0, "max_width_px": 90, "max_height_px": 30},
                "model_used": "yolov8n.pt (test stub)",
                "conf_threshold": self.conf_threshold,
            }

    fake_module.CrackDetector = FakeCrackDetector
    sys.modules["detector"] = fake_module


_install_stub_detector()

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    # The sqlite FILE persists across the whole test session (see the
    # :memory: connection-pooling note above) — without an explicit
    # wipe here, later tests would see earlier tests' rows. That was
    # harmless before, but duplicate-detection logic (dedup.py) is
    # exactly the kind of test that depends on starting from nothing.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_image_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (200, 150), color=(80, 80, 80)).save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()
