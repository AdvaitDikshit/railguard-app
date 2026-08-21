"""
Heuristic scan for stock-photo watermark bars across the full dataset.

Trigger: one training image (C-58-_jpg.rf...) was found to carry a
visible Alamy watermark (black caption bar + "alamy" / "Image ID: ..."
/ "www.alamy.com" text) — a real dataset-licensing red flag. No OCR
engine is available in this environment (pytesseract needs a Tesseract
binary, not installed), so this uses a calibrated visual heuristic
instead of reading the watermark text directly:

A stock-site caption bar has three properties natural photo content
rarely has all three of at once:
  1. A hard, near-full-width horizontal edge (sharp cut, not a gradual
     shading transition) — `ratio` = peak row-gradient vs. the image's
     typical row-gradient.
  2. The band below that edge is close to a single solid color aside
     from thin text strokes — `flat_frac` = fraction of that band's
     pixels within 15 gray levels of its median.
  3. The band is a plausible caption-bar height (2-20% of image height),
     not the whole lower half of the photo.

Calibrated against 15 random non-watermarked images (including two with
strong natural horizontal edges) + the 1 known watermarked image: 0
false positives, 1/1 true positive. This is a heuristic shortlist for
HUMAN review, not a certain detector — false negatives (subtler
watermarks) are expected and this does not replace manually skimming
the dataset.

Usage:
    python scripts/scan_watermarks.py
"""
import csv
from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset" / "merged"
OUT_DIR = BASE_DIR / "dataset" / "watermark_scan"

RATIO_THRESHOLD = 4.0
FLAT_THRESHOLD = 0.55
BAND_MIN, BAND_MAX = 0.02, 0.20


def analyze(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dy = np.abs(np.diff(gray, axis=0))
    row_edge = dy.mean(axis=1)
    y0 = int(h * 0.75)
    region = row_edge[y0:]
    if len(region) == 0:
        return None
    peak_idx_local = int(np.argmax(region))
    peak_row = y0 + peak_idx_local
    typical = np.median(row_edge)
    ratio = float(region.max() / (typical + 1e-6))

    below = gray[peak_row:h, :]
    if below.size == 0:
        return None
    med = np.median(below)
    flat_frac = float((np.abs(below - med) < 15).mean())
    band_h = (h - peak_row) / h

    flagged = ratio > RATIO_THRESHOLD and flat_frac > FLAT_THRESHOLD and BAND_MIN < band_h < BAND_MAX
    return {"ratio": ratio, "flat_frac": flat_frac, "band_h": band_h, "flagged": flagged}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    flagged_count = 0
    total = 0

    for split in ("train", "valid", "test"):
        img_dir = DATASET_DIR / split / "images"
        if not img_dir.exists():
            continue
        paths = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.jpeg")) + sorted(img_dir.glob("*.png"))
        print(f"Scanning {split}: {len(paths)} images")
        for i, p in enumerate(paths, 1):
            r = analyze(p)
            total += 1
            if r is None:
                continue
            rows.append([split, p.name, r["ratio"], r["flat_frac"], r["band_h"], r["flagged"]])
            if r["flagged"]:
                flagged_count += 1
                dst = OUT_DIR / f"{split}__{p.name}"
                cv2.imwrite(str(dst), cv2.imread(str(p)))
            if i % 1000 == 0:
                print(f"  ...{i}/{len(paths)}")

    csv_path = OUT_DIR / "scan_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "filename", "ratio", "flat_frac", "band_h", "flagged"])
        writer.writerows(rows)

    print(f"\nTotal images scanned: {total}")
    print(f"Flagged for manual review: {flagged_count}")
    print(f"Flagged copies saved to: {OUT_DIR}")
    print(f"Full results CSV: {csv_path}")


if __name__ == "__main__":
    main()
