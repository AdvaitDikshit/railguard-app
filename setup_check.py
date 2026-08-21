"""
Quick setup verification — run this to check everything is in place.
Usage:  python setup_check.py
"""

import sys
import importlib
from pathlib import Path

print("═" * 55)
print("  RailGuard — Setup Verification")
print("═" * 55)

BASE = Path(__file__).parent

checks = {
    "Python ≥ 3.10":        lambda: sys.version_info >= (3, 10),
    "torch":                lambda: bool(importlib.import_module("torch")),
    "ultralytics (YOLOv8)": lambda: bool(importlib.import_module("ultralytics")),
    "flask":                lambda: bool(importlib.import_module("flask")),
    "cv2 (OpenCV)":         lambda: bool(importlib.import_module("cv2")),
    "roboflow":             lambda: bool(importlib.import_module("roboflow")),
    "PIL (Pillow)":         lambda: bool(importlib.import_module("PIL")),
    "numpy":                lambda: bool(importlib.import_module("numpy")),
}

all_ok = True
for name, check in checks.items():
    try:
        ok = check()
    except Exception:
        ok = False
    status = "" if ok else ""
    print(f"  {status}  {name}")
    if not ok:
        all_ok = False

print()

# Check GPU
try:
    import torch
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        print(f"    GPU detected: {gpu}")
    else:
        print("    No GPU detected — will use CPU (training will be slow)")
except Exception:
    pass

# Check dataset
merged = BASE / "dataset" / "merged" / "data.yaml"
if merged.exists():
    print("    Merged dataset: FOUND")
else:
    print("    Merged dataset: not found  → run scripts/download_dataset.py")

# Check model
model = BASE / "models" / "best_crack_detector.pt"
if model.exists():
    print("    Trained model: FOUND")
else:
    print("    Trained model: not found  → run scripts/train_model.py")

print()
if all_ok:
    print("    All dependencies OK!")
    print("    Next: python scripts/download_dataset.py")
else:
    print("     Some dependencies missing — run: pip install -r requirements.txt")
print("═" * 55)