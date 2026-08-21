"""
Content-based image validation.

The original app.py only checked the *filename extension*
(`Path(f).suffix.lower() in ALLOWED_EXT`). That accepts anything an
attacker names "photo.jpg" regardless of what bytes are actually inside
it. This module decodes the file and verifies the real image format,
which is what "file-content validation" means in practice for a public
upload endpoint.
"""

import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .config import settings

# Maps the *actual decoded format* PIL reports to the extensions we
# consider consistent with it. A .jpg that decodes as PNG bytes (or
# vice versa) is rejected, not silently accepted.
FORMAT_TO_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "BMP": {".bmp"},
    "TIFF": {".tif", ".tiff"},
    "WEBP": {".webp"},
}


class ValidationError(ValueError):
    pass


def validate_image_bytes(raw: bytes, filename: str) -> str:
    """
    Returns the verified PIL format string (e.g. "JPEG") on success.
    Raises ValidationError with a user-facing message on failure.
    """
    if not raw:
        raise ValidationError("Uploaded file is empty.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValidationError(f"File exceeds the {settings.max_upload_mb}MB upload limit.")

    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extension_set:
        raise ValidationError(f"File extension '{ext}' is not an accepted image type.")

    # First pass: verify() checks structural integrity without fully
    # decoding pixel data (catches truncated/corrupt files cheaply).
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ValidationError(f"File is not a readable image: {e}") from e

    # verify() invalidates the file object for further use — reopen to
    # read the actual decoded format and confirm it fully decodes.
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        fmt = img.format
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ValidationError(f"File could not be decoded as an image: {e}") from e

    if fmt not in FORMAT_TO_EXTENSIONS:
        raise ValidationError(f"Detected image format '{fmt}' is not supported.")

    if ext not in FORMAT_TO_EXTENSIONS[fmt]:
        raise ValidationError(
            f"File extension '{ext}' does not match its actual content ({fmt}). "
            "This is rejected as a mislabeled/spoofed upload."
        )

    return fmt
