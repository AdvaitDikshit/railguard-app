"""
Rebuilds train/valid/test so that no single source photograph's
Roboflow-generated augmented copies end up split across more than one
of train/valid/test.

Trigger: audit found 32.1% of the 1,824 unique source images in
dataset/merged have augmented copies (same basename before the
Roboflow `.rf.<hash>` suffix) scattered across ≥2 splits — meaning the
existing validation/test metrics are inflated by near-duplicate leakage,
not a genuine measure of generalization.

Approach: group every image+label pair by source basename, shuffle
GROUPS (not individual files) with a fixed seed for reproducibility,
and assign each group's files entirely to one split — targeting the
same ~69/20/10 proportions as the original split, measured by group
count (not file count, since group sizes vary 1-7x).

Non-destructive: writes a NEW dataset/merged_resplit/ directory by
copying files. dataset/merged/ is untouched. Point a training run at
dataset/merged_resplit/data.yaml to use the leak-free split.

Usage:
    python scripts/fix_split_leakage.py
"""
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "dataset" / "merged"
DST_DIR = BASE_DIR / "dataset" / "merged_resplit"

SPLIT_RATIOS = {"train": 0.69, "valid": 0.20, "test": 0.11}
SEED = 42

PATTERN = re.compile(r'^(.*?)(?:_jpg)?\.rf\.[0-9a-f]+\.(jpg|jpeg|png)$', re.IGNORECASE)


def source_basename(filename: str) -> str:
    m = PATTERN.match(filename)
    return m.group(1) if m else filename


def collect_groups():
    """Map source basename -> list of (split, stem, image_path, label_path)."""
    groups = defaultdict(list)
    for split in ("train", "valid", "test"):
        img_dir = SRC_DIR / split / "images"
        lbl_dir = SRC_DIR / split / "labels"
        if not img_dir.exists():
            continue
        for img_path in img_dir.glob("*"):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            stem = img_path.stem
            label_path = lbl_dir / f"{stem}.txt"
            base = source_basename(img_path.name)
            groups[base].append((split, stem, img_path, label_path))
    return groups


def assign_splits(group_keys):
    random.Random(SEED).shuffle(group_keys)
    n = len(group_keys)
    n_train = round(n * SPLIT_RATIOS["train"])
    n_valid = round(n * SPLIT_RATIOS["valid"])
    assignment = {}
    for i, key in enumerate(group_keys):
        if i < n_train:
            assignment[key] = "train"
        elif i < n_train + n_valid:
            assignment[key] = "valid"
        else:
            assignment[key] = "test"
    return assignment


def main():
    groups = collect_groups()
    group_keys = list(groups.keys())
    assignment = assign_splits(group_keys)

    for split in ("train", "valid", "test"):
        (DST_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (DST_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    counts = {"train": 0, "valid": 0, "test": 0}
    for base, entries in groups.items():
        target_split = assignment[base]
        for orig_split, stem, img_path, label_path in entries:
            dst_img = DST_DIR / target_split / "images" / img_path.name
            shutil.copy2(img_path, dst_img)
            if label_path.exists():
                dst_lbl = DST_DIR / target_split / "labels" / f"{stem}.txt"
                shutil.copy2(label_path, dst_lbl)
            counts[target_split] += 1

    data_yaml = DST_DIR / "data.yaml"
    data_yaml.write_text(
        "train: ../train/images\n"
        "val: ../valid/images\n"
        "test: ../test/images\n\n"
        "nc: 1\n"
        "names: ['crack']\n"
    )

    print(f"Unique source images (groups): {len(group_keys)}")
    print(f"Files written per split: {counts}")
    print(f"Total files: {sum(counts.values())}")
    print(f"New dataset root: {DST_DIR}")
    print(f"data.yaml: {data_yaml}")

    # ── sanity check: confirm zero leakage in the new split ──────
    check = defaultdict(set)
    for split in ("train", "valid", "test"):
        for img_path in (DST_DIR / split / "images").glob("*"):
            check[source_basename(img_path.name)].add(split)
    leaked = {b: s for b, s in check.items() if len(s) > 1}
    print(f"\nLeakage check on new split: {len(leaked)} source(s) crossing splits (should be 0)")


if __name__ == "__main__":
    main()
