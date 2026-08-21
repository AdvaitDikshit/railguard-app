"""
Unit tests for the duplicate-detection heuristic (app/dedup.py) —
pure-function tests, no API/DB involved.
"""
import io

from PIL import Image

from app.dedup import compute_phash, hamming_distance, haversine_m


def _image_bytes(color, size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _checkerboard_bytes(offset=0, size=(64, 64)):
    """
    A non-uniform pattern — a flat solid color is a degenerate case for
    average-hash (every pixel equals the mean by construction, so a
    solid black and solid white image both hash to all-1-bits; this
    isn't a real-world problem since actual photographs have texture,
    but it does mean tests need non-uniform images to be meaningful).
    """
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            on = ((x // 8) + (y // 8) + offset) % 2 == 0
            px[x, y] = (200, 200, 200) if on else (20, 20, 20)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_identical_images_have_zero_hamming_distance():
    a = compute_phash(_checkerboard_bytes())
    b = compute_phash(_checkerboard_bytes())
    assert hamming_distance(a, b) == 0


def test_very_different_images_have_large_hamming_distance():
    pattern_a = compute_phash(_checkerboard_bytes(offset=0))
    pattern_b = compute_phash(_checkerboard_bytes(offset=1))  # inverted checkerboard
    assert hamming_distance(pattern_a, pattern_b) > 20


def test_haversine_same_point_is_zero():
    assert haversine_m(18.5679, 73.9143, 18.5679, 73.9143) == 0


def test_haversine_known_distance_roughly_correct():
    # Two points ~1.1km apart (roughly 0.01 degrees latitude at this latitude).
    d = haversine_m(18.5679, 73.9143, 18.5779, 73.9143)
    assert 900 < d < 1300


def test_phash_is_16_char_hex():
    h = compute_phash(_image_bytes((50, 60, 70)))
    assert len(h) == 16
    int(h, 16)  # raises if not valid hex
