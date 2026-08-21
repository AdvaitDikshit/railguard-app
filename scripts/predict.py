"""
Railway Crack Detection — Command Line Interface
Usage:
    python scripts/predict.py --image path/to/image.jpg
    python scripts/predict.py --image path/to/image.jpg --model models/best_crack_detector.pt
    python scripts/predict.py --image path/to/image.jpg --conf 0.4 --show
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from detector import CrackDetector


def parse_args():
    p = argparse.ArgumentParser(description="Railway Crack Detector — CLI")
    p.add_argument("--image",  required=True, help="Path to input image")
    p.add_argument("--model",  default=None,  help="Path to trained .pt model")
    p.add_argument("--conf",   type=float, default=0.35, help="Confidence threshold (0-1)")
    p.add_argument("--show",   action="store_true", help="Display annotated image (requires display)")
    p.add_argument("--json",   action="store_true", help="Output raw JSON result")
    return p.parse_args()


def print_report(result: dict):
    sev = result["severity"]
    adv = result["advisory"]
    dets = result["detections"]

    icons = {
        "CRITICAL": "", "HIGH": " ", "MODERATE": "", "LOW": "", "NO_CRACK": ""
    }

    print("\n" + "═" * 62)
    print(f"  {icons.get(sev,'?')}  RAILWAY CRACK DETECTION REPORT")
    print("═" * 62)
    print(f"  Image      : {result['original_image']}")
    print(f"  Timestamp  : {result['timestamp']}")
    print(f"  Model      : {result['model_used']}")
    print()
    print(f"  SEVERITY   : {sev}")
    print(f"  Detections : {result['detection_count']}")
    print()

    if dets:
        print("  ┌── Detected Objects ────────────────────────────────")
        for i, d in enumerate(dets, 1):
            print(f"  │  {i}. {d['class_name']:<20} "
                  f"conf={d['confidence']:.1%}  area={d['area_frac']:.2%}")
        print("  └─────────────────────────────────────────────────────")
        print()

    print(f"  {adv['heading']}")
    print()
    print("  RECOMMENDED ACTIONS:")
    for i, action in enumerate(adv["actions"], 1):
        print(f"  {i:2d}. {action}")
    print()
    print(f"  Timeline    : {adv['timeline']}")
    print(f"  Authority   : {adv['authority']}")
    print(f"  Risk        : {adv['risk_summary']}")
    print()
    print(f"  Annotated   : {result['annotated_image']}")
    print("═" * 62 + "\n")


def main():
    args = parse_args()
    img  = Path(args.image)
    if not img.exists():
        print(f"  Image not found: {args.image}")
        sys.exit(1)

    print(f"  Analysing: {img.name}")
    detector = CrackDetector(model_path=args.model, conf_threshold=args.conf)
    result   = detector.detect(str(img))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)

    if args.show:
        try:
            import cv2
            ann = result["annotated_image"]
            # strip leading 'results/' prefix if needed
            ann_path = Path(__file__).parent.parent / "static" / ann
            if not ann_path.exists():
                ann_path = Path(__file__).parent.parent / ann
            img_cv = cv2.imread(str(ann_path))
            if img_cv is not None:
                cv2.imshow("Railway Crack Detection", img_cv)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
        except Exception as e:
            print(f"   Could not display image: {e}")


if __name__ == "__main__":
    main()