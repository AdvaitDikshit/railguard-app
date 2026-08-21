"""
Second attempt at auto-tightening loose boxes: classical edge/line
detection instead of SAM.

SAM (tighten_boxes_sam.py) failed for this domain — it segments salient
*objects* (rail, ballast), not thin low-contrast surface cracks, so its
masks filled the entire prompt box instead of isolating the crack line.

This script instead looks for the crack's actual signature: a thin,
elongated, locally-darker/brighter linear discontinuity. Within each
existing loose box, it runs Canny edge detection + finds the bounding
region of the strongest connected edge structure, which is a much more
crack-appropriate prior than "segment the salient object."

Still read-only on dataset/merged/. Writes to dataset/tighten_review/.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from tighten_boxes_sam import (
    BASE_DIR, DATASET_DIR, REVIEW_DIR,
    yolo_to_xyxy, xyxy_to_yolo, load_labels, pick_sample,
)


def find_crack_region(gray_crop: np.ndarray):
    """Returns (x1,y1,x2,y2) tight box around the strongest edge cluster, or None."""
    blur = cv2.GaussianBlur(gray_crop, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)

    # Dilate slightly so a broken/thin crack line becomes one connected
    # component instead of many tiny fragments.
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    h, w = gray_crop.shape[:2]
    crop_area = h * w

    # Score contours by "crack-likeness": elongated (high aspect ratio
    # extent) but not so large it's basically the whole crop (that would
    # just be picking up rail/sleeper edges again).
    best = None
    best_score = -1
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        area_frac = area / crop_area
        if area_frac > 0.6 or area_frac < 0.001:
            continue  # too big (probably structure) or noise speck
        elongation = max(cw, ch) / max(1, min(cw, ch))
        score = elongation * (1 - area_frac)  # prefer elongated + smaller
        if score > best_score:
            best_score = score
            best = (x, y, x + cw, y + ch)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train", choices=["train", "valid", "test"])
    ap.add_argument("--sample", type=int, default=20)
    args = ap.parse_args()

    images_dir = DATASET_DIR / args.split / "images"
    labels_dir = DATASET_DIR / args.split / "labels"
    out_dir = REVIEW_DIR / f"{args.split}_edges"
    out_dir.mkdir(parents=True, exist_ok=True)

    label_paths = pick_sample(args.split, args.sample)
    print(f"Processing {len(label_paths)} labeled images from '{args.split}' (edge-based)")

    orig_areas, new_areas = [], []
    for i, lp in enumerate(label_paths, 1):
        stem = lp.stem
        img_path = None
        for ext in (".jpg", ".jpeg", ".png"):
            cand = images_dir / f"{stem}{ext}"
            if cand.exists():
                img_path = cand
                break
        if img_path is None:
            continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        boxes = load_labels(lp)
        if not boxes:
            continue

        vis = img.copy()
        for cls, cx, cy, bw, bh in boxes:
            x1, y1, x2, y2 = yolo_to_xyxy(cx, cy, bw, bh, w, h)
            orig_area_frac = bw * bh
            crop = gray[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            region = find_crack_region(crop)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(vis, f"orig {orig_area_frac:.0%}", (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

            if region:
                rx1, ry1, rx2, ry2 = region
                tx1, ty1, tx2, ty2 = x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2
                new_area_frac = ((tx2 - tx1) * (ty2 - ty1)) / (w * h)
                cv2.rectangle(vis, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
                cv2.putText(vis, f"tight {new_area_frac:.0%}", (tx1, min(h - 5, ty2 + 18)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                orig_areas.append(orig_area_frac)
                new_areas.append(new_area_frac)
            else:
                cv2.putText(vis, "no edge region found", (x1, y2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        cv2.imwrite(str(out_dir / f"{stem}_compare.jpg"), vis)
        print(f"  [{i}/{len(label_paths)}] {stem}")

    if orig_areas:
        import statistics
        print("\n── Summary (edge-based) ──")
        print(f"Boxes with a candidate region: {len(orig_areas)}")
        print(f"Median original area  : {statistics.median(orig_areas):.1%}")
        print(f"Median tightened area : {statistics.median(new_areas):.1%}")
    print(f"Review images: {out_dir}")


if __name__ == "__main__":
    main()
