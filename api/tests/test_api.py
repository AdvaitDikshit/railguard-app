"""
API integration tests — end-to-end through the real FastAPI app, real
SQLAlchemy models, real PDF generation, with only the YOLO model itself
stubbed out (see conftest.py). This is the same flow that was
hand-verified via Swagger UI during development; committing it as a
real test means that verification survives future changes.

Run from api/:
    pytest tests/ -v
"""
import io

from PIL import Image


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_detect_accepts_valid_image(client, sample_image_bytes):
    r = client.post("/api/detect", files={"file": ("track.jpg", sample_image_bytes, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["severity"] == "HIGH"


def test_detect_rejects_non_image_content(client):
    r = client.post("/api/detect", files={"file": ("evil.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400


def test_detect_rejects_extension_content_mismatch(client):
    """A PNG's real bytes with a .jpg extension — content-based validation, not just suffix."""
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, format="PNG")
    r = client.post("/api/detect", files={"file": ("fake.jpg", buf.getvalue(), "image/jpeg")})
    assert r.status_code == 400


def test_create_report_with_gps(client, sample_image_bytes):
    r = client.post(
        "/api/reports",
        files={"file": ("track.jpg", sample_image_bytes, "image/jpeg")},
        data={"source": "camera", "lat": "18.5679", "lng": "73.9143", "accuracy_m": "12.5"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["location"]["lat"] == 18.5679
    assert body["location"]["lng"] == 73.9143
    assert body["severity"]["ai_severity"] == "HIGH"
    # Never auto-populate the human field from the AI pipeline.
    assert body["severity"]["engineering_severity"] is None
    assert body["annotated_url"] is not None


def test_report_appears_in_list(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]
    r = client.get("/api/reports")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert report_id in ids


def test_get_report_by_id(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]
    r = client.get(f"/api/reports/{report_id}")
    assert r.status_code == 200
    assert r.json()["id"] == report_id
    assert len(r.json()["detections"]) == 1


def test_get_report_404_for_unknown_id(client):
    r = client.get("/api/reports/does-not-exist")
    assert r.status_code == 404


# ── /verify: auth + AI/human separation ───────────────────────────

def test_verify_requires_admin_token(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]

    r = client.post(f"/api/reports/{report_id}/verify", json={
        "engineering_severity": "LOW", "engineering_notes": "x", "verified_by": "tester",
    })
    assert r.status_code == 401


def test_verify_rejects_wrong_admin_token(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]

    r = client.post(
        f"/api/reports/{report_id}/verify",
        headers={"X-Admin-Token": "wrong-token"},
        json={"engineering_severity": "LOW", "engineering_notes": "x", "verified_by": "tester"},
    )
    assert r.status_code == 401


def test_verify_with_correct_token_sets_engineering_fields_only(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]
    original_ai_severity = create.json()["severity"]["ai_severity"]

    r = client.post(
        f"/api/reports/{report_id}/verify",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"engineering_severity": "MODERATE", "engineering_notes": "Field-confirmed.", "verified_by": "J. Rao"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["engineering_severity"] == "MODERATE"
    assert body["verified_by"] == "J. Rao"
    # The AI pipeline's own assessment must never be overwritten by a human verification.
    assert body["ai_severity"] == original_ai_severity == "HIGH"


def test_verify_404_for_unknown_report(client):
    r = client.post(
        "/api/reports/does-not-exist/verify",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"engineering_severity": "LOW", "engineering_notes": "x", "verified_by": "tester"},
    )
    assert r.status_code == 404


# ── PDF ─────────────────────────────────────────────────────────

def test_report_pdf_is_a_real_pdf(client, sample_image_bytes):
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    report_id = create.json()["id"]

    r = client.get(f"/api/reports/{report_id}/pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000
