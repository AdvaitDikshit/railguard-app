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
| POST   | `/api/reports`              | Full pipeline: validate → detect → persist report + GPS          |
| GET    | `/api/reports`              | List recent reports (paginated)                                  |
| GET    | `/api/reports/{id}`         | Fetch one report, including detections/location/severity         |
| POST   | `/api/reports/{id}/verify`  | Record a human engineering assessment (separate from AI fields)  |
| GET    | `/api/reports/{id}/pdf`     | Generate and download the evidence PDF                           |
| GET    | `/health`                   | Liveness check                                                   |

## Example: submit a report with GPS

```bash
curl -X POST http://localhost:8000/api/reports \
  -F "file=@sample.jpg" \
  -F "source=camera" \
  -F "lat=18.5679" \
  -F "lng=73.9143" \
  -F "accuracy_m=12.5"
```

## What's intentionally NOT done here

- **No authentication.** `/api/reports/{id}/verify` (the human
  verification endpoint) must be placed behind real auth before any
  public launch — it's open here because auth wasn't in this
  implementation batch.
- **No video support** — image-only, per the current scope.
- **No duplicate-report clustering** — every submission creates a new
  report row; the geo/perceptual-hash dedup engine is a later phase.
- **No Alembic migrations** — `create_all()` on startup is an MVP
  shortcut, fine until the schema needs a real migration.
