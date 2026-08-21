# RailGuard API

A FastAPI service that sits **alongside** the original Flask app
(`app.py`, `detector.py`, `templates/index.html`) without modifying it.
It reuses `detector.py`'s `CrackDetector` class directly and adds:

- Real file-content image validation (not just filename extension)
- Postgres-backed persistence for reports/detections/locations/severity
  (replacing the original in-memory `sessions` dict + flat `history.json`)
- GPS actually captured **and stored** with each report
- A schema-level split between AI-estimated severity and a qualified
  human's engineering assessment — never the same field
- PDF evidence report generation with a mandatory disclaimer
- Per-route rate limiting
- Secrets read from environment / `.env`, never hardcoded

This is backend infrastructure only — the existing `templates/index.html`
UI is untouched, and this service has no UI of its own yet (see the
project roadmap for the Next.js frontend phase).

## Setup

From the **project root** (`railway_crack_detection advanced new version/`),
install the base dependencies once (YOLO/OpenCV/torch), then this
service's own dependencies:

```bash
pip install -r requirements.txt
pip install -r api/requirements.txt
```

Copy the env template and fill it in:

```bash
cd api
cp .env.example .env
```

Start Postgres locally (requires Docker):

```bash
docker compose up -d
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup (MVP approach — no
migrations tool yet; see the project roadmap for adding Alembic before
the schema needs to evolve under live data).

## Smoke test without Docker

If you don't want to stand up Postgres just to try it, set in `.env`:

```
DATABASE_URL=sqlite:///./railguard_dev.db
```

SQLAlchemy will use a local SQLite file instead. This is fine for local
testing only — production should run on Postgres as specified.

## Endpoints

| Method | Path                        | Purpose                                                        |
|--------|-----------------------------|------------------------------------------------------------------|
| POST   | `/api/detect`               | Stateless detection — validate, run YOLO, return result, no save |
| POST   | `/api/reports`              | Full pipeline: validate → detect → dedup check → persist report + GPS |
| GET    | `/api/reports`              | List recent reports (paginated), each carrying lat/lng for the map view |
| GET    | `/api/reports/{id}`         | Fetch one report, including detections/location/severity         |
| GET    | `/api/reports/{id}/cluster` | All reports believed to be the same physical defect as this one (see Duplicate detection below) |
| POST   | `/api/reports/{id}/verify`  | Record a human engineering assessment — requires `X-Admin-Token` header (see below) |
| GET    | `/api/reports/{id}/pdf`     | Generate and download the evidence PDF                           |
| POST   | `/api/videos`               | Video pipeline: validate → tracked detection → temporal aggregation → persist (see Video below) |
| GET    | `/api/videos`               | List video reports                                                |
| GET    | `/api/videos/{id}`          | Fetch one video report, including per-track detections            |
| GET    | `/health`                   | Liveness check                                                   |

Note: `POST /api/reports/{id}/verify` also works for video report ids —
it's generic over any report regardless of source.

## Example: submit a report with GPS

```bash
curl -X POST http://localhost:8000/api/reports \
  -F "file=@sample.jpg" \
  -F "source=camera" \
  -F "lat=18.5679" \
  -F "lng=73.9143" \
  -F "accuracy_m=12.5"
```

## Duplicate detection

If N people photograph the same physical crack, `POST /api/reports`
recognizes later submissions as the same defect instead of creating N
independent reports — see `app/dedup.py`. The rule: a 64-bit average
hash of the image (no extra dependency, computed with PIL) combined
with GPS proximity (within 75m). If either report is missing GPS, it
falls back to hash-only matching with a much stricter threshold. A
matched report gets `status: "duplicate"` and `cluster_id` pointing at
the original ("leader") report; `GET /api/reports/{id}/cluster` lists
every report in that cluster from either member's id.

This is a simple, explainable heuristic — not a learned embedding
model — which is the right tradeoff at this project's scale: it's easy
to reason about why two reports were (or weren't) linked.

## Video

`POST /api/videos` runs `detector.py`'s `CrackDetector.detect_video()`
— YOLO + ByteTrack (via ultralytics' built-in `.track()`) across every
frame, aggregated by track id so a crack visible across 80 consecutive
frames is reported once, with the timestamp it was first seen, not 80
separate detections.

```bash
curl -X POST http://localhost:8000/api/videos \
  -F "file=@clip.mp4" -F "lat=18.5679" -F "lng=73.9143"
```

**Runs synchronously, inside the request.** A real production
deployment should queue this (Redis/RQ or similar) rather than block a
request thread for the duration of processing — this project doesn't
have that infrastructure yet, so it's a documented simplification, not
an oversight. `MAX_VIDEO_FRAMES` (config.py, default 450 ≈ 15s at
30fps) is the safety valve that bounds how long any single request can
take without a queue in front of it — longer clips are truncated, not
slowly processed in full.

**Not yet built:** duplicate-clustering for video reports (`dedup.py`
was designed around single-image perceptual hashing, not video) and
PDF export for video reports (`pdf_service.py` expects a single
before/after image pair, not a multi-timestamp video summary).

## Verifying a report (admin)

`POST /api/reports/{id}/verify` requires an `X-Admin-Token` header
matching `ADMIN_TOKEN` in `.env`. Generate a token with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

If `ADMIN_TOKEN` is unset, the endpoint fails closed (503) rather than
silently allowing writes. This is a single shared token, not a user
account system — proportionate to gating one write path, not a reason
to add full auth to the rest of the (intentionally anonymous) public
reporting flow.

```bash
curl -X POST http://localhost:8000/api/reports/{id}/verify \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: <your token>" \
  -d '{"engineering_severity":"HIGH","engineering_notes":"...","verified_by":"J. Rao"}'
```

## What's intentionally NOT done here

- **No video support** — image-only, per the current scope.
- **No duplicate-report clustering** — every submission creates a new
  report row; the geo/perceptual-hash dedup engine is a later phase.
- **No Alembic migrations** — `create_all()` on startup is an MVP
  shortcut, fine until the schema needs a real migration.
