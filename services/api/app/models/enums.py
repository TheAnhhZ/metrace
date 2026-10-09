# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Domain enumerations. Stored as text with CHECK constraints (no PG enum types,
so adding a value is a one-line migration)."""

from enum import StrEnum

from sqlalchemy import CheckConstraint


class StorageKind(StrEnum):
    CHILLED = "chilled"
    FROZEN = "frozen"
    DRY = "dry"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class ReceivingDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class LotStatus(StrEnum):
    IN_STOCK = "in_stock"
    USED_UP = "used_up"
    DISCARDED = "discarded"


class DishKind(StrEnum):
    SOLID = "solid"
    LIQUID = "liquid"


class MealSlot(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class BatchStatus(StrEnum):
    COOKING = "cooking"
    FINISHED = "finished"
    DISCARDED = "discarded"


class CustomerKind(StrEnum):
    SCHOOL = "school"
    FACTORY = "factory"


class AssetType(StrEnum):
    FRIDGE = "fridge"
    FREEZER = "freezer"
    COLD_ROOM = "cold_room"
    TRUCK = "truck"
    THERMOMETER = "thermometer"


class ShipmentStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    HELD = "held"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"


class SampleStatus(StrEnum):
    STORED = "stored"
    DISCARDED = "discarded"


class ComplaintChannel(StrEnum):
    PORTAL = "portal"
    PHONE = "phone"
    CSKH = "cskh"


class ComplaintStatus(StrEnum):
    OPEN = "open"
    LINKED = "linked"
    RESOLVED = "resolved"


class IncidentStatus(StrEnum):
    OPEN = "open"
    CONTAINED = "contained"
    CLOSED = "closed"


class LockTargetType(StrEnum):
    BATCH = "batch"
    LOT = "lot"
    SUPPLIER = "supplier"


class CloseRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BasisType(StrEnum):
    LAW = "law"
    GUIDANCE = "guidance"
    FIELD = "field"
    INTERNAL = "internal"


def one_of(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or f"{column}_valid")
