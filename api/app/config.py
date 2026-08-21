"""
Central configuration — every secret / tunable value is read from the
environment (via a .env file locally, or real env vars in production).
Nothing here is hardcoded, unlike the original app.py's `app.secret_key`.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = API_DIR.parent  # .../railway_crack_detection advanced new version


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(API_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────
    # Postgres in normal use; sqlite is only for a dependency-free local
    # smoke test (see README) and is not what production should run on.
    database_url: str = "postgresql+psycopg2://railguard:railguard@localhost:5432/railguard"

    # ── CORS ────────────────────────────────────────────────────
    # Comma-separated list of allowed origins. No wildcard by default —
    # the original app used CORS(app) with no restriction at all.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Uploads ─────────────────────────────────────────────────
    max_upload_mb: int = 15
    allowed_extensions: str = ".jpg,.jpeg,.png,.bmp,.tif,.tiff,.webp"
    max_video_mb: int = 100
    max_video_frames: int = 450  # ~15s at 30fps — hard runtime cap, see detector.py

    # ── Rate limiting (slowapi / limits syntax) ────────────────
    rate_limit_detect: str = "10/minute"
    rate_limit_report: str = "6/minute"
    rate_limit_pdf: str = "20/minute"
    # Video processing is much heavier per-request than an image (runs
    # synchronously — see routers/videos.py for why) — a tighter limit.
    rate_limit_video: str = "3/minute"

    # ── Detection ───────────────────────────────────────────────
    conf_threshold: float = 0.55
    model_path: str = ""  # empty → CrackDetector auto-discovers best.pt

    # ── Optional Claude AI-analysis passthrough (unchanged from ai_analysis.py) ──
    anthropic_api_key: str = ""

    # ── Admin auth ──────────────────────────────────────────────
    # Gates POST /api/reports/{id}/verify — the one endpoint that records
    # a human engineering assessment and must not be publicly writable.
    # Empty by default so a misconfigured deployment fails CLOSED (every
    # verify request is rejected) rather than accidentally open.
    admin_token: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extension_set(self) -> set:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}


settings = Settings()
