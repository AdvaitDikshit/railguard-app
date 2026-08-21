"""
YOLOv8 Training Script for Railway Crack Detection
Run this after download_dataset.py
"""

import os
import sys
import yaml
import shutil
from pathlib import Path
from datetime import datetime

from ultralytics import YOLO

# ─────────────────────────────────────────────────────────────
# TRAINING CONFIGURATION
# ─────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent.parent
# Points at the leak-free resplit (dataset/merged/ had 32.1% of source
# images' augmented copies crossing train/valid/test — see
# scripts/fix_split_leakage.py). This is the dataset the baseline
# should be measured against.
DATASET_DIR = BASE_DIR / "dataset" / "merged_resplit"
MODELS_DIR  = BASE_DIR / "models"

CONFIG = {
    # Model size: yolov8n (nano-fastest), yolov8s (small), yolov8m (medium),
    #             yolov8l (large), yolov8x (extra-large-best accuracy)
    "model":          "yolov8s.pt",

    "epochs":         100,       # increase for better accuracy (try 150-300)
    "imgsz":          640,       # input image size (keep 640 for best results)
    "batch":          -1,        # auto-batch: Ultralytics picks the largest safe
                                  # batch for available VRAM (~60% util target) —
                                  # safer than a fixed guess on a 6GB card
    "patience":       20,        # early stopping patience
    "lr0":            0.01,      # initial learning rate
    "lrf":            0.01,      # final learning rate factor
    "momentum":       0.937,
    "weight_decay":   0.0005,
    "warmup_epochs":  3,
    "cos_lr":         True,      # cosine LR scheduler
    "augment":        True,

    # Data augmentation (helps with small datasets)
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

    "device":         "",        # "" = auto (GPU if available, else CPU)
    "workers":        4,
    "project":        str(MODELS_DIR),
    "name":           "railway_crack_detector",
    "exist_ok":       True,
    "save":           True,
    "save_period":    10,        # save checkpoint every N epochs
    "verbose":        True,
    "plots":          True,      # save training plots
}

# ─────────────────────────────────────────────────────────────


def check_dataset():
    """Verify merged dataset exists and has images."""
    data_yaml = DATASET_DIR / "data.yaml"
    if not data_yaml.exists():
        print("  Merged dataset not found!")
        print("    Run:  python scripts/download_dataset.py  first")
        sys.exit(1)

    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)

    train_img = DATASET_DIR / "train" / "images"
    n_train   = len(list(train_img.glob("*.*"))) if train_img.exists() else 0
    valid_img = DATASET_DIR / "valid" / "images"
    n_valid   = len(list(valid_img.glob("*.*"))) if valid_img.exists() else 0

    print(f"  Dataset: {cfg.get('nc')} classes → {cfg.get('names')}")
    print(f"    Train: {n_train} images   Valid: {n_valid} images")

    if n_train == 0:
        print("  No training images found. Check dataset structure.")
        sys.exit(1)

    return data_yaml


def train():
    """Run YOLOv8 training."""
    print("═" * 60)
    print("  Railway Crack Detection — Model Training")
    print("═" * 60)

    data_yaml = check_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Loading base model: {CONFIG['model']}")
    model = YOLO(CONFIG["model"])

    print(f"\n  Starting training for {CONFIG['epochs']} epochs …")
    print(f"    Data    : {data_yaml}")
    print(f"    Output  : {MODELS_DIR / CONFIG['name']}")
    print()

    run_cfg = {k: v for k, v in CONFIG.items()
               if k not in {"model"}}

    results = model.train(
        data=str(data_yaml),
        **run_cfg,
    )

    # ── save best model to a fixed location ─────────────────────
    best_src = Path(results.save_dir) / "weights" / "best.pt"
    best_dst = MODELS_DIR / "best_crack_detector.pt"
    if best_src.exists():
        shutil.copy2(best_src, best_dst)
        print(f"\n  Best model saved → {best_dst}")
    else:
        print(f"   best.pt not found at {best_src}")

    # ── print final metrics ──────────────────────────────────────
    try:
        metrics = model.val()
        print("\n  Validation Metrics:")
        print(f"    mAP50    : {metrics.box.map50:.4f}")
        print(f"    mAP50-95 : {metrics.box.map:.4f}")
        print(f"    Precision: {metrics.box.mp:.4f}")
        print(f"    Recall   : {metrics.box.mr:.4f}")
    except Exception as e:
        print(f"   Could not compute final metrics: {e}")

    # ── save training summary ────────────────────────────────────
    summary = {
        "trained_at":   datetime.now().isoformat(),
        "model":        CONFIG["model"],
        "epochs":       CONFIG["epochs"],
        "best_model":   str(best_dst),
        "results_dir":  str(results.save_dir),
        "dataset":      str(data_yaml),
    }
    summary_path = MODELS_DIR / "training_summary.yaml"
    with open(summary_path, "w") as f:
        yaml.dump(summary, f)

    print(f"\n  Training summary saved → {summary_path}")
    print("\n  Training complete! Run:  python app.py  to start the web app.")
    return best_dst


if __name__ == "__main__":
    train()