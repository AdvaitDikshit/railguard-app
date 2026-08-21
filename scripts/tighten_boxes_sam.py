"""
Auto-tighten loose YOLO bounding boxes into pixel-accurate boxes using
SAM (Segment Anything) box-prompted segmentation.

Why: audit of dataset/merged/train/labels/*.txt showed a median training
box covering 65.7% of image area (86.5% of boxes span >50% of image
width) — the original Roboflow annotations are loose "crack is
somewhere in this region" boxes, not tight boxes around the crack
itself. This directly explains poor localization (low mAP50-95) and
skews the severity engine's size-based classification.

Approach: for each existing label, treat its loose box as a *prompt*
to SAM, which produces a pixel mask of the actual crack-like object
inside that region. The tight box is then derived from the mask's
true extent — SAM does the precision work; we don't hand-draw anything.

This script is READ-ONLY on the original dataset. It writes:
  - dataset/tighten_review/<split>/<name>_compare.jpg   (before/after visual)
  - dataset/tighten_review/<split>/<name>.txt            (proposed tightened YOLO label)
  - dataset/tighten_review/summary.csv                   (per-box before/after stats)

Nothing under dataset/merged/ is modified.

Usage (proof-of-concept sample):
    python scripts/tighten_boxes_sam.py --sample 20

Usage (full split):
    python scripts/tighten_boxes_sam.py --split train --all
"""
import argparse
import csv
import random
from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset" / "merged"
REVIEW_DIR = BASE_DIR / "dataset" / "tighten_review"


def yolo_to_xyxy(cx, cy, w, h, img_w, img_h):
    x1 = int((cx - w / 2) * img_w)
    y1 = int((cy - h / 2) * img_h)
    x2 = int((cx + w / 2) * img_w)
    y2 = int((cy + h / 2) * img_h)
    return max(0, x1), max(0, y1), min(img_w, x2), min(img_h, y2)


def xyxy_to_yolo(x1, y1, x2, y2, img_w, img_h):
    cx = ((x1 + x2) / 2) / img_w
    cy = ((y1 + y2) / 2) / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return cx, cy, w, h


def load_labels(label_path: Path):
    boxes = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text().strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls, cx, cy, w, h = parts[0], *map(float, parts[1:5])
        boxes.append((int(cls), cx, cy, w, h))
    return boxes


def pick_sample(split: str, n: int, seed: int = 0):
    labels_dir = DATASET_DIR / split / "labels"
    all_labels = sorted(labels_dir.glob("*.txt"))
    # Stratify roughly by first-box area so the sample spans the
    # small/medium/large range, not just whatever sorts first.
    scored = []
    for lp in all_labels:
        boxes = load_labels(lp)
        if not boxes:
            continue
        area = boxes[0][3] * boxes[0][4]
        scored.append((area, lp))
    scored.sort(key=lambda t: t[0])
    if not scored:
        return []
    step = max(1, len(scored) // n)
    picked = [scored[i][1] for i in range(0, len(scored), step)][:n]
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train", choices=["train", "valid", "test"])
    ap.add_argument("--sample", type=int, default=20, help="Number of images for a stratified proof-of-concept sample")
    ap.add_argument("--all", action="store_true", help="Process the entire split instead of a sample")
    ap.add_argument("--model", default="sam_b.pt", help="ultralytics SAM checkpoint (sam_b.pt, mobile_sam.pt, ...)")
    args = ap.parse_args()

    from ultralytics import SAM

    print(f"Loading SAM model: {args.model} (will download on first use if not cached)")
    sam = SAM(args.model)

    images_dir = DATASET_DIR / args.split / "images"
    labels_dir = DATASET_DIR / args.split / "labels"
    out_dir = REVIEW_DIR / args.split
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        label_paths = sorted(labels_dir.glob("*.txt"))
    else:
        label_paths = pick_sample(args.split, args.sample)

    print(f"Processing {len(label_paths)} labeled images from '{args.split}'")

    rows = []
    for i, lp in enumerate(label_paths, 1):
        stem = lp.stem
        img_path = None
        for ext in (".jpg", ".jpeg", ".png"):
            cand = images_dir / f"{stem}{ext}"
            if cand.exists():
                img_path = cand
                break
        if img_path is None:
            print(f"  [{i}/{len(label_paths)}] {stem}: image not found, skipping")
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        boxes = load_labels(lp)
        if not boxes:
            continue

        vis = img.copy()
        new_lines = []
        for cls, cx, cy, bw, bh in boxes:
            x1, y1, x2, y2 = yolo_to_xyxy(cx, cy, bw, bh, w, h)
            orig_area_frac = bw * bh

            # SAM box-prompted segmentation: the loose box is the prompt,
            # SAM returns a precise mask of what's actually inside it.
            result = sam(str(img_path), bboxes=[[x1, y1, x2, y2]], verbose=False)[0]

            tight_box = None
            if result.masks is not None and len(result.masks.data) > 0:
                mask = result.masks.data[0].cpu().numpy().astype(np.uint8)
                ys, xs = np.where(mask > 0)
                if len(xs) > 0:
                    tx1, tx2 = int(xs.min()), int(xs.max())
                    ty1, ty2 = int(ys.min()), int(ys.max())
                    tight_box = (tx1, ty1, tx2, ty2)

            # Original loose box: red
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(vis, f"orig {orig_area_frac:.0%}", (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

            if tight_box:
                tx1, ty1, tx2, ty2 = tight_box
                new_area_frac = ((tx2 - tx1) * (ty2 - ty1)) / (w * h)
                cv2.rectangle(vis, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
                cv2.putText(vis, f"tight {new_area_frac:.0%}", (tx1, min(h - 5, ty2 + 18)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                ncx, ncy, nbw, nbh = xyxy_to_yolo(tx1, ty1, tx2, ty2, w, h)
                new_lines.append(f"{cls} {ncx:.6f} {ncy:.6f} {nbw:.6f} {nbh:.6f}")
                rows.append([stem, orig_area_frac, new_area_frac])
            else:
                # SAM found nothing usable inside the prompt box — keep the
                # original box rather than silently dropping the label.
                new_lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                rows.append([stem, orig_area_frac, orig_area_frac])

        cv2.imwrite(str(out_dir / f"{stem}_compare.jpg"), vis)
        (out_dir / f"{stem}.txt").write_text("\n".join(new_lines) + "\n")
        print(f"  [{i}/{len(label_paths)}] {stem}: {len(boxes)} box(es) processed")

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REVIEW_DIR / "summary.csv"
    write_header = not summary_path.exists()
    with open(summary_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["image", "orig_area_frac", "tight_area_frac"])
        writer.writerows(rows)

    if rows:
        import statistics
        origs = [r[1] for r in rows]
        tights = [r[2] for r in rows]
        print("\n── Summary ──")
        print(f"Boxes processed        : {len(rows)}")
        print(f"Median original area   : {statistics.median(origs):.1%}")
        print(f"Median tightened area  : {statistics.median(tights):.1%}")
        print(f"Review images written to: {out_dir}")
        print(f"Summary CSV            : {summary_path}")


if __name__ == "__main__":
    main()
