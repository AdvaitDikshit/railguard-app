"""
Moves every image flagged by scan_watermarks.py (dataset/watermark_scan/
scan_results.csv, flagged=True) out of the active train/valid/test
folders into dataset/removed_watermarked/<split>/{images,labels}/.

This is a MOVE, not a delete — nothing is destroyed. If a flagged image
turns out to be a false positive on manual inspection, it can be moved
back. The active dataset/merged/ folders (what data.yaml points to)
end up with the flagged images stripped out, which is what actually
matters for retraining.

Usage:
    python scripts/quarantine_watermarks.py
"""
import csv
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset" / "merged"
SCAN_CSV = BASE_DIR / "dataset" / "watermark_scan" / "scan_results.csv"
QUARANTINE_DIR = BASE_DIR / "dataset" / "removed_watermarked"


def main():
    if not SCAN_CSV.exists():
        raise SystemExit(f"Scan results not found: {SCAN_CSV}. Run scripts/scan_watermarks.py first.")

    moved = 0
    missing = 0
    by_split = {}

    with open(SCAN_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["flagged"] != "True":
                continue
            split = row["split"]
            filename = row["filename"]
            stem = Path(filename).stem

            img_src = DATASET_DIR / split / "images" / filename
            lbl_src = DATASET_DIR / split / "labels" / f"{stem}.txt"

            img_dst_dir = QUARANTINE_DIR / split / "images"
            lbl_dst_dir = QUARANTINE_DIR / split / "labels"
            img_dst_dir.mkdir(parents=True, exist_ok=True)
            lbl_dst_dir.mkdir(parents=True, exist_ok=True)

            if img_src.exists():
                shutil.move(str(img_src), str(img_dst_dir / filename))
                moved += 1
            else:
                missing += 1
                continue

            if lbl_src.exists():
                shutil.move(str(lbl_src), str(lbl_dst_dir / f"{stem}.txt"))

            by_split[split] = by_split.get(split, 0) + 1

    print(f"Moved {moved} images (+ matching labels) to {QUARANTINE_DIR}")
    if missing:
        print(f"  ({missing} listed images were already missing — skipped)")
    for split, count in by_split.items():
        print(f"  {split}: {count}")

    for split in ("train", "valid", "test"):
        remaining = len(list((DATASET_DIR / split / "images").glob("*")))
        print(f"  {split} remaining images: {remaining}")


if __name__ == "__main__":
    main()
