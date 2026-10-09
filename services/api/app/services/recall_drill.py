# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""#2 Recall drill: "if this node were bad, how fast could we find and stop everything?"

Traces both ways, previews the lock inside a SAVEPOINT that is rolled back (no
real lock, no notice), measures how many affected portions can be located at a
delivery point (coverage), and records the drill in the audit chain.
"""

import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.principal import Principal
from app.models.cooking import CookingBatch
from app.models.enums import ShipmentStatus
from app.models.incident import Incident
from app.models.shipment import Shipment, ShipmentItem
from app.services import lineage_query, lock_service
from app.services.lineage_query import NodeRef


def coverage(session: Session, batch_ids: set) -> dict:
    """Share of produced portions of the affected batches that LEFT the kitchen to a known
    delivery point (dispatched/delivered). Planned or held trucks are still in the kitchen.
    No affected portions at all => coverage is None (nothing to locate), not 100 %."""
    served = session.execute(
        select(CookingBatch.id, CookingBatch.batch_code, CookingBatch.portions_produced).where(
            CookingBatch.id.in_(batch_ids), CookingBatch.portions_produced > 0
        )
    ).all()
    shipped = dict(
        session.execute(
            select(ShipmentItem.batch_id, func.sum(ShipmentItem.portions))
            .join(Shipment, Shipment.id == ShipmentItem.shipment_id)
            .where(
                ShipmentItem.batch_id.in_([b.id for b in served]),
                Shipment.status.in_([ShipmentStatus.DISPATCHED, ShipmentStatus.DELIVERED]),
            )
            .group_by(ShipmentItem.batch_id)
        ).all()
    )
    produced = sum(b.portions_produced for b in served)
    located = sum(min(int(shipped.get(b.id, 0)), b.portions_produced) for b in served)
    return {
        "produced_portions": produced,
        "located_portions": located,
        "coverage_pct": round(100 * located / produced, 1) if produced else None,
        "batches": [
            {"batch": b.batch_code, "produced": b.portions_produced, "shipped": int(shipped.get(b.id, 0))}
            for b in served
        ],
    }


def run_drill(session: Session, principal: Principal, root: NodeRef) -> dict:
    started = time.monotonic()
    down = lineage_query.forward(session, root, **lock_service.WRITER_WALK)
    up = lineage_query.backward(session, root, **lock_service.WRITER_WALK)
    trace_ms = int((time.monotonic() - started) * 1000)

    preview = None
    if root.type in lock_service.LOCKABLE:
        savepoint = session.begin_nested()
        probe = Incident(
            code=f"DRILL-{int(time.time() * 1000)}",
            title="Recall drill (dry run)",
            opened_by=principal.username,
            suspects=[],
        )
        session.add(probe)
        session.flush()
        result = lock_service.apply(session, probe, [root], lock_lots=True, actor=principal.username)
        preview = {
            "would_hold": len(result.held_shipments),
            "already_out": len(result.already_dispatched),
            "delivery_points": len(result.delivery_points),
            "lock_ms": result.elapsed_ms,
        }
        savepoint.rollback()  # dry run: nothing is locked, no notice is sent

    cover = coverage(session, down.ids("batch"))
    summary = {
        "root": root.key,
        "trace_ms": trace_ms,
        "total_ms": int((time.monotonic() - started) * 1000),
        "forward": {t: len(down.ids(t)) for t in ("lot", "batch", "shipment", "delivery_point")},
        "backward": {t: len(up.ids(t)) for t in ("supplier", "lot", "batch")},
        "truncated": down.truncated or up.truncated,
        "lock_preview": preview,
        "coverage": cover,
    }
    head = append_audit(
        session,
        actor=principal.username,
        action="drill.run",
        entity_type=root.type,
        entity_id=root.id,
        payload={k: v for k, v in summary.items() if k != "coverage"} | {"coverage_pct": cover["coverage_pct"]},
    )
    session.commit()
    return {
        **summary,
        "audit_anchor": {"seq": head.seq, "hash": head.hash},
        "label": "Diễn tập: dữ liệu synthetic, không khóa thật, không gửi thông báo",
    }
