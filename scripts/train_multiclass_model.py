"""
YOLOv8 Training Script for the multi-class defect model (crack, spalling,
squat, shelling, flaking, broken_rail) — see scripts/build_multiclass_dataset.py
for how dataset/merged_resplit_multiclass/ was built.

Deliberately a separate script/output from train_model.py rather than a
flag on it: this trains a different model (models/best_multiclass_detector.pt)
so the existing single-class crack model stays intact and comparable —
we specifically want to check per-class metrics against the crack-only
baseline afterward, not silently replace it.

Run this after scripts/build_multiclass_dataset.py.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml
from ultralytics import YOLO

BASE_DIR    = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset" / "merged_resplit_multiclass"
MODELS_DIR  = BASE_DIR / "models"

CONFIG = {
    "model":          "yolov8s.pt",
    "epochs":         100,
    "imgsz":          640,
    "batch":          -1,
    "patience":       20,
    "lr0":            0.01,
    "lrf":            0.01,
    "momentum":       0.937,
    "weight_decay":   0.0005,
    "warmup_epochs":  3,
    "cos_lr":         True,
    "augment":        True,

    "hsv_h":          0.015,
    "hsv_s":          0.7,
    "hsv_v":          0.4,
    "degrees":        10.0,
    "translate":      0.1,
    "scale":          0.5,
    "flipud":         0.0,
    "fliplr":         0.5,
    "mosaic":         1.0,
    "mixup":          0.1,

    "device":         "",
    "workers":        4,
    "project":        str(MODELS_DIR),
    "name":           "railway_multiclass_detector",
    "exist_ok":       True,
    "save":           True,
    "save_period":    10,
    "verbose":        True,
    "plots":          True,
}


def check_dataset():
    data_yaml = DATASET_DIR / "data.yaml"
    if not data_yaml.exists():
        print("  Multi-class dataset not found!")
        print("    Run:  python scripts/build_multiclass_dataset.py  first")
        sys.exit(1)

    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)

    train_img = DATASET_DIR / "train" / "images"
    n_train   = len(list(train_img.glob("*.*"))) if train_img.exists() else 0
    valid_img = DATASET_DIR / "valid" / "images"
    n_valid   = len(list(valid_img.glob("*.*"))) if valid_img.exists() else 0

    print(f"  Dataset: {cfg.get('nc')} classes -> {cfg.get('names')}")
    print(f"    Train: {n_train} images   Valid: {n_valid} images")

    if n_train == 0:
        print("  No training images found. Check dataset structure.")
        sys.exit(1)

    return data_yaml


def train():
    print("=" * 60)
    print("  Railway Multi-Class Defect Detection - Model Training")
    print("=" * 60)

    data_yaml = check_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Loading base model: {CONFIG['model']}")
    model = YOLO(CONFIG["model"])

    print(f"\n  Starting training for {CONFIG['epochs']} epochs ...")
    print(f"    Data    : {data_yaml}")
    print(f"    Output  : {MODELS_DIR / CONFIG['name']}")
    print()

    run_cfg = {k: v for k, v in CONFIG.items() if k not in {"model"}}

    results = model.train(
        data=str(data_yaml),
        **run_cfg,
    )

    best_src = Path(results.save_dir) / "weights" / "best.pt"
    best_dst = MODELS_DIR / "best_multiclass_detector.pt"
    if best_src.exists():
        shutil.copy2(best_src, best_dst)
        print(f"\n  Best model saved -> {best_dst}")
    else:
        print(f"   best.pt not found at {best_src}")

    # ── per-class metrics, not just overall mAP — the whole point of
    #    this run is checking whether crack detection held up while the
    #    new classes came online, not just an aggregate number. ────────
    try:
        metrics = model.val()
        names = metrics.names if hasattr(metrics, "names") else {}
        print("\n  Overall Validation Metrics:")
        print(f"    mAP50    : {metrics.box.map50:.4f}")
        print(f"    mAP50-95 : {metrics.box.map:.4f}")
        print(f"    Precision: {metrics.box.mp:.4f}")
        print(f"    Recall   : {metrics.box.mr:.4f}")

        print("\n  Per-class mAP50:")
        for i, ap50 in enumerate(metrics.box.ap50):
            cls_name = names.get(i, str(i)) if isinstance(names, dict) else names[i]
            print(f"    {cls_name:15s}: {ap50:.4f}")
    except Exception as e:
        print(f"   Could not compute final metrics: {e}")

    summary = {
        "trained_at":   datetime.now().isoformat(),
        "model":        CONFIG["model"],
        "epochs":       CONFIG["epochs"],
        "best_model":   str(best_dst),
        "results_dir":  str(results.save_dir),
        "dataset":      str(data_yaml),
    }
    summary_path = MODELS_DIR / "training_summary_multiclass.yaml"
    with open(summary_path, "w") as f:
        yaml.dump(summary, f)

    print(f"\n  Training summary saved -> {summary_path}")
    print("\n  Training complete.")
    return best_dst


if __name__ == "__main__":
    train()
