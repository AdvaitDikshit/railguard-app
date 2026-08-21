"""
Railway Crack Detection — Model Evaluation
Runs validation on the test set and generates a performance report.
Usage:  python scripts/evaluate_model.py
"""

import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO

BASE_DIR    = Path(__file__).parent.parent
MODELS_DIR  = BASE_DIR / "models"
DATASET_DIR = BASE_DIR / "dataset" / "merged"


def find_model() -> Path:
    candidates = [
        MODELS_DIR / "best_crack_detector.pt",
        MODELS_DIR / "railway_crack_detector" / "weights" / "best.pt",
    ]
    for c in candidates:
        if c.exists():
            return c
    print("  No trained model found. Run scripts/train_model.py first.")
    sys.exit(1)


def main():
    print("═" * 60)
    print("  Railway Crack Detection — Evaluation")
    print("═" * 60)

    model_path = find_model()
    data_yaml  = DATASET_DIR / "data.yaml"

    if not data_yaml.exists():
        print("  dataset/merged/data.yaml not found.")
        sys.exit(1)

    print(f"\n  Model : {model_path}")
    print(f"  Data  : {data_yaml}\n")

    model = YOLO(str(model_path))

    # validate on test split
    metrics = model.val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        save_json=True,
        plots=True,
        project=str(MODELS_DIR),
        name="eval_results",
        exist_ok=True,
    )

    print("\n" + "─" * 60)
    print("  EVALUATION RESULTS")
    print("─" * 60)
    print(f"  mAP@50       : {metrics.box.map50:.4f}  ({metrics.box.map50*100:.2f}%)")
    print(f"  mAP@50-95    : {metrics.box.map:.4f}  ({metrics.box.map*100:.2f}%)")
    print(f"  Precision    : {metrics.box.mp:.4f}")
    print(f"  Recall       : {metrics.box.mr:.4f}")

    # per-class
    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)
    names = cfg.get("names", [])

    if hasattr(metrics.box, "ap_class_index"):
        print("\n  Per-Class AP@50:")
        for cls_idx, ap in zip(metrics.box.ap_class_index, metrics.box.ap50):
            name = names[cls_idx] if cls_idx < len(names) else f"class_{cls_idx}"
            bar  = "█" * int(ap * 20)
            print(f"    {name:<25} {ap:.4f}  {bar}")

    print("\n  Evaluation complete. Plots saved to models/eval_results/")


if __name__ == "__main__":
    main()