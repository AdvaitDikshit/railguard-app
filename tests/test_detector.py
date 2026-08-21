"""
Unit tests for detector.py's pure logic — the size categorization,
severity classification, and class-name normalization functions that
have already been changed twice this project (once to fix the
CRITICAL-skew from loose annotations, once to patch the 303-class
training bug's garbage labels). These exist specifically so a future
edit to that logic can't silently regress without a test failing.

Run from the project root:
    pytest tests/test_detector.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from detector import (  # noqa: E402
    categorise_size,
    classify_severity,
    normalize_class_name,
    CrackDetector,
    SIZE_LARGE,
    SIZE_MEDIUM,
    SIZE_SMALL,
)


# ── categorise_size ──────────────────────────────────────────────

def test_categorise_size_boundaries():
    assert categorise_size(SIZE_LARGE) == "large"
    assert categorise_size(SIZE_LARGE - 0.001) == "medium"
    assert categorise_size(SIZE_MEDIUM) == "medium"
    assert categorise_size(SIZE_MEDIUM - 0.001) == "small"
    assert categorise_size(SIZE_SMALL) == "small"
    assert categorise_size(SIZE_SMALL - 0.001) == "hairline"


def test_categorise_size_zero_and_full_image():
    assert categorise_size(0.0) == "hairline"
    assert categorise_size(1.0) == "large"


def test_categorise_size_regression_known_real_detection():
    """
    The exact real detection from the first live API test this session:
    area_frac=0.368 (36.8% of frame). Before the threshold recalibration
    this was misclassified "large" (old SIZE_LARGE=0.15) and drove a
    CRITICAL severity. After recalibration against the dataset's real
    box-size distribution it must be "small".
    """
    assert categorise_size(0.368) == "small"


# ── classify_severity ────────────────────────────────────────────

def test_classify_severity_no_detections():
    assert classify_severity([]) == "NO_CRACK"


def test_classify_severity_large_high_confidence_is_critical():
    dets = [{"confidence": 0.90, "size_cat": "large"}]
    assert classify_severity(dets) == "CRITICAL"


def test_classify_severity_hairline_low_confidence_is_low():
    dets = [{"confidence": 0.60, "size_cat": "hairline"}]
    assert classify_severity(dets) == "LOW"


def test_classify_severity_takes_worst_of_multiple_detections():
    dets = [
        {"confidence": 0.60, "size_cat": "hairline"},   # LOW
        {"confidence": 0.90, "size_cat": "large"},        # CRITICAL
    ]
    assert classify_severity(dets) == "CRITICAL"


def test_classify_severity_regression_known_real_detection():
    """Same real detection as above, post-recalibration: small size + 91% conf -> HIGH."""
    dets = [{"confidence": 0.909079372882843, "size_cat": "small"}]
    assert classify_severity(dets) == "HIGH"


# ── normalize_class_name ─────────────────────────────────────────

def test_normalize_class_name_known_real_classes():
    assert normalize_class_name(300, "crack") == "crack"
    assert normalize_class_name(301, "cracked") == "crack"
    assert normalize_class_name(299, "cacked") == "crack"
    assert normalize_class_name(298, "Defects") == "defect"
    assert normalize_class_name(302, "railway-gap") == "railway gap"


def test_normalize_class_name_garbage_placeholder_classes():
    """
    The 303-class training bug: classes 0-297 are meaningless numeric
    placeholders inherited from pre-merge source datasets. Never surface
    the raw garbage label to a user.
    """
    for garbage_id in (0, 1, 37, 150, 297):
        result = normalize_class_name(garbage_id, str(garbage_id))
        assert result == "possible defect"
        assert result != str(garbage_id)


# ── detect_video's tracking aggregation ──────────────────────────
#
# Tests the "collapse N frames of the same tracked crack into one
# defect" logic in isolation, by faking `model.track()`'s output —
# real video decoding isn't exercised here (that needs an actual video
# file + loaded model), but the aggregation is the part with real risk
# of a bug, and it's pure Python once you have per-frame boxes/ids.

class _FakeArray:
    """Minimal stand-in for a torch tensor's .cpu().numpy() chain."""
    def __init__(self, data):
        self._data = data

    def cpu(self):
        return self

    def numpy(self):
        import numpy as np
        return np.array(self._data)


class _FakeBoxes:
    def __init__(self, xyxy, conf, ids):
        self.xyxy = _FakeArray(xyxy)
        self.conf = _FakeArray(conf)
        self.id = _FakeArray(ids) if ids is not None else None


class _FakeResult:
    def __init__(self, xyxy, conf, ids, orig_shape=(480, 640)):
        self.boxes = _FakeBoxes(xyxy, conf, ids) if ids is not None else None
        self.orig_shape = orig_shape


def _make_detector_with_fake_model(frames):
    """A CrackDetector with __init__ (and its real YOLO load) skipped,
    model.track() replaced with a canned frame sequence."""
    from unittest.mock import MagicMock
    det = CrackDetector.__new__(CrackDetector)
    det.conf_threshold = 0.55
    det.model_path = "fake.pt"
    det.model = MagicMock()
    det.model.track.return_value = iter(frames)
    return det


def test_detect_video_collapses_repeated_track_into_one_defect(tmp_path, monkeypatch):
    """The same track_id=1 appears in 3 consecutive frames -> one unique defect."""
    frames = [
        _FakeResult(xyxy=[[10, 10, 60, 40]], conf=[0.70], ids=[1]),
        _FakeResult(xyxy=[[12, 11, 62, 41]], conf=[0.85], ids=[1]),  # best confidence
        _FakeResult(xyxy=[[11, 10, 61, 40]], conf=[0.60], ids=[1]),
    ]
    det = _make_detector_with_fake_model(frames)

    # cv2.VideoCapture on a bogus path safely reports 0s -> fps falls
    # back to the 30.0 default, no exception.
    fake_video = str(tmp_path / "fake.mp4")
    result = det.detect_video(fake_video)

    assert result["unique_defect_count"] == 1
    assert result["frames_analyzed"] == 3
    defect = result["detections"][0]
    assert defect["track_id"] == 1
    # The representative box/confidence is from the best-confidence sighting.
    assert defect["confidence"] == 0.85
    assert defect["bbox"] == [12, 11, 62, 41]
    assert defect["frame_count"] == 3


def test_detect_video_keeps_earliest_first_seen_timestamp(tmp_path):
    """first_seen_s must be the FIRST frame the track appeared in, even
    if a later frame has higher confidence and becomes the representative box."""
    frames = [
        _FakeResult(xyxy=[[10, 10, 60, 40]], conf=[0.60], ids=[1]),  # frame 0 -> t=0.0
        _FakeResult(xyxy=[[10, 10, 60, 40]], conf=[0.95], ids=[1]),  # frame 1 -> t=1/30
    ]
    det = _make_detector_with_fake_model(frames)
    result = det.detect_video(str(tmp_path / "fake.mp4"))
    assert result["detections"][0]["first_seen_s"] == 0.0
    assert result["detections"][0]["confidence"] == 0.95


def test_detect_video_distinguishes_separate_tracks():
    frames = [
        _FakeResult(xyxy=[[10, 10, 60, 40], [400, 300, 450, 340]], conf=[0.70, 0.80], ids=[1, 2]),
    ]
    det = _make_detector_with_fake_model(frames)
    result = det.detect_video("ignored.mp4")
    assert result["unique_defect_count"] == 2
    assert {d["track_id"] for d in result["detections"]} == {1, 2}


def test_detect_video_respects_max_frames_cap():
    frames = [_FakeResult(xyxy=[[0, 0, 10, 10]], conf=[0.6], ids=[1]) for _ in range(10)]
    det = _make_detector_with_fake_model(frames)
    result = det.detect_video("ignored.mp4", max_frames=3)
    # Breaks the frame AFTER hitting the cap (10 available frames, only
    # process up to the 4th before stopping).
    assert result["frames_analyzed"] == 4
    # `truncated` compares against real cv2 video metadata (total frame
    # count), which a fake/nonexistent path can't provide — not
    # meaningfully testable without a real video file, so not asserted
    # here. The cap behavior itself (frames_analyzed above) is what matters.


def test_detect_video_no_detections_is_no_crack_severity():
    frames = [_FakeResult(xyxy=[], conf=[], ids=None)]
    det = _make_detector_with_fake_model(frames)
    result = det.detect_video("ignored.mp4")
    assert result["unique_defect_count"] == 0
    assert result["severity"] == "NO_CRACK"
