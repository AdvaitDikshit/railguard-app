"""
Duplicate-report detection: if 50 people photograph the same physical
crack, the platform should recognize that as one defect with 50
corroborating reports, not 50 independent incidents (see the original
project audit's brief on this — it's the most conceptually novel piece
of the whole platform per the later competitive-analysis review).

Approach: perceptual similarity (a lightweight 64-bit average hash,
computed with PIL only — no new dependency) combined with GPS
proximity. Two reports are considered the same physical defect when:

  - both have GPS, they're within DUPLICATE_RADIUS_M of each other,
    AND their image hashes are within DUPLICATE_HASH_THRESHOLD bits
    of each other (loose photo-similarity — different framing/exposure
    of the same real crack is expected), OR
  - either is missing GPS, so location can't narrow candidates — fall
    back to hash-only matching, but with a much STRICTER threshold
    (STRICT_HASH_THRESHOLD) to keep the false-positive rate low when
    location can't corroborate the match.

This is deliberately a simple, explainable heuristic — not a learned
embedding model — appropriate for this project's scale and the value
of being able to explain *why* two reports were clustered.
"""
import io
import math
from typing import Optional

from PIL import Image
from sqlalchemy.orm import Session

from . import models

DUPLICATE_RADIUS_M = 75.0        # same defect, photographed from ~the same spot
DUPLICATE_HASH_THRESHOLD = 12     # out of 64 bits — loose, GPS corroborates
STRICT_HASH_THRESHOLD = 4         # out of 64 bits — tight, no GPS to corroborate


def compute_phash(image_bytes: bytes) -> str:
    """64-bit average hash: shrink to 8x8 grayscale, threshold against
    the mean, pack the bits. Returns a 16-char hex string."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, p in enumerate(pixels):
        if p >= avg:
            bits |= (1 << i)
    return f"{bits:016x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    return bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000.0  # meters
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def find_duplicate_of(
    db: Session,
    phash: str,
    lat: Optional[float],
    lng: Optional[float],
) -> Optional[models.Report]:
    """
    Returns the existing Report this new submission is a likely duplicate
    of, or None if it looks like a genuinely new defect. Only considers
    reports that aren't themselves already marked as duplicates of
    something else, so a cluster always resolves back to one leader.
    """
    candidates = (
        db.query(models.Report)
        .filter(models.Report.cluster_id.is_(None))  # only cluster leaders
        .all()
    )

    best_match = None
    best_distance = None

    for candidate in candidates:
        original_media = next((m for m in candidate.media if m.role == "original"), None)
        if not original_media or not original_media.phash:
            continue

        dist = hamming_distance(phash, original_media.phash)

        if lat is not None and lng is not None and candidate.location and candidate.location.lat is not None:
            geo_dist = haversine_m(lat, lng, candidate.location.lat, candidate.location.lng)
            if geo_dist > DUPLICATE_RADIUS_M or dist > DUPLICATE_HASH_THRESHOLD:
                continue
        else:
            # No GPS on one side or the other — hash-only, stricter bar.
            if dist > STRICT_HASH_THRESHOLD:
                continue

        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_match = candidate

    return best_match
