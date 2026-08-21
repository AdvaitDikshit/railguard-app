"""
Unit tests for content-based image validation and EXIF sanitization.
"""
import io

import pytest
from PIL import Image

from app.validation import ValidationError, sanitize_image_bytes, validate_image_bytes


def _jpeg_bytes(size=(100, 80), exif_bytes=None) -> bytes:
    img = Image.new("RGB", size, color=(120, 100, 80))
    buf = io.BytesIO()
    if exif_bytes:
        img.save(buf, format="JPEG", exif=exif_bytes)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_accepts_real_jpeg():
    fmt = validate_image_bytes(_jpeg_bytes(), "photo.jpg")
    assert fmt == "JPEG"


def test_validate_rejects_empty_file():
    with pytest.raises(ValidationError):
        validate_image_bytes(b"", "photo.jpg")


def test_validate_rejects_non_image_bytes():
    with pytest.raises(ValidationError):
        validate_image_bytes(b"this is not an image", "photo.jpg")


def test_validate_rejects_content_extension_mismatch():
    png_bytes_with_jpg_name = io.BytesIO()
    Image.new("RGB", (10, 10)).save(png_bytes_with_jpg_name, format="PNG")
    with pytest.raises(ValidationError):
        validate_image_bytes(png_bytes_with_jpg_name.getvalue(), "photo.jpg")


def test_validate_rejects_disallowed_extension():
    with pytest.raises(ValidationError):
        validate_image_bytes(_jpeg_bytes(), "photo.exe")


def test_sanitize_strips_exif_gps_metadata():
    """
    Build a real JPEG with EXIF metadata baked in (as a phone camera
    would attach, including device identifiers and orientation), then
    confirm sanitize_image_bytes actually removes it before the file is
    ever written to disk. A real phone photo's EXIF GPSInfo IFD is what
    this closes the door on — using simple tags here since correctly
    hand-encoding a GPS IFD's rational-number format isn't the point of
    this test, only "does sanitize strip whatever EXIF is present".
    """
    img = Image.new("RGB", (60, 40))
    exif = img.getexif()
    exif[0x010F] = "TestPhone Inc."  # Make
    exif[0x0110] = "TestPhone 9"      # Model
    exif[0x0112] = 3                  # Orientation

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    raw = buf.getvalue()

    # Confirm the EXIF was actually embedded before sanitizing (sanity check).
    before = Image.open(io.BytesIO(raw)).getexif()
    assert len(before) > 0

    sanitized = sanitize_image_bytes(raw, "JPEG")
    after = Image.open(io.BytesIO(sanitized)).getexif()
    assert len(after) == 0


def test_sanitize_preserves_visual_orientation_before_dropping_it():
    """
    A photo tagged "rotate 90°" must still look rotated after EXIF is
    stripped — exif_transpose() must bake the rotation into the pixels
    themselves, not just discard it.
    """
    img = Image.new("RGB", (100, 50))  # wide rectangle
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation: rotate 270° / EXIF "6" = 90° CW display rotation
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())

    sanitized = sanitize_image_bytes(buf.getvalue(), "JPEG")
    result = Image.open(io.BytesIO(sanitized))
    # A 100x50 image with a 90°-class rotation applied becomes 50x100.
    assert result.size == (50, 100)
