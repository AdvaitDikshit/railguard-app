# RailGuard — Railway Track Safety Platform

Mini Project | MIT World Peace University, Pune
Department of Mechanical Robotics & Automation Engineering | 2025-26

AI-assisted visual screening for railway track defects. Started as a
YOLOv8 crack-detection demo; now growing into a public reporting
platform. **This is not a certified railway engineering inspection
system** — see [web/app/how-it-works](web/app/how-it-works/page.tsx)
for the full disclaimer.

## Architecture

Three parts, developed incrementally, each still runnable independently:

| Part | What it is | Where |
|---|---|---|
| **Original demo** | Single-user Flask app — upload an image, get a detection, in-memory history. Still functional, unmodified. | [`app.py`](app.py), [`detector.py`](detector.py), [`templates/`](templates/) |
| **API** | FastAPI service — Postgres-backed reports, GPS storage, AI-vs-human severity split, PDF generation, rate limiting. Reuses `detector.py` directly. | [`api/`](api/README.md) |
| **Web** | Next.js frontend for the API — upload/camera capture, live detection overlay, report history, PDF download. | [`web/`](web/README.md) |

```
Browser (web/, Next.js)
    ↓ HTTP
FastAPI (api/) ──imports──> detector.py (YOLOv8 + severity engine)
    ↓
Postgres (dev: SQLite) — reports, detections, locations, severity
```

## Running it

**Original demo (fastest way to see the model work):**
```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

**API + web (the current development path):**
```bash
pip install -r requirements.txt
pip install -r api/requirements.txt
cd api && cp .env.example .env && uvicorn app.main:app --reload --port 8000
# in a second terminal:
cd web && npm install && cp .env.local.example .env.local && npm run dev
# → http://localhost:3000 (requires the API running)
```
See [api/README.md](api/README.md) and [web/README.md](web/README.md) for details,
including running Postgres via `docker compose up -d` (or SQLite for a
dependency-free local check).

## Model

YOLOv8n, single-class ("crack") detector, trained on a merged Roboflow
railway-crack dataset. **Known issue, not yet fixed:** the currently
deployed `runs/detect/train/weights/best.pt` was trained before the
dataset's class labels were fully normalized to a single class — see
the note in [`detector.py`](detector.py) (`normalize_class_name`) for
what this means and what a retrain needs to fix. The dataset has also
had ~479 images with stock-photo watermarks (Alamy/Shutterstock) found
and quarantined out of `dataset/merged/` — see
`scripts/scan_watermarks.py` and `scripts/quarantine_watermarks.py`.

Trained model weights and the dataset itself are not included in this
repository — see `scripts/download_dataset.py` and
`scripts/train_model.py` to reproduce them.

## Status

Actively evolving from an academic YOLO demo toward a public reporting
platform. See project notes / commit history for the current phase.
Not deployed anywhere yet.
