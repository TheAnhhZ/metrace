# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Meal-service checklist computed from data (the kitchen state machine lives in
the API, no BPMN): menu -> received -> cooked -> samples -> Mẫu 3 -> dispatched."""

from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_time import local_datetime
from app.models.cooking import CookingBatch, Menu, MenuItem, PortionCheck, RetainedSample
from app.models.enums import BatchStatus, SampleStatus
from app.models.shipment import Shipment, ShipmentItem
from app.models.supplier_and_lots import Receiving


def meal_status(session: Session, day: date, slot: str) -> list[dict]:
    dishes = set(
        session.scalars(select(MenuItem.dish_id).join(Menu).where(Menu.service_date == day, Menu.meal_slot == slot))
    )
    day_start = local_datetime(day, time(0, 0))
    received = session.scalar(
        select(func.count())
        .select_from(Receiving)
        .where(Receiving.received_at >= day_start, Receiving.received_at < day_start + timedelta(days=1))
    )
    batches = session.scalars(
        select(CookingBatch).where(CookingBatch.service_date == day, CookingBatch.meal_slot == slot)
    ).all()
    finished = {b.dish_id for b in batches if b.status == BatchStatus.FINISHED}
    served = [b for b in batches if b.status == BatchStatus.FINISHED and b.dish_id in dishes]
    sampled = set(
        session.scalars(
            select(RetainedSample.batch_id).where(
                RetainedSample.batch_id.in_([b.id for b in served]), RetainedSample.status == SampleStatus.STORED
            )
        )
    )
    shipments = session.scalars(select(Shipment).where(Shipment.service_date == day, Shipment.meal_slot == slot)).all()
    items = session.execute(
        select(ShipmentItem.shipment_id, ShipmentItem.batch_id).where(
            ShipmentItem.shipment_id.in_([s.id for s in shipments])
        )
    ).all()
    checked = set(
        session.execute(
            select(PortionCheck.shipment_id, PortionCheck.batch_id).where(
                PortionCheck.shipment_id.in_([s.id for s in shipments])
            )
        ).all()
    )
    gone = [s for s in shipments if s.status in ("dispatched", "delivered")]
    return [
        {"key": "menu", "done": bool(dishes), "detail": {"dishes": len(dishes)}},
        {"key": "received", "done": received > 0, "detail": {"receivings_today": received}},
        {
            "key": "cooked",
            "done": bool(dishes) and dishes <= finished,
            "detail": {"finished": len(dishes & finished), "planned": len(dishes)},
        },
        {
            "key": "samples",
            "done": bool(served) and len(sampled) == len(served),
            "detail": {"sampled": len(sampled), "served_batches": len(served)},
        },
        {
            "key": "form3",
            "done": bool(items) and all(tuple(i) in checked for i in items),
            "detail": {"checked": sum(tuple(i) in checked for i in items), "items": len(items)},
        },
        {
            "key": "dispatched",
            "done": bool(shipments) and len(gone) == len(shipments),
            "detail": {
                "dispatched": len(gone),
                "shipments": len(shipments),
                "held": sum(s.status == "held" for s in shipments),
            },
        },
    ]
