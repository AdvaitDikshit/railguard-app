"""Pydantic request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Inbound ─────────────────────────────────────────────────────

class LocationIn(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    accuracy_m: Optional[float] = None
    source: Optional[str] = "gps"  # gps | manual


class VerifyIn(BaseModel):
    """Human/authority verification — the only way engineering_* fields get set."""
    engineering_severity: str = Field(..., pattern="^(NO_CRACK|LOW|MODERATE|HIGH|CRITICAL)$")
    engineering_notes: str = Field(..., min_length=1, max_length=4000)
    verified_by: str = Field(..., min_length=1, max_length=255)
    new_status: Optional[str] = Field(
        default=None,
        pattern="^(under_review|verified|dismissed|escalated|duplicate)$",
    )


# ── Outbound ────────────────────────────────────────────────────

class DetectionOut(BaseModel):
    class_name: str
    confidence: float
    bbox: List[int]
    width_px: int
    height_px: int
    area_frac: float
    size_cat: str

    model_config = {"from_attributes": True}


class LocationOut(BaseModel):
    lat: Optional[float]
    lng: Optional[float]
    accuracy_m: Optional[float]
    source: Optional[str]
    nearest_station: Optional[str]

    model_config = {"from_attributes": True}


class SeverityOut(BaseModel):
    ai_severity: str
    ai_max_confidence: float
    ai_detection_count: int
    ai_heading: Optional[str]
    ai_risk_summary: Optional[str]
    ai_actions: Optional[List[str]]
    ai_timeline: Optional[str]
    ai_authority: Optional[str]

    engineering_severity: Optional[str]
    engineering_notes: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    status: str
    source: str
    created_at: datetime
    original_url: Optional[str] = None
    annotated_url: Optional[str] = None
    location: Optional[LocationOut] = None
    severity: Optional[SeverityOut] = None
    detections: List[DetectionOut] = []
    cluster_id: Optional[str] = None  # set when this report was matched as a
                                       # duplicate of an earlier one — see dedup.py

    model_config = {"from_attributes": True}


class ReportSummaryOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    ai_severity: Optional[str] = None
    detection_count: Optional[int] = None
    annotated_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    model_config = {"from_attributes": True}


# ── Video ───────────────────────────────────────────────────────

class VideoDetectionOut(BaseModel):
    track_id: int
    class_name: str
    confidence: float
    bbox: List[int]
    size_cat: str
    first_seen_s: float
    frame_count: int

    model_config = {"from_attributes": True}


class VideoReportOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    video_url: Optional[str] = None
    duration_s: Optional[float] = None
    fps: Optional[float] = None
    frames_analyzed: Optional[int] = None
    location: Optional[LocationOut] = None
    severity: Optional[SeverityOut] = None
    detections: List[VideoDetectionOut] = []

    model_config = {"from_attributes": True}


class VideoSummaryOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    ai_severity: Optional[str] = None
    duration_s: Optional[float] = None
    unique_defect_count: Optional[int] = None

    model_config = {"from_attributes": True}
