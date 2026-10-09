# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Apply and release incident locks with strong consistency, no message bus.

`apply` takes the same advisory lock as every guard, walks lineage, writes the
locks and moves pending shipments to HELD in ONE transaction. Shipments that
already left get recall notices (outbox -> worker). Incomplete lineage fails
closed. Each incident releases only its own locks.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import service_date, utcnow
from app.core.errors import AppError
from app.core.outbox import emit
from app.core.reason_codes import ReasonCode
from app.core.settings import get_settings
from app.models.enums import ShipmentStatus
from app.models.incident import Incident, Lock
from app.models.shipment import Shipment
from app.services import lineage_query
from app.services.lineage_query import NodeRef
from app.services.lock_guard import serialize_lock_decisions

LOCKABLE = ("batch", "lot", "supplier")


@dataclass
class LockResult:
    targets: list[str]
    held_shipments: list[uuid.UUID]
    already_dispatched: list[uuid.UUID]
    delivery_points: list[uuid.UUID]
    audit_head: tuple[int, str]
    elapsed_ms: int
    blast_radius: dict = field(default_factory=dict)
    truncated: bool = False  # walk hit a cap: every open shipment was held (fail closed)


def apply(session: Session, incident: Incident, suspects: list[NodeRef], lock_lots: bool, actor: str) -> LockResult:
    started = time.monotonic()
    serialize_lock_decisions(session)  # same key as every guard: no TOCTOU

    bad = [s.key for s in suspects if s.type not in LOCKABLE]
    if bad:
        raise AppError(
            422, ReasonCode.VALIDATION_ERROR, "Only batches, lots and suppliers can be locked", details={"invalid": bad}
        )
    targets = set(suspects)
    truncated = False
    batches = [s for s in suspects if s.type == "batch"]
    if lock_lots and batches:
        up = lineage_query.backward_many(session, batches, max_depth=lineage_query.MAX_DEPTH_CAP, max_nodes=5000)
        truncated |= up.truncated
        targets |= {n for n in up.nodes if n.type == "lot"}
    down = lineage_query.forward_many(session, sorted(targets), max_depth=lineage_query.MAX_DEPTH_CAP, max_nodes=5000)
    truncated |= down.truncated

    for target in sorted(targets):
        session.execute(
            insert(Lock)
            .values(
                id=uuid.uuid4(),
                incident_id=incident.id,
                target_type=target.type,
                target_id=target.id,
                active=True,
                created_by=actor,
            )
            .on_conflict_do_nothing(index_elements=["incident_id", "target_type", "target_id"], index_where=Lock.active)
        )
    shipment_ids = sorted(down.ids("shipment"))
    open_trucks = select(Shipment).where(Shipment.status.in_([ShipmentStatus.PLANNED, ShipmentStatus.READY]))
    if not truncated:
        open_trucks = open_trucks.where(Shipment.id.in_(shipment_ids))
    # Truncated walk = we may not see every affected truck: fail closed and hold ALL open ones.
    pending = session.scalars(open_trucks.order_by(Shipment.id).with_for_update()).all()
    for shipment in pending:
        shipment.status = ShipmentStatus.HELD
    held = [s.id for s in pending]
    gone = sorted(
        set(
            session.scalars(
                select(Shipment.id).where(
                    Shipment.id.in_(shipment_ids),
                    Shipment.status.in_([ShipmentStatus.DISPATCHED, ShipmentStatus.DELIVERED]),
                    Shipment.service_date >= recall_since(),
                )
            )
        )
    )

    head = append_audit(
        session,
        actor=actor,
        action="lock.applied",
        entity_type="incident",
        entity_id=incident.id,
        payload={"targets": sorted(t.key for t in targets), "held": held, "dispatched": gone, "truncated": truncated},
    )
    emit(
        session,
        "lock.applied",
        {"incident_id": incident.id, "audit_seq": head.seq, "audit_hash": head.hash},
        aggregate_type="incident",
        aggregate_id=incident.id,
    )
    return LockResult(
        targets=sorted(t.key for t in targets),
        held_shipments=held,
        already_dispatched=gone,
        delivery_points=sorted(down.ids("delivery_point")),
        audit_head=(head.seq, head.hash),
        elapsed_ms=int((time.monotonic() - started) * 1000),
        blast_radius={"batches": len(down.ids("batch")), "shipments": len(shipment_ids)},
        truncated=truncated,
    )


def recall_since():
    """Deliveries older than the recall window have been eaten long ago: no recall notice."""
    return service_date() - timedelta(days=get_settings().recall_window_days)


def release_for_incident(session: Session, incident_id: uuid.UUID, actor: str) -> int:
    """Release ONLY this incident's locks; another incident on the same lot keeps it locked."""
    serialize_lock_decisions(session)
    result = session.execute(
        update(Lock)
        .where(Lock.incident_id == incident_id, Lock.active)
        .values(active=False, released_by=actor, released_at=utcnow())
    )
    return result.rowcount
