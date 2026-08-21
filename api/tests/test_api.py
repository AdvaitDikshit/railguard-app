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


def test_report_list_includes_location_for_map_view(client, sample_image_bytes):
    """GET /api/reports must carry lat/lng — the /map page's only data source."""
    client.post(
        "/api/reports",
        files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")},
        data={"lat": "18.5679", "lng": "73.9143"},
    )
    r = client.get("/api/reports")
    located = [x for x in r.json() if x["lat"] is not None]
    assert len(located) >= 1
    assert located[0]["lat"] == 18.5679
    assert located[0]["lng"] == 73.9143


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


# ── Duplicate detection ────────────────────────────────────────────

def _jpeg(color, size=(120, 90)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG")
    return buf.getvalue()


def test_near_identical_photo_at_same_location_is_flagged_duplicate(client):
    """The exact 'N people photograph the same crack' scenario."""
    first = client.post(
        "/api/reports",
        files={"file": ("a.jpg", _jpeg((110, 100, 90)), "image/jpeg")},
        data={"lat": "18.5679", "lng": "73.9143"},
    )
    assert first.json()["status"] == "submitted"
    assert first.json()["cluster_id"] is None
    leader_id = first.json()["id"]

    # A second, near-identical photo (same color, same scene) from a
    # nearby vantage point.
    second = client.post(
        "/api/reports",
        files={"file": ("b.jpg", _jpeg((112, 101, 89)), "image/jpeg")},
        data={"lat": "18.5680", "lng": "73.9144"},  # ~15m away
    )
    assert second.json()["status"] == "duplicate"
    assert second.json()["cluster_id"] == leader_id


def test_different_photo_far_away_is_not_flagged_duplicate(client):
    client.post(
        "/api/reports",
        files={"file": ("a.jpg", _jpeg((110, 100, 90)), "image/jpeg")},
        data={"lat": "18.5679", "lng": "73.9143"},
    )
    far_away = client.post(
        "/api/reports",
        files={"file": ("c.jpg", _jpeg((10, 200, 30)), "image/jpeg")},  # visually different
        data={"lat": "19.0760", "lng": "72.8777"},  # Mumbai — genuinely far
    )
    assert far_away.json()["status"] == "submitted"
    assert far_away.json()["cluster_id"] is None


def test_cluster_endpoint_lists_all_matched_reports(client):
    first = client.post(
        "/api/reports",
        files={"file": ("a.jpg", _jpeg((80, 80, 80)), "image/jpeg")},
        data={"lat": "18.50", "lng": "73.90"},
    )
    leader_id = first.json()["id"]
    second = client.post(
        "/api/reports",
        files={"file": ("b.jpg", _jpeg((82, 81, 79)), "image/jpeg")},
        data={"lat": "18.5001", "lng": "73.9001"},
    )
    dup_id = second.json()["id"]
    assert second.json()["cluster_id"] == leader_id

    # Fetching the cluster from EITHER member's id returns both.
    r = client.get(f"/api/reports/{leader_id}/cluster")
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert ids == {leader_id, dup_id}

    r2 = client.get(f"/api/reports/{dup_id}/cluster")
    assert {x["id"] for x in r2.json()} == {leader_id, dup_id}
