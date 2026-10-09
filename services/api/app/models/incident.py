# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Complaints, incidents, locks, four-eyes close requests and recall notices."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UuidPrimaryKey
from app.models.enums import (
    CloseRequestStatus,
    ComplaintChannel,
    ComplaintStatus,
    IncidentStatus,
    LockTargetType,
    MealSlot,
    one_of,
)


class Complaint(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "complaint"
    __table_args__ = (
        one_of("channel", ComplaintChannel),
        one_of("status", ComplaintStatus),
        one_of("meal_slot", MealSlot),
        Index(
            "ix_complaint_sla_open", "sla_due_at", postgresql_where=text("NOT sla_breached AND status <> 'resolved'")
        ),
    )

    code: Mapped[str] = mapped_column(String(40), unique=True)
    customer_org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_org.id"), index=True)
    delivery_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_point.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    service_date: Mapped[date] = mapped_column(Date)
    meal_slot: Mapped[str] = mapped_column(String(20))
    affected_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=ComplaintStatus.OPEN)
    reported_by: Mapped[str] = mapped_column(String(100))
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)


class Incident(UuidPrimaryKey, Timestamps, Base):
    """Status is owned by the API (Flowable never writes back)."""

    __tablename__ = "incident"
    __table_args__ = (one_of("status", IncidentStatus),)

    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default=IncidentStatus.OPEN)
    suspects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    opened_by: Mapped[str] = mapped_column(String(100))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    process_instance_id: Mapped[str | None] = mapped_column(String(64))
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    # Should: AI-drafted report. A DRAFT only; QA edits and approves, nothing acts on it.
    report_draft: Mapped[str | None] = mapped_column(Text)
    report_model: Mapped[str | None] = mapped_column(String(60))
    report_prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    report_final: Mapped[str | None] = mapped_column(Text)
    report_approved_by: Mapped[str | None] = mapped_column(String(100))
    report_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentComplaint(Base):
    __tablename__ = "incident_complaint"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id", ondelete="CASCADE"), primary_key=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaint.id"), primary_key=True)


class Lock(UuidPrimaryKey, Base):
    """A node is locked while ANY active lock exists on it; each incident releases only its own."""

    __tablename__ = "lock"
    __table_args__ = (
        one_of("target_type", LockTargetType),
        Index(
            "uq_lock_active_per_incident",
            "incident_id",
            "target_type",
            "target_id",
            unique=True,
            postgresql_where=text("active"),
        ),
        Index("ix_lock_active_target", "target_type", "target_id", postgresql_where=text("active")),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_by: Mapped[str | None] = mapped_column(String(100))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentCloseRequest(UuidPrimaryKey, Base):
    """Four-eyes: approved_by must differ from requested_by and hold the approver role."""

    __tablename__ = "incident_close_request"
    __table_args__ = (
        one_of("status", CloseRequestStatus),
        Index(
            "uq_close_request_pending",
            "incident_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id"), index=True)
    requested_by: Mapped[str] = mapped_column(String(100))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=CloseRequestStatus.PENDING)
    decided_by: Mapped[str | None] = mapped_column(String(100))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecallNotice(UuidPrimaryKey, Base):
    """One per (incident, delivery point). Carries the audit head as an external anchor."""

    __tablename__ = "recall_notice"
    __table_args__ = (UniqueConstraint("incident_id", "delivery_point_id", name="uq_recall_notice_point"),)

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id"), index=True)
    customer_org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_org.id"), index=True)
    delivery_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_point.id"))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    audit_seq: Mapped[int] = mapped_column(Integer)
    audit_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))
