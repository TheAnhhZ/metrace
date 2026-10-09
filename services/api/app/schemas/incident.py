# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Requests and responses for complaints, incidents, locks and close requests."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComplaintChannel, MealSlot


class _Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ComplaintIn(BaseModel):
    delivery_point_id: uuid.UUID
    channel: ComplaintChannel = ComplaintChannel.CSKH
    service_date: date
    meal_slot: MealSlot
    affected_count: int = Field(0, ge=0)
    description: str = Field("", max_length=2000)


class ComplaintOut(_Read):
    id: uuid.UUID
    code: str
    customer_org_id: uuid.UUID
    delivery_point_id: uuid.UUID
    channel: str
    service_date: date
    meal_slot: str
    affected_count: int
    description: str
    status: str
    reported_by: str
    sla_due_at: datetime
    sla_breached: bool
    created_at: datetime


class ClusterSuggestion(BaseModel):
    batch_id: uuid.UUID
    batch_code: str
    dish: str
    n_complaints: int
    n_points: int
    complaint_ids: list[uuid.UUID]
    upstream: list[dict[str, Any]] = Field(description="Lots and intermediate batches behind this batch")


class SuspectRef(BaseModel):
    type: Literal["batch", "lot", "supplier"]
    id: uuid.UUID


class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    complaint_ids: list[uuid.UUID] = []


class ConfirmSuspectsIn(BaseModel):
    nodes: list[SuspectRef] = Field(min_length=1)
    lock_lots: bool = True


class LockOut(_Read):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    active: bool
    created_by: str
    created_at: datetime
    released_by: str | None
    released_at: datetime | None


class CloseRequestIn(BaseModel):
    note: str = Field("", max_length=2000)


class CloseRequestOut(_Read):
    id: uuid.UUID
    incident_id: uuid.UUID
    requested_by: str
    requested_at: datetime
    note: str
    status: str
    decided_by: str | None
    decided_at: datetime | None


class IncidentOut(_Read):
    id: uuid.UUID
    code: str
    title: str
    status: str
    suspects: list[dict[str, Any]]
    opened_by: str
    opened_at: datetime
    closed_at: datetime | None
    escalated: bool
    process_instance_id: str | None


class IncidentDetailOut(IncidentOut):
    server_now: datetime
    complaints: list[ComplaintOut]
    locks: list[LockOut]
    close_requests: list[CloseRequestOut]
    notices: list[dict[str, Any]]
    shipments: list[dict[str, Any]]


class LockResultOut(BaseModel):
    incident: IncidentOut
    targets: list[str]
    held_shipments: list[uuid.UUID]
    already_dispatched: list[uuid.UUID]
    delivery_points: list[uuid.UUID]
    audit_head: dict[str, Any]
    elapsed_ms: int
