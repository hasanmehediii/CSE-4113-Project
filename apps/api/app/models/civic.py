"""Relational source of truth. Flexible event payloads are projected to Mongo via an outbox."""

import time

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_id


def now():
    return int(time.time())


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    ward: Mapped[str | None] = mapped_column(String(30))


class Road(Base):
    __tablename__ = "roads"
    __table_args__ = (
        UniqueConstraint("area_id", "name", name="uq_road_area_name"),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="ck_road_coordinates",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    area_id: Mapped[str] = mapped_column(ForeignKey("areas.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class Category(Base):
    __tablename__ = "complaint_categories"
    __table_args__ = (
        CheckConstraint("base_priority BETWEEN 0 AND 100", name="ck_category_priority"),
    )
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    base_priority: Mapped[int] = mapped_column(Integer)


class WorkerApplication(Base):
    __tablename__ = "worker_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')", name="ck_application_status"
        ),
        CheckConstraint(
            "nid_digest IS NOT NULL OR nid_image_url IS NOT NULL", name="ck_application_identity"
        ),
        Index("ix_worker_review_queue", "status", "submitted_at"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # NID numbers are HMAC fingerprints, never plaintext or returned to clients.
    nid_digest: Mapped[str | None] = mapped_column(String(64), unique=True)
    nid_image_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    submitted_at: Mapped[int] = mapped_column(BigInteger, default=now)
    reviewed_at: Mapped[int | None] = mapped_column(BigInteger)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(String(1000))


class WorkerLocation(Base):
    __tablename__ = "worker_locations"
    __table_args__ = (
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="ck_worker_coordinates",
        ),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("kind IN ('complaint','road_update')", name="ck_complaint_kind"),
        CheckConstraint("condition IN ('bad','good','unknown')", name="ck_road_condition"),
        CheckConstraint(
            "status IN ('open','assigned','awaiting_confirmation','resolved','disputed','false')",
            name="ck_complaint_status",
        ),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="ck_complaint_coordinates",
        ),
        Index("ix_complaints_queue", "status", "category_code", "created_at"),
        Index("ix_complaints_road_time", "road_id", "created_at"),
        Index("ix_complaints_author_time", "author_id", "created_at"),
        Index("ix_complaints_created", "created_at"),
        Index("ix_complaints_incident", "incident_id"),
        Index(
            "ix_incident_candidates", "category_code", "updated_at",
            postgresql_where=text("kind = 'complaint' AND incident_id IS NULL"),
            sqlite_where=text("kind = 'complaint' AND incident_id IS NULL"),
        ),
        CheckConstraint(
            "incident_id IS NULL OR (kind = 'complaint' AND incident_id <> id)",
            name="ck_complaint_incident",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # NULL identifies the original report/incident. Additional reports reference it.
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"))
    road_id: Mapped[str | None] = mapped_column(ForeignKey("roads.id"))
    category_code: Mapped[str] = mapped_column(ForeignKey("complaint_categories.code"))
    kind: Mapped[str] = mapped_column(String(20), default="complaint")
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    condition: Mapped[str] = mapped_column(String(10), default="bad")
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now, onupdate=now)


class ComplaintImage(Base):
    __tablename__ = "complaint_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))


class ComplaintPrediction(Base):
    __tablename__ = "complaint_predictions"
    __table_args__ = (
        CheckConstraint("status IN ('pending','ready')", name="ck_prediction_status"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_prediction_confidence"
        ),
        Index("ix_prediction_retry", "status", "next_attempt_at"),
    )
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    predicted_category: Mapped[str | None] = mapped_column(ForeignKey("complaint_categories.code"))
    confidence: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(100))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[int] = mapped_column(BigInteger, default=now)
    classified_at: Mapped[int | None] = mapped_column(BigInteger)


class ComplaintVote(Base):
    __tablename__ = "complaint_votes"
    __table_args__ = (CheckConstraint("value IN (-1,1)", name="ck_complaint_vote"),)
    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)


class FalseReport(Base):
    __tablename__ = "complaint_false_reports"
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), primary_key=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    image_url: Mapped[str] = mapped_column(String(2048))
    comment: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','cancelled')", name="ck_assignment_status"
        ),
        CheckConstraint("source IN ('admin','system')", name="ck_assignment_source"),
        Index(
            "uq_assignment_active",
            "complaint_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_assignments_worker_status", "worker_id", "status", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(15), default="active")
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    completed_at: Mapped[int | None] = mapped_column(BigInteger)


class Resolution(Base):
    __tablename__ = "resolutions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','disputed')", name="ck_resolution_status"
        ),
        Index("ix_resolutions_complaint", "complaint_id", "created_at"),
        Index(
            "uq_resolution_current", "complaint_id", unique=True,
            postgresql_where=text("superseded_at IS NULL"),
            sqlite_where=text("superseded_at IS NULL"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id"), unique=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    comment: Mapped[str] = mapped_column(String(2000))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(15), default="pending")
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    confirmed_at: Mapped[int | None] = mapped_column(BigInteger)
    superseded_at: Mapped[int | None] = mapped_column(BigInteger)


class ResolutionVote(Base):
    __tablename__ = "resolution_votes"
    __table_args__ = (
        CheckConstraint("value IN (-1,1)", name="ck_resolution_vote"),
        CheckConstraint("value = 1 OR image_url IS NOT NULL", name="ck_dislike_evidence"),
    )
    resolution_id: Mapped[str] = mapped_column(ForeignKey("resolutions.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)


class ModerationCase(Base):
    __tablename__ = "moderation_cases"
    __table_args__ = (
        CheckConstraint("kind IN ('false_complaint','worker_dispute')", name="ck_moderation_kind"),
        CheckConstraint("status IN ('open','dismissed','actioned')", name="ck_moderation_status"),
        Index("ix_moderation_queue", "status", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    resolution_id: Mapped[str | None] = mapped_column(ForeignKey("resolutions.id"))
    # One case per source even when later votes are submitted concurrently.
    source_key: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(15), default="open")
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[int | None] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(1000))


class PointEntry(Base):
    __tablename__ = "point_entries"
    __table_args__ = (Index("ix_point_entries_account", "user_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(120), unique=True)
    complaint_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"))
    resolution_id: Mapped[str | None] = mapped_column(ForeignKey("resolutions.id"))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_pending", "delivered_at", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    delivered_at: Mapped[int | None] = mapped_column(BigInteger)
