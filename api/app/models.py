"""
ORM models for the persistent report store.

Schema note on severity (see project audit, section J / F):
`SeverityAssessment` deliberately keeps two separate groups of columns —
`ai_*` (always populated by the detector pipeline) and `engineering_*`
(NULL until a qualified human writes to it via POST /reports/{id}/verify).
The API and PDF layer must never merge these into one field — that
separation is the whole point.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from .database import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(32), primary_key=True, default=new_id)
    status = Column(String(20), nullable=False, default="submitted")
    # submitted -> (duplicate | under_review | verified | dismissed | escalated)
    source = Column(String(20), nullable=False, default="upload")  # upload | camera
    original_filename = Column(String(255), nullable=True)
    reporter_contact = Column(String(255), nullable=True)  # optional, anonymous by default
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Duplicate-report clustering (see ../dedup.py). NULL until a match is
    # found; once found, every report in the cluster shares the *first*
    # report's id as cluster_id (that report's own cluster_id stays NULL —
    # it's the leader). A report with cluster_id set and status="duplicate"
    # is a re-report of an already-known physical defect, not a new one.
    cluster_id = Column(String(32), ForeignKey("reports.id"), nullable=True)

    media = relationship("Media", back_populates="report", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="report", cascade="all, delete-orphan")
    location = relationship("Location", back_populates="report", uselist=False, cascade="all, delete-orphan")
    severity = relationship("SeverityAssessment", back_populates="report", uselist=False, cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"

    id = Column(String(32), primary_key=True, default=new_id)
    report_id = Column(String(32), ForeignKey("reports.id"), nullable=False)
    role = Column(String(20), nullable=False)  # original | annotated
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    phash = Column(String(16), nullable=True)  # 64-bit average hash, hex-encoded — see ../dedup.py
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    report = relationship("Report", back_populates="media")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(32), primary_key=True, default=new_id)
    report_id = Column(String(32), ForeignKey("reports.id"), nullable=False)
    class_name = Column(String(50), nullable=False, default="crack")
    confidence = Column(Float, nullable=False)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)
    width_px = Column(Integer, nullable=False)
    height_px = Column(Integer, nullable=False)
    area_px = Column(Integer, nullable=False)
    area_frac = Column(Float, nullable=False)
    size_cat = Column(String(20), nullable=False)  # hairline | small | medium | large

    report = relationship("Report", back_populates="detections")


class Location(Base):
    __tablename__ = "locations"

    id = Column(String(32), primary_key=True, default=new_id)
    report_id = Column(String(32), ForeignKey("reports.id"), nullable=False, unique=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    source = Column(String(20), nullable=True)  # gps | manual
    captured_at = Column(DateTime(timezone=True), nullable=True)
    nearest_station = Column(String(255), nullable=True)  # populated later by a geocoding step, not yet wired up

    report = relationship("Report", back_populates="location")


class SeverityAssessment(Base):
    __tablename__ = "severity_assessments"

    id = Column(String(32), primary_key=True, default=new_id)
    report_id = Column(String(32), ForeignKey("reports.id"), nullable=False, unique=True)

    # ── AI-estimated (always populated by the pipeline, never edited by a human) ──
    ai_severity = Column(String(20), nullable=False)  # NO_CRACK | LOW | MODERATE | HIGH | CRITICAL
    ai_max_confidence = Column(Float, nullable=False, default=0.0)
    ai_detection_count = Column(Integer, nullable=False, default=0)
    ai_heading = Column(String(255), nullable=True)
    ai_risk_summary = Column(Text, nullable=True)
    ai_actions = Column(JSON, nullable=True)  # list[str]
    ai_timeline = Column(String(255), nullable=True)
    ai_authority = Column(String(255), nullable=True)
    ai_model_path = Column(String(500), nullable=True)
    ai_conf_threshold = Column(Float, nullable=True)

    # ── Engineering assessment — NULL until a verified human fills it in ──
    engineering_severity = Column(String(20), nullable=True)
    engineering_notes = Column(Text, nullable=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    report = relationship("Report", back_populates="severity")
