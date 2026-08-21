"""
RailGuard API — FastAPI service.

Additive to the original Flask app: app.py/detector.py/templates/ are
untouched. This service reuses detector.py's CrackDetector directly and
adds: Postgres persistence, stored GPS, an AI/engineering severity
split, PDF generation, rate limiting, and env-based secrets.

Run:
    cd api
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import PROJECT_ROOT, settings
from .database import Base, engine
from .ratelimit import limiter
from .routers import detect, reports

app = FastAPI(title="RailGuard API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # never "*" — configured via .env
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(detect.router)
app.include_router(reports.router)

# Serve stored evidence images. Uploads live under api/storage/uploads;
# annotated frames are written by detector.py into the original
# project's static/results directory and served from there unchanged.
app.mount("/media/uploads", StaticFiles(directory=str(PROJECT_ROOT / "api" / "storage" / "uploads")), name="uploads")
app.mount("/media/results", StaticFiles(directory=str(PROJECT_ROOT / "static" / "results")), name="results")


@app.on_event("startup")
def on_startup():
    # MVP: create tables directly. A real migration tool (Alembic) should
    # replace this before the schema needs to evolve under live data.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
