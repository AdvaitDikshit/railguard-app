"""
Dataset Downloader for Railway Crack Detection
Downloads and merges multiple datasets from Roboflow
FIXED: handles zip download manually to avoid SDK unzip bug
"""

import os
import sys
import shutil
import yaml
import zipfile
import requests
from pathlib import Path
from roboflow import Roboflow

# ─────────────────────────────────────────────────────────────
ROBOFLOW_API_KEY = "RL4YEU2i3GZafb3nrHZl"

DATASETS = [
    {
        "workspace":   "advaits-workspace",
        "project":     "railway-crack",
        "version":     1,
        "description": "Railway Track Defects"
    },
    # Add more datasets here if needed
]

BASE_DIR    = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset"
MERGED_DIR  = DATASET_DIR / "merged"
# ─────────────────────────────────────────────────────────────


def download_and_extract(ds: dict) -> Path | None:
    """Download a Roboflow dataset as a zip and extract it manually."""
    rf      = Roboflow(api_key=ROBOFLOW_API_KEY)
    project = rf.workspace(ds["workspace"]).project(ds["project"])
    version = project.version(ds["version"])

    dest_dir = DATASET_DIR / f"{ds['project']}_v{ds['version']}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    zip_path = dest_dir / "dataset.zip"

    # ── try SDK download first ───────────────────────────────────
    try:
        print(f"    Trying SDK download…")
        version.download("yolov8", location=str(dest_dir), overwrite=True)
        # if we get here and there are images, SDK worked
        if any(dest_dir.rglob("*.jpg")) or any(dest_dir.rglob("*.png")):
            print(f"      SDK download succeeded")
            return dest_dir
    except Exception as e:
        print(f"    SDK failed ({e}), trying direct zip download…")

    # ── fallback: get the download URL from the API and fetch zip ─
    try:
        # Roboflow export API endpoint
        url = (
            f"https://api.roboflow.com/{ds['workspace']}/{ds['project']}"
            f"/{ds['version']}/yolov8"
            f"?api_key={ROBOFLOW_API_KEY}"
        )
        print(f"    Fetching export URL…")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        export_link = (
            data.get("export", {}).get("link")
            or data.get("link")
        )
        if not export_link:
            print(f"      No export link in response: {list(data.keys())}")
            return None

        print(f"    Downloading zip…")
        with requests.get(export_link, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"    Extracting zip…")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(dest_dir)

        zip_path.unlink(missing_ok=True)
        print(f"      Extracted to {dest_dir}")
        return dest_dir

    except Exception as e:
        print(f"      Direct download also failed: {e}")
        return None


def merge_datasets(paths: list[Path]):
    """Merge multiple YOLOv8 datasets into one unified dataset."""
    print(f"\n  Merging {len(paths)} dataset(s) into {MERGED_DIR}")

    splits = ["train", "valid", "test"]
    for split in splits:
        for sub in ["images", "labels"]:
            (MERGED_DIR / split / sub).mkdir(parents=True, exist_ok=True)

    all_classes: list[str] = []
    class_maps:  list[dict] = []

    for path in paths:
        yaml_file = next(path.glob("data.yaml"), None) or next(path.glob("*.yaml"), None)
        if yaml_file is None:
            print(f"    No YAML found in {path}, skipping")
            class_maps.append({})
            continue

        with open(yaml_file) as f:
            cfg = yaml.safe_load(f)

        ds_classes = cfg.get("names", [])
        if isinstance(ds_classes, dict):
            ds_classes = [ds_classes[k] for k in sorted(ds_classes)]

        local_map = {}
        for local_id, name in enumerate(ds_classes):
            norm = name.lower().replace(" ", "_")
            if norm not in all_classes:
                all_classes.append(norm)
            local_map[local_id] = all_classes.index(norm)

        class_maps.append(local_map)
        print(f"    {path.name}: {ds_classes}")

    print(f"\n   Unified classes: {all_classes}")

    file_counter = {s: 0 for s in splits}

    for path, cmap in zip(paths, class_maps):
        for split in splits:
            img_dir = path / split / "images"
            lbl_dir = path / split / "labels"
            if not img_dir.exists():
                img_dir = path / split
            if not img_dir.exists():
                continue

            for img_path in img_dir.glob("*.*"):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                    continue

                file_counter[split] += 1
                stem    = f"{path.name}_{img_path.stem}"
                dst_img = MERGED_DIR / split / "images" / f"{stem}{img_path.suffix}"
                shutil.copy2(img_path, dst_img)

                src_lbl = (lbl_dir / img_path.stem).with_suffix(".txt")
                if not src_lbl.exists():
                    src_lbl = (path / split / img_path.stem).with_suffix(".txt")

                dst_lbl = MERGED_DIR / split / "labels" / f"{stem}.txt"
                if src_lbl.exists() and cmap:
                    lines    = src_lbl.read_text().splitlines()
                    remapped = []
                    for line in lines:
                        if line.strip():
                            parts  = line.split()
                            new_id = cmap.get(int(parts[0]), int(parts[0]))
                            remapped.append(f"{new_id} {' '.join(parts[1:])}")
                    dst_lbl.write_text("\n".join(remapped))
                elif src_lbl.exists():
                    shutil.copy2(src_lbl, dst_lbl)

    print(f"\n  Files — train:{file_counter['train']}  "
          f"valid:{file_counter['valid']}  test:{file_counter['test']}")

    data_yaml_content = {
        "path":  str(MERGED_DIR),
        "train": "train/images",
        "val":   "valid/images",
        "test":  "test/images",
        "nc":    len(all_classes),
        "names": all_classes,
    }
    out_yaml = MERGED_DIR / "data.yaml"
    with open(out_yaml, "w") as f:
        yaml.dump(data_yaml_content, f, default_flow_style=False)

    print(f"  Merged YAML: {out_yaml}")
    return out_yaml


if __name__ == "__main__":
    print("═" * 60)
    print("  Railway Crack Detection — Dataset Downloader (Fixed)")
    print("═" * 60)

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []

    for ds in DATASETS:
        print(f"\n  {ds['description']}  ({ds['workspace']}/{ds['project']} v{ds['version']})")
        path = download_and_extract(ds)
        if path:
            downloaded.append(path)

    if downloaded:
        merge_datasets(downloaded)
        print("\n  Done! Run:  python scripts/train_model.py")
    else:
        print("\n  No datasets downloaded.")
        print("\n── MANUAL OPTION ──────────────────────────────────────")
        print("1. Go to https://universe.roboflow.com")
        print("2. Find your dataset → Versions → Export Dataset")
        print("3. Choose YOLOv8 format → Download zip")
        print("4. Extract the zip into:  dataset/railway-crack_v1/")
        print("   So the structure is:   dataset/railway-crack_v1/train/images/")
        print("5. Then run:  python scripts/train_model.py  (skipping this script)")