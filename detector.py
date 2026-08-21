"""
Railway Crack Detection — Inference Engine
Fixes:
  1. Single bounding box per crack (tight NMS iou=0.3)
  2. Advisory varies by crack SIZE (width/height/area of bbox)
  3. Confidence threshold raised to 0.55
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

# ── paths ─────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "static" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── confidence threshold ──────────────────────────────────────
# 0.55 = only show detections the model is >55% sure about.
# Lower = more detections but more false positives.
# Higher = fewer but more reliable detections.
DEFAULT_CONF = 0.55

# ── NMS IoU threshold ─────────────────────────────────────────
# 0.3 = if two boxes overlap >30% they get merged into one.
# This is what eliminates duplicate bounding boxes on the same crack.
NMS_IOU = 0.3

# ── crack size thresholds (as % of image area) ────────────────
# Used to give different advisory based on physical crack size.
#
# RECALIBRATED (Aug 2026) — the original absolute cutoffs (large >15%,
# medium 5-15%, small 1-5%) assumed roughly tight bounding boxes. An
# audit of this project's actual training labels found the ground-truth
# boxes are loose "crack is somewhere in this region" annotations, not
# tight boxes: median box area = 65.7% of the image, 86.5% of boxes
# span >50% of image width. With the old thresholds, nearly every
# detection fell into "large" regardless of the crack's real size,
# which systematically pushed classify_severity() toward HIGH/CRITICAL.
#
# These thresholds are now set from the actual area_frac percentiles of
# this dataset's labels (train split, post watermark-cleanup, n=4869
# boxes), so "large"/"medium"/"small"/"hairline" reflect genuine
# relative rank within what this model was trained on, instead of an
# absolute assumption that no longer matched the data:
#   p10=0.056  p25=0.395  p40=0.559  p75=0.911  p90=0.988
# hairline = bottom ~10%, small = next ~30%, medium = next ~35%,
# large = top ~25%.
#
# Caveat: this recalibrates severity's SIZE categories to the dataset's
# real distribution, but does not fix the underlying loose-annotation
# problem itself (see dataset/tighten_review/ and dataset/
# removed_watermarked/ for that investigation) — a retrained model on
# tighter boxes would make "size" mean actual physical crack size again,
# not just relative rank among loose boxes.
SIZE_LARGE  = 0.91   # top ~25% of this dataset's box sizes → large
SIZE_MEDIUM = 0.56   # next ~35% → medium
SIZE_SMALL  = 0.06   # next ~30% → small
# below 6% → hairline crack (bottom ~10%)

# ── class-name normalization ─────────────────────────────────
# KNOWN BUG (found Aug 2026, not yet fixed by retraining): best.pt was
# trained BEFORE dataset/merged/fix_labels.py normalized every label to
# class 0 and before data.yaml's single-class (nc:1, names:['crack'])
# config existed in its current form — file timestamps show training
# finished ~2 hours before data.yaml was written and ~2 months before
# fix_labels.py. As a result this checkpoint actually has 303 output
# classes, not 1 — almost all of them meaningless leftover numeric
# placeholders from the original (pre-merge) Roboflow source datasets
# (model.names looks like {0: '0', 1: '1', ..., 300: 'crack', ...}).
# Only 5 class indices carry real meaning; everything else is noise.
# This does NOT affect severity (which only uses confidence + box size,
# not class), but showing the raw class name to a user would be actively
# misleading. Normalize here until the model is retrained on the
# already-fixed dataset (dataset/merged, post watermark-cleanup) —
# at that point this map should be deleted and the real single class
# name used directly.
_REAL_CLASS_NAMES = {
    298: "defect",
    299: "crack",   # "cacked" — typo of "cracked" in the source label
    300: "crack",
    301: "crack",   # "cracked"
    302: "railway gap",
}

def normalize_class_name(cls_id: int, raw_name: str) -> str:
    # The legacy map only covers ids 298-302 from the old 303-class model
    # that predated the dataset-leakage fix and retrain. The new model is
    # a clean single-class model and already reports the correct label
    # ("crack") via raw_name — use that directly. The old model's classes
    # 0-297 were meaningless numeric placeholders (raw_name == str(cls_id)
    # e.g. "37", "150") inherited from pre-merge source datasets, so a
    # purely-numeric raw_name is exactly the signature to still catch and
    # hide as "possible defect"; any real model label never looks like that.
    if cls_id in _REAL_CLASS_NAMES:
        return _REAL_CLASS_NAMES[cls_id]
    if raw_name and not raw_name.strip().isdigit():
        return raw_name
    return "possible defect"

# ── BGR colours for bounding boxes ───────────────────────────
SEV_COLORS = {
    "CRITICAL": (0,   0,   220),
    "HIGH":     (0,   100, 255),
    "MODERATE": (0,   190, 255),
    "LOW":      (50,  210, 50),
    "NO_CRACK": (50,  210, 50),
}

# ─────────────────────────────────────────────────────────────
# DYNAMIC ADVISORY — varies by crack size AND confidence
# Each entry: crack_size_category → advisory dict
# ─────────────────────────────────────────────────────────────

def build_advisory(severity: str, crack_profile: dict) -> dict:
    """
    Generate a specific advisory based on:
    - severity level (CRITICAL/HIGH/MODERATE/LOW/NO_CRACK)
    - crack_profile: {size_cat, max_width_px, max_height_px, max_area_pct, max_conf, count}
    Returns a fully populated advisory dict.
    """
    size_cat   = crack_profile.get("size_cat", "small")
    count      = crack_profile.get("count", 0)
    max_conf   = crack_profile.get("max_conf", 0)
    w_px       = crack_profile.get("max_width_px", 0)
    h_px       = crack_profile.get("max_height_px", 0)
    area_pct   = crack_profile.get("max_area_pct", 0)

    # ── CRITICAL ──────────────────────────────────────────────
    if severity == "CRITICAL":
        if size_cat == "large":
            return {
                "icon":    "",
                "color":   "#c0392b",
                "heading": "CRITICAL — Catastrophic Crack, Immediate Shutdown",
                "risk_summary": (
                    f"LARGE crack spanning {area_pct:.1f}% of track surface "
                    f"({w_px}×{h_px}px) detected with {max_conf:.0%} confidence. "
                    "Structural integrity severely compromised. Derailment risk is EXTREME."
                ),
                "actions": [
                    f"EMERGENCY SHUTDOWN — halt ALL trains immediately. {count} crack(s) detected.",
                    f"Deploy emergency engineering team ON-SITE within 1 hour.",
                    "Impose 0 km/h — ABSOLUTE NO TRAFFIC on this section.",
                    "Notify Divisional Railway Manager (DRM), Safety Commissioner, and Zone HQ.",
                    "Dispatch heavy rail replacement/welding unit with full equipment.",
                    "Install physical barrier and warning signals at both ends of the section.",
                    "GPS-tag all crack locations and photograph for official incident report.",
                    "File emergency incident report (Form IRS-T-12) within 4 hours.",
                    "Do NOT reopen track without sign-off from Chief Engineer.",
                ],
                "timeline":  "Emergency repair: within 12 hours. Track closed until certified safe.",
                "authority": "Chief Engineer + Divisional Railway Manager (DRM) + Safety Commissioner",
            }
        elif size_cat == "medium":
            return {
                "icon":    "",
                "color":   "#c0392b",
                "heading": "CRITICAL — Severe Crack, Line Closure Required",
                "risk_summary": (
                    f"Severe crack covering {area_pct:.1f}% of track area "
                    f"({w_px}×{h_px}px) detected at {max_conf:.0%} confidence. "
                    "High risk of rail fracture under train loading."
                ),
                "actions": [
                    f"IMMEDIATELY halt all train operations on this section. {count} crack(s) found.",
                    "Deploy emergency response team within 2 hours.",
                    "Impose 0 km/h speed restriction — NO TRAFFIC PERMITTED.",
                    "Notify Divisional Railway Manager (DRM) and Safety Commissioner without delay.",
                    "Dispatch emergency rail welding / replacement unit.",
                    "Conduct manual on-site inspection at GPS coordinates before reopening.",
                    "File incident report (Form IRS-T-12) within 6 hours.",
                    "Photograph and GPS-tag crack location for official records.",
                ],
                "timeline":  "Emergency repair within 24 hours. No operations until cleared.",
                "authority": "Divisional Railway Manager (DRM) + Safety Commissioner",
            }
        else:  # small / hairline but high confidence
            return {
                "icon":    "",
                "color":   "#c0392b",
                "heading": "CRITICAL — Deep Crack Detected, Urgent Inspection",
                "risk_summary": (
                    f"Small but deep crack ({w_px}×{h_px}px, {area_pct:.2f}% area) "
                    f"detected at very high confidence ({max_conf:.0%}). "
                    "May indicate subsurface fracture. Immediate inspection required."
                ),
                "actions": [
                    f"Impose speed restriction: MAX 10 km/h immediately. {count} crack(s) detected.",
                    "Dispatch Permanent Way Inspector for urgent physical inspection within 4 hours.",
                    "Use ultrasonic rail testing equipment to check for subsurface fracture.",
                    "Notify Section Engineer and Divisional Engineer immediately.",
                    "Install crack-marking paint and measure crack width manually.",
                    "If crack width > 1mm, escalate to full line closure.",
                    "Increase patrol frequency to every 3 hours.",
                ],
                "timeline":  "Physical inspection within 4 hours. Repair decision within 24 hours.",
                "authority": "Divisional Engineer (DE) + Section Engineer (SE)",
            }

    # ── HIGH ──────────────────────────────────────────────────
    elif severity == "HIGH":
        if size_cat == "large":
            return {
                "icon":    "",
                "color":   "#e67e22",
                "heading": "HIGH — Wide Surface Crack, Speed Restriction Mandatory",
                "risk_summary": (
                    f"Large surface crack covering {area_pct:.1f}% of track "
                    f"({w_px}×{h_px}px) at {max_conf:.0%} confidence. "
                    "Risk of crack propagation under repeated loading."
                ),
                "actions": [
                    f"Impose speed restriction: MAX 10 km/h immediately. {count} crack(s) detected.",
                    "Schedule emergency PW Inspector visit within 24 hours.",
                    "Deploy rail grinding unit to assess surface crack depth.",
                    "Install fishplates as temporary stabilisation across the crack.",
                    "Submit defect report to Divisional Engineer within 12 hours.",
                    "Mark crack boundaries with paint — re-measure every 4 hours.",
                    "Monitor for crack width growth — if > 2mm, close section immediately.",
                    "Increase patrol frequency to every 6 hours.",
                ],
                "timeline":  "Temporary repair within 24 hours. Full repair within 72 hours.",
                "authority": "Divisional Engineer (DE) + Section Engineer (SE)",
            }
        elif size_cat == "medium":
            return {
                "icon":    "",
                "color":   "#e67e22",
                "heading": "HIGH — Significant Crack, Urgent Maintenance Required",
                "risk_summary": (
                    f"Significant crack ({w_px}×{h_px}px, {area_pct:.1f}% area) "
                    f"at {max_conf:.0%} confidence. Risk of failure under heavy load."
                ),
                "actions": [
                    f"Impose speed restriction: MAX 15 km/h on affected section. {count} crack(s).",
                    "Schedule PW Inspector visit within 24 hours.",
                    "Deploy rail welding / repair gang within 48 hours.",
                    "Install joint bars or fishplates as temporary stabilisation.",
                    "Submit defect report to Section Engineer and Divisional Engineer.",
                    "Patrol every 8 hours until repair is complete.",
                    "Apply crack-marking paint and measure progression hourly.",
                ],
                "timeline":  "Repair required within 48–72 hours.",
                "authority": "Divisional Engineer (DE) + Section Engineer (SE)",
            }
        else:
            return {
                "icon":    "",
                "color":   "#e67e22",
                "heading": "HIGH — Surface Crack Detected, Monitor Closely",
                "risk_summary": (
                    f"Surface crack ({w_px}×{h_px}px) detected at {max_conf:.0%} confidence. "
                    "Requires prompt attention to prevent propagation."
                ),
                "actions": [
                    f"Impose speed restriction: MAX 25 km/h. {count} crack(s) logged.",
                    "Schedule PW inspection within 48 hours.",
                    "Apply crack sealant as temporary measure if crack is open.",
                    "Log in Track Maintenance Register with photograph.",
                    "Notify Section Engineer — plan repair in next maintenance window.",
                    "Patrol twice daily until repaired.",
                ],
                "timeline":  "Inspection within 48 hours. Repair within 5 days.",
                "authority": "Section Engineer (SE) + Junior Engineer (JE)",
            }

    # ── MODERATE ──────────────────────────────────────────────
    elif severity == "MODERATE":
        if size_cat in ("large", "medium"):
            return {
                "icon":    "",
                "color":   "#f39c12",
                "heading": "MODERATE — Visible Crack, Scheduled Repair Needed",
                "risk_summary": (
                    f"Visible crack covering {area_pct:.1f}% of track area "
                    f"({w_px}×{h_px}px) at {max_conf:.0%} confidence. "
                    "Low immediate risk but deterioration likely without maintenance."
                ),
                "actions": [
                    f"Impose precautionary speed restriction: MAX 30 km/h. {count} crack(s) found.",
                    "Schedule PW inspection within 72 hours.",
                    "Plan rail grinding or surface treatment in next maintenance cycle.",
                    "Log crack dimensions in Track Maintenance Register.",
                    "Notify Section Engineer for scheduling.",
                    "Patrol twice daily — escalate if crack width increases.",
                    "Apply crack-marking paint for progression monitoring.",
                ],
                "timeline":  "Inspection within 72 hours. Repair within 7 days.",
                "authority": "Section Engineer (SE)",
            }
        else:
            return {
                "icon":    "",
                "color":   "#f39c12",
                "heading": "MODERATE — Minor Surface Crack, Routine Action",
                "risk_summary": (
                    f"Minor surface crack ({w_px}×{h_px}px, {area_pct:.2f}% area) "
                    f"detected at {max_conf:.0%} confidence. "
                    "Standard preventive maintenance recommended."
                ),
                "actions": [
                    f"Log {count} crack(s) in Track Maintenance Register with photos.",
                    "No immediate speed restriction required.",
                    "Include in next scheduled maintenance inspection.",
                    "Apply surface crack sealant during next maintenance window.",
                    "Monitor at standard patrol frequency.",
                    "Re-inspect in 7 days — escalate if growth observed.",
                ],
                "timeline":  "Include in next scheduled maintenance within 14 days.",
                "authority": "Junior Engineer (JE) + Section Engineer (SE)",
            }

    # ── LOW ───────────────────────────────────────────────────
    elif severity == "LOW":
        return {
            "icon":    "",
            "color":   "#2980b9",
            "heading": "LOW — Surface Marking Detected, Monitor",
            "risk_summary": (
                f"Possible surface marking or hairline crack ({w_px}×{h_px}px, "
                f"{area_pct:.3f}% area) at {max_conf:.0%} confidence. "
                "Low risk — standard monitoring advised."
            ),
            "actions": [
                f"Note {count} potential indication(s) in Track Patrol Log.",
                "No speed restriction required at this time.",
                "Visual inspection on next scheduled patrol.",
                "Photograph for record — compare on next inspection.",
                "If crack is confirmed on visual inspection, escalate to MODERATE.",
            ],
            "timeline":  "Review at next routine patrol (within 7 days).",
            "authority": "Junior Engineer (JE)",
        }

    # ── NO CRACK ──────────────────────────────────────────────
    else:
        return {
            "icon":    "",
            "color":   "#27ae60",
            "heading": "No Crack Detected — Track Appears Normal",
            "risk_summary": "No structural anomaly detected in this image. Track surface looks intact.",
            "actions": [
                "Continue standard patrol and maintenance schedule.",
                "No immediate action required.",
                "Log this inspection in routine patrol records.",
            ],
            "timeline":  "Standard maintenance cycle.",
            "authority": "Routine Operations",
        }


# ─────────────────────────────────────────────────────────────
# SIZE CATEGORISER
# ─────────────────────────────────────────────────────────────

def categorise_size(area_frac: float) -> str:
    if area_frac >= SIZE_LARGE:
        return "large"
    elif area_frac >= SIZE_MEDIUM:
        return "medium"
    elif area_frac >= SIZE_SMALL:
        return "small"
    return "hairline"


# ─────────────────────────────────────────────────────────────
# SEVERITY CLASSIFIER
# ─────────────────────────────────────────────────────────────

SEVERITY_ORDER = ["NO_CRACK", "LOW", "MODERATE", "HIGH", "CRITICAL"]

def classify_severity(detections: list) -> str:
    """
    Severity is based on BOTH confidence AND physical crack size.
    A large crack at moderate confidence can still be HIGH/CRITICAL.
    A tiny crack at very high confidence stays MODERATE.
    """
    if not detections:
        return "NO_CRACK"

    worst = "LOW"
    for det in detections:
        conf     = det["confidence"]
        size_cat = det["size_cat"]

        if size_cat == "large":
            if conf >= 0.75:   sev = "CRITICAL"
            elif conf >= 0.55: sev = "HIGH"
            else:              sev = "MODERATE"
        elif size_cat == "medium":
            if conf >= 0.85:   sev = "CRITICAL"
            elif conf >= 0.65: sev = "HIGH"
            elif conf >= 0.55: sev = "MODERATE"
            else:              sev = "LOW"
        elif size_cat == "small":
            if conf >= 0.90:   sev = "HIGH"
            elif conf >= 0.70: sev = "MODERATE"
            else:              sev = "LOW"
        else:  # hairline
            if conf >= 0.90:   sev = "MODERATE"
            else:              sev = "LOW"

        if SEVERITY_ORDER.index(sev) > SEVERITY_ORDER.index(worst):
            worst = sev

    return worst


# ─────────────────────────────────────────────────────────────
# MAIN DETECTOR CLASS
# ─────────────────────────────────────────────────────────────

class CrackDetector:
    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = DEFAULT_CONF):
        self.conf_threshold = conf_threshold
        self.model_path     = self._find_model(model_path)
        self.model          = YOLO(str(self.model_path))
        print(f"  Model loaded : {self.model_path}")
        print(f"  Conf threshold: {self.conf_threshold:.0%}  |  NMS IoU: {NMS_IOU}")

    def _find_model(self, path: Optional[str]) -> Path:
        if path and Path(path).exists():
            return Path(path)
        candidates = [
            # models/best_crack_detector.pt is the canonical output of
            # scripts/train_model.py — check it first so a fresh retrain is
            # always picked up. The runs/detect/train* paths are fallbacks
            # for ad-hoc/manual runs that never got copied there; they used
            # to be checked FIRST, which meant a stale leftover best.pt in
            # runs/detect/train silently shadowed every newer retrain.
            BASE_DIR / "models" / "best_crack_detector.pt",
            BASE_DIR / "runs" / "detect" / "train"  / "weights" / "best.pt",
            BASE_DIR / "runs" / "detect" / "train2" / "weights" / "best.pt",
            BASE_DIR / "runs" / "detect" / "train3" / "weights" / "best.pt",
        ]
        for c in candidates:
            if c.exists():
                return c
        print("  No trained model found — using yolov8n.pt (demo mode)")
        return Path("yolov8n.pt")

    def detect(self, image_path: str) -> dict:
        img_path = Path(image_path)
        img      = cv2.imread(str(img_path))
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        h, w     = img.shape[:2]
        total_px = h * w

        # ── Run YOLOv8 with tight NMS ──────────────────────────
        # iou=0.3 → boxes overlapping more than 30% get merged into 1
        # This is the key fix for duplicate bounding boxes
        results = self.model(
            str(img_path),
            conf=self.conf_threshold,
            iou=NMS_IOU,           # ← tight NMS = single box per crack
            verbose=False,
        )[0]

        # ── Parse boxes ────────────────────────────────────────
        detections = []
        if results.boxes is not None and len(results.boxes) > 0:
            boxes   = results.boxes.xyxy.cpu().numpy()
            confs   = results.boxes.conf.cpu().numpy()
            cls_ids = results.boxes.cls.cpu().numpy().astype(int)
            names   = results.names

            for box, conf, cls_id in zip(boxes, confs, cls_ids):
                x1, y1, x2, y2 = map(int, box)
                bw       = max(0, x2 - x1)
                bh       = max(0, y2 - y1)
                area_px  = bw * bh
                area_frac = area_px / total_px if total_px > 0 else 0
                size_cat  = categorise_size(area_frac)

                detections.append({
                    "class_id":   int(cls_id),
                    "class_name": normalize_class_name(int(cls_id), names.get(cls_id, "")),
                    "confidence": float(conf),
                    "bbox":       [x1, y1, x2, y2],
                    "width_px":   bw,
                    "height_px":  bh,
                    "area_px":    area_px,
                    "area_frac":  area_frac,
                    "size_cat":   size_cat,
                })

        # Sort by area descending (largest crack first)
        detections.sort(key=lambda d: d["area_px"], reverse=True)

        # ── Classify severity ───────────────────────────────────
        severity = classify_severity(detections)

        # ── Build crack profile for advisory ───────────────────
        if detections:
            biggest = detections[0]
            profile = {
                "count":        len(detections),
                "size_cat":     biggest["size_cat"],
                "max_conf":     max(d["confidence"] for d in detections),
                "max_area_pct": biggest["area_frac"] * 100,
                "max_width_px": biggest["width_px"],
                "max_height_px":biggest["height_px"],
            }
        else:
            profile = {"count": 0, "size_cat": "none", "max_conf": 0,
                       "max_area_pct": 0, "max_width_px": 0, "max_height_px": 0}

        advisory = build_advisory(severity, profile)

        # ── Draw annotated image ────────────────────────────────
        ann_name = f"result_{uuid.uuid4().hex[:10]}.jpg"
        ann_path = RESULTS_DIR / ann_name
        annotated = self._draw(img.copy(), detections, severity, advisory, profile)
        cv2.imwrite(str(ann_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

        return {
            "id":              uuid.uuid4().hex[:12],
            "timestamp":       datetime.now().isoformat(),
            "original_image":  str(img_path),
            "annotated_image": f"results/{ann_name}",
            "image_size":      {"width": w, "height": h},
            "severity":        severity,
            "detections":      detections,
            "detection_count": len(detections),
            "advisory":        advisory,
            "crack_profile":   profile,
            "model_used":      str(self.model_path),
            "conf_threshold":  self.conf_threshold,
        }

    def detect_video(self, video_path: str, max_frames: int = 450, device: Optional[str] = None) -> dict:
        """
        Runs tracked detection across a video (YOLO + ByteTrack, via
        ultralytics' built-in .track()) and aggregates per-track-ID
        sightings into unique physical defects — a crack visible across
        80 consecutive frames is reported once, with the frame it was
        first seen, not 80 separate detections. This is what "avoid
        counting the same crack hundreds of times" (the original
        project brief's own phrasing) actually means in practice.

        `max_frames` is a hard runtime cap (not a sampling stride —
        tracking needs consecutive frames to maintain identity, so
        skipping frames for speed isn't compatible with it). At 450
        frames / ~30fps that's about 15 seconds of source video; a
        longer clip is simply truncated, not sped through.
        """
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_s = total_frames / fps if fps > 0 else 0.0
        cap.release()

        tracks: dict = {}
        frames_processed = 0

        results_gen = self.model.track(
            source=str(video_path),
            conf=self.conf_threshold,
            iou=NMS_IOU,
            tracker="bytetrack.yaml",
            persist=True,
            stream=True,
            verbose=False,
            device=device,  # None = auto (GPU if available); override e.g. "cpu"
        )

        for frame_idx, result in enumerate(results_gen):
            frames_processed += 1
            if frames_processed > max_frames:
                break
            ts = frame_idx / fps if fps > 0 else 0.0

            if result.boxes is None or result.boxes.id is None:
                continue

            h, w = result.orig_shape
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            ids = result.boxes.id.cpu().numpy().astype(int)

            for box, conf, raw_tid in zip(boxes, confs, ids):
                tid = int(raw_tid)
                x1, y1, x2, y2 = map(int, box)
                bw, bh = max(0, x2 - x1), max(0, y2 - y1)
                area_px = bw * bh
                area_frac = area_px / (w * h) if w * h > 0 else 0.0
                size_cat = categorise_size(area_frac)

                if tid not in tracks:
                    tracks[tid] = {
                        "track_id": tid,
                        "class_name": "possible defect",
                        "confidence": float(conf),
                        "bbox": [x1, y1, x2, y2],
                        "width_px": bw, "height_px": bh,
                        "area_px": area_px, "area_frac": area_frac,
                        "size_cat": size_cat,
                        "first_seen_s": ts,
                        "frame_count": 1,
                    }
                else:
                    t = tracks[tid]
                    t["frame_count"] += 1
                    if ts < t["first_seen_s"]:
                        t["first_seen_s"] = ts
                    if conf > t["confidence"]:
                        # Keep the highest-confidence sighting as the
                        # representative box/size for this track.
                        t.update({
                            "confidence": float(conf), "bbox": [x1, y1, x2, y2],
                            "width_px": bw, "height_px": bh,
                            "area_px": area_px, "area_frac": area_frac,
                            "size_cat": size_cat,
                        })

        unique_defects = sorted(tracks.values(), key=lambda t: t["first_seen_s"])
        severity = classify_severity(unique_defects)

        if unique_defects:
            biggest = max(unique_defects, key=lambda d: d["area_px"])
            profile = {
                "count":         len(unique_defects),
                "size_cat":      biggest["size_cat"],
                "max_conf":      max(d["confidence"] for d in unique_defects),
                "max_area_pct":  biggest["area_frac"] * 100,
                "max_width_px":  biggest["width_px"],
                "max_height_px": biggest["height_px"],
            }
        else:
            profile = {"count": 0, "size_cat": "none", "max_conf": 0,
                       "max_area_pct": 0, "max_width_px": 0, "max_height_px": 0}

        advisory = build_advisory(severity, profile)

        return {
            "id":                  uuid.uuid4().hex[:12],
            "timestamp":           datetime.now().isoformat(),
            "video_path":          str(video_path),
            "duration_s":          duration_s,
            "fps":                 fps,
            "frames_analyzed":     frames_processed,
            "truncated":           total_frames > frames_processed,
            "unique_defect_count": len(unique_defects),
            "severity":            severity,
            "detections":          unique_defects,
            "advisory":            advisory,
            "crack_profile":       profile,
            "model_used":          str(self.model_path),
            "conf_threshold":      self.conf_threshold,
        }

    def _draw(self, img, detections, severity, advisory, profile) -> np.ndarray:
        h, w   = img.shape[:2]
        color  = SEV_COLORS.get(severity, (50, 200, 50))

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf  = det["confidence"]
            size_c = det["size_cat"]

            # Main bounding box (thickness varies with size)
            thick = 4 if size_c in ("large","medium") else 2
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)

            # Corner accent lines
            cl = min(18, (x2-x1)//5, (y2-y1)//5)
            ct = thick + 1
            for (cx, cy, dx, dy) in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(img, (cx,cy), (cx+dx*cl, cy),    color, ct)
                cv2.line(img, (cx,cy), (cx, cy+dy*cl),    color, ct)

            # Label: "CRACK  96%  [LARGE]"
            size_label = size_c.upper()
            txt = f"CRACK  {conf:.0%}  [{size_label}]"
            font = cv2.FONT_HERSHEY_SIMPLEX
            fs   = 0.55
            (tw, th), _ = cv2.getTextSize(txt, font, fs, 2)
            pad  = 5
            lx   = x1
            ly   = max(0, y1 - th - pad*2)
            cv2.rectangle(img, (lx, ly), (lx+tw+pad*2, y1), color, -1)
            cv2.putText(img, txt, (lx+pad, y1-pad),
                        font, fs, (255,255,255), 2, cv2.LINE_AA)

        # ── Top info banner ────────────────────────────────────
        banner_h = 54
        banner   = np.zeros((banner_h, w, 3), dtype=np.uint8)

        bg = {
            "CRITICAL": (0,0,150), "HIGH":(0,70,180),
            "MODERATE": (0,120,160), "LOW":(30,110,30), "NO_CRACK":(20,100,20),
        }
        banner[:] = bg.get(severity, (30,30,30))
        # darken top half for gradient feel
        banner[:banner_h//2] = (banner[:banner_h//2] * 0.65).astype(np.uint8)

        n    = len(detections)
        conf = profile.get("max_conf", 0)
        size = profile.get("size_cat","—").upper()

        l1 = f"  {advisory['icon']}  {severity.replace('_',' ')}  |  {n} crack(s)  |  max conf: {conf:.1%}  |  largest: {size}"
        l2 = f"  {advisory['heading']}"

        cv2.putText(banner, l1, (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(banner, l2, (8, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200,200,200), 1, cv2.LINE_AA)

        return np.vstack([banner, img])
    