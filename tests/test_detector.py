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
