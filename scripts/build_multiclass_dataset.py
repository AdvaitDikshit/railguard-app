"""
Merges the existing single-class crack dataset with two newly-sourced
Roboflow datasets (surface defects: spalling/squat/shelling/flaking/
groove/broken-rail) into one unified multi-class YOLO dataset, then
re-splits the combined pool with the same leakage-safe, group-by-source
logic as scripts/fix_split_leakage.py — Roboflow's own pre-made splits
are not trusted here, since one of the sources (Kakashi's) has a
suspiciously lopsided train:valid:test ratio (4068:61:27) suggesting
its train split is mostly augmented copies of a much smaller set of
real photos, which is exactly the leakage failure mode fixed earlier
in this dataset's history.

Sources merged:
  1. dataset/merged                          — existing, box format, 1 class
  2. rail_defect_detection_v1 (Saeed)        — polygon format, 8 classes
  3. rail_surface_defects_v7 (Kakashi)       — box format, 8 classes

Unified class scheme (6 classes):
  0 crack        1 spalling     2 squat
  3 shelling     4 flaking      5 broken_rail

Dropped as non-defect / too ambiguous to be worth training on:
  Joints, Rails (location markers, not defects), Scars (unclear defect
  type, not something we set out to detect). Images whose only labels
  were dropped classes are kept as negative (background) examples with
  an empty label file, rather than discarded outright.

  'groove' was also tried and dropped: only 56 instances total across
  the whole pool, and a first pass put every single one in train with
  zero in valid/test — not enough data to train or even measure, so
  it's folded into the drop list rather than shipped as a class no one
  can verify.

Non-destructive: writes dataset/multiclass_pool/ (flat staging pool)
and dataset/merged_resplit_multiclass/ (final train/valid/test). None
of the three source directories are modified.

Usage:
    python scripts/build_multiclass_dataset.py
"""
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXTERNAL_DIR = Path(r"F:\railway track")  # the two new downloads live here, outside the repo

POOL_DIR = BASE_DIR / "dataset" / "multiclass_pool"
DST_DIR = BASE_DIR / "dataset" / "merged_resplit_multiclass"

SPLIT_RATIOS = {"train": 0.69, "valid": 0.20, "test": 0.11}
SEED = 42

CLASSES = ["crack", "spalling", "squat", "shelling", "flaking", "broken_rail"]
CLASS_ID = {name: i for i, name in enumerate(CLASSES)}

# ── Per-source class remap: source class name -> unified class name, or
#    None to drop the class entirely (image kept as background if that
#    was its only label). ────────────────────────────────────────────
SOURCES = [
    {
        "tag": "crackset",
        "root": BASE_DIR / "dataset" / "merged",
        "names": ["crack"],  # source data.yaml order, id-indexed
        "remap": {"crack": "crack"},
        "format": "box",
    },
    {
        "tag": "saeed",
        "root": EXTERNAL_DIR / "rail_defect_detection_v1",
        "names": ["Cracks", "Flakings", "Grooves", "Joints", "Putus", "Shellings", "Spallings", "Squats"],
        "remap": {
            "Cracks": "crack", "Flakings": "flaking", "Grooves": None,
            "Joints": None, "Putus": "broken_rail", "Shellings": "shelling",
            "Spallings": "spalling", "Squats": "squat",
        },
        "format": "polygon",
    },
    {
        "tag": "kakashi",
        "root": EXTERNAL_DIR / "rail_surface_defects_v7",
        "names": ["Cracks", "Flaking", "Rails", "Scars", "Shelling", "Spalling", "Squat", "breaks"],
        "remap": {
            "Cracks": "crack", "Flaking": "flaking", "Rails": None, "Scars": None,
            "Shelling": "shelling", "Spalling": "spalling", "Squat": "squat", "breaks": "broken_rail",
        },
        "format": "box",
    },
]

PATTERN = re.compile(r'^(.*?)(?:_jpg)?\.rf\.[0-9a-f]+\.(jpg|jpeg|png)$', re.IGNORECASE)


def source_basename(filename: str) -> str:
    m = PATTERN.match(filename)
    return m.group(1) if m else filename


def polygon_to_box(coords: list[float]) -> tuple[float, float, float, float]:
    """coords = [x1,y1,x2,y2,...] normalized -> (cx, cy, w, h) normalized."""
    xs = coords[0::2]
    ys = coords[1::2]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w = x_max - x_min
    h = y_max - y_min
    return cx, cy, w, h


def convert_label_file(src_path: Path, source_names: list[str], remap: dict, fmt: str) -> list[str]:
    """Read one source label file, remap classes, convert format. Returns
    new label lines (unified class ids); may be shorter than input if
    some lines' classes were dropped, or empty if all were dropped."""
    out_lines = []
    if not src_path.exists():
        return out_lines
    for line in src_path.read_text().splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        cls_id = int(parts[0])
        if cls_id >= len(source_names):
            continue  # malformed/unexpected id, skip defensively
        src_class_name = source_names[cls_id]
        unified_name = remap.get(src_class_name)
        if unified_name is None:
            continue  # dropped class
        new_id = CLASS_ID[unified_name]
        nums = [float(x) for x in parts[1:]]
        if fmt == "polygon":
            if len(nums) < 6 or len(nums) % 2 != 0:
                continue  # not a valid polygon (need >=3 points)
            cx, cy, w, h = polygon_to_box(nums)
        else:
            if len(nums) != 4:
                continue
            cx, cy, w, h = nums
        out_lines.append(f"{new_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return out_lines


def build_pool():
    for sub in ("images", "labels"):
        (POOL_DIR / sub).mkdir(parents=True, exist_ok=True)

    stats = defaultdict(int)
    class_counts = defaultdict(int)

    for source in SOURCES:
        root = source["root"]
        if not root.exists():
            print(f"  SKIP (not found): {root}")
            continue
        for split in ("train", "valid", "test"):
            img_dir = root / split / "images"
            lbl_dir = root / split / "labels"
            if not img_dir.exists():
                continue
            for img_path in img_dir.glob("*"):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue
                new_lines = convert_label_file(
                    lbl_dir / f"{img_path.stem}.txt", source["names"], source["remap"], source["format"]
                )
                # Prefix with source tag so basename-grouping never collides
                # across datasets, and so we can trace provenance later.
                new_name = f"{source['tag']}__{img_path.name}"
                dst_img = POOL_DIR / "images" / new_name
                shutil.copy2(img_path, dst_img)
                dst_lbl = POOL_DIR / "labels" / f"{Path(new_name).stem}.txt"
                dst_lbl.write_text("\n".join(new_lines) + ("\n" if new_lines else ""))

                stats[source["tag"]] += 1
                for line in new_lines:
                    class_counts[CLASSES[int(line.split()[0])]] += 1

    print("Pooled images per source:", dict(stats))
    print("Instance counts per class (pool-wide):", dict(class_counts))
    return stats


def resplit_pool():
    groups = defaultdict(list)
    for img_path in (POOL_DIR / "images").glob("*"):
        base = source_basename(img_path.name)
        groups[base].append(img_path)

    group_keys = list(groups.keys())
    random.Random(SEED).shuffle(group_keys)
    n = len(group_keys)
    n_train = round(n * SPLIT_RATIOS["train"])
    n_valid = round(n * SPLIT_RATIOS["valid"])
    assignment = {}
    for i, key in enumerate(group_keys):
        assignment[key] = "train" if i < n_train else ("valid" if i < n_train + n_valid else "test")

    for split in ("train", "valid", "test"):
        (DST_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (DST_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    counts = {"train": 0, "valid": 0, "test": 0}
    for base, imgs in groups.items():
        target = assignment[base]
        for img_path in imgs:
            shutil.copy2(img_path, DST_DIR / target / "images" / img_path.name)
            lbl_path = POOL_DIR / "labels" / f"{img_path.stem}.txt"
            shutil.copy2(lbl_path, DST_DIR / target / "labels" / lbl_path.name)
            counts[target] += 1

    data_yaml = DST_DIR / "data.yaml"
    names_repr = ", ".join(f"'{c}'" for c in CLASSES)
    data_yaml.write_text(
        "train: ../train/images\n"
        "val: ../valid/images\n"
        "test: ../test/images\n\n"
        f"nc: {len(CLASSES)}\n"
        f"names: [{names_repr}]\n"
    )

    print(f"\nUnique source images (groups): {len(group_keys)}")
    print(f"Files written per split: {counts}")
    print(f"data.yaml: {data_yaml}")

    # ── leakage check ──────────────────────────────────────────
    check = defaultdict(set)
    for split in ("train", "valid", "test"):
        for img_path in (DST_DIR / split / "images").glob("*"):
            check[source_basename(img_path.name)].add(split)
    leaked = {b: s for b, s in check.items() if len(s) > 1}
    print(f"Leakage check: {len(leaked)} source(s) crossing splits (should be 0)")


def main():
    print("=== Building pooled multi-class dataset ===")
    build_pool()
    print("\n=== Re-splitting pool (leakage-safe, group-by-source) ===")
    resplit_pool()


if __name__ == "__main__":
    main()
