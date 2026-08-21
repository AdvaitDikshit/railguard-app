"""
API integration tests for the video pipeline. detector.detect_video()
is stubbed (conftest.py) with a canned two-track result — real
video-frame tracking is covered separately by tests/test_detector.py's
aggregation tests. What's under test here is the API/DB wiring: does a
real (tiny) video pass content validation, get persisted correctly,
and come back out with the right shape.
"""


def test_video_report_rejects_bad_extension(client, sample_video_bytes):
    r = client.post("/api/videos", files={"file": ("clip.exe", sample_video_bytes, "video/mp4")})
    assert r.status_code == 400


def test_video_report_rejects_non_video_content(client):
    r = client.post("/api/videos", files={"file": ("clip.mp4", b"not a real video", "video/mp4")})
    assert r.status_code == 400


def test_create_video_report(client, sample_video_bytes):
    r = client.post(
        "/api/videos",
        files={"file": ("clip.mp4", sample_video_bytes, "video/mp4")},
        data={"lat": "18.5679", "lng": "73.9143"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "submitted"
    assert body["duration_s"] == 12.5
    assert body["frames_analyzed"] == 375
    assert body["severity"]["ai_severity"] == "HIGH"
    assert body["severity"]["ai_detection_count"] == 2
    assert body["location"]["lat"] == 18.5679
    assert body["video_url"] is not None

    # Temporal aggregation carried through: two distinct tracked
    # defects, each with its own first-seen timestamp — not one row
    # per raw frame.
    dets = body["detections"]
    assert len(dets) == 2
    assert {d["track_id"] for d in dets} == {1, 2}
    first = next(d for d in dets if d["track_id"] == 1)
    assert first["first_seen_s"] == 2.1


def test_video_report_appears_in_video_list(client, sample_video_bytes):
    create = client.post("/api/videos", files={"file": ("clip.mp4", sample_video_bytes, "video/mp4")})
    report_id = create.json()["id"]
    r = client.get("/api/videos")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert report_id in ids


def test_get_video_report_by_id(client, sample_video_bytes):
    create = client.post("/api/videos", files={"file": ("clip.mp4", sample_video_bytes, "video/mp4")})
    report_id = create.json()["id"]
    r = client.get(f"/api/videos/{report_id}")
    assert r.status_code == 200
    assert r.json()["id"] == report_id


def test_get_video_report_404_for_unknown_id(client):
    r = client.get("/api/videos/does-not-exist")
    assert r.status_code == 404


def test_image_report_not_returned_by_video_endpoint(client, sample_image_bytes):
    """A GET /api/videos/{id} for an *image* report's id should 404,
    not accidentally return an image report through the video schema."""
    create = client.post("/api/reports", files={"file": ("t.jpg", sample_image_bytes, "image/jpeg")})
    image_report_id = create.json()["id"]
    r = client.get(f"/api/videos/{image_report_id}")
    assert r.status_code == 404


def test_video_report_reachable_via_existing_verify_endpoint(client, sample_video_bytes):
    """/verify is generic over any report id, including video reports —
    no separate verify endpoint needed for video."""
    create = client.post("/api/videos", files={"file": ("clip.mp4", sample_video_bytes, "video/mp4")})
    report_id = create.json()["id"]

    r = client.post(
        f"/api/reports/{report_id}/verify",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"engineering_severity": "MODERATE", "engineering_notes": "Reviewed footage.", "verified_by": "J. Rao"},
    )
    assert r.status_code == 200
    assert r.json()["engineering_severity"] == "MODERATE"
    assert r.json()["ai_severity"] == "HIGH"
