# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Retained samples: store with a QR seal (P4 minimum), list for the locker
screen, discard only after the retention window and never during an incident."""

import io
import secrets
import uuid
from datetime import date, time

import segno
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import local_datetime, utcnow
from app.core.database import get_or_404
from app.core.errors import AppError
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.cooking import CookingBatch, Dish, Menu, RetainedSample
from app.models.enums import BatchStatus, SampleStatus
from app.rules.sample_rules import check_sample_discard, check_sample_quantity, eligible_discard_at
from app.rules.thresholds import load_thresholds
from app.schemas.kitchen_operations import SampleIn
from app.services import lock_guard
from app.services.poka_yoke_logger import enforce


def _meal_end(session: Session, batch: CookingBatch):
    end = session.scalar(
        select(func.max(Menu.meal_end_at)).where(
            Menu.service_date == batch.service_date, Menu.meal_slot == batch.meal_slot
        )
    )
    return end or local_datetime(batch.service_date, time(23, 59))


def store_sample(session: Session, principal: Principal, req: SampleIn) -> RetainedSample:
    batch = get_or_404(session, CookingBatch, req.batch_id, "batch")
    if batch.status != BatchStatus.FINISHED:
        raise AppError(409, ReasonCode.CONFLICT, "Only a finished batch can be sampled")
    dish = session.get(Dish, batch.dish_id)
    th = load_thresholds(session)
    enforce(session, check_sample_quantity(dish.kind, req.qty_g, req.qty_ml, th), principal, "batch", batch.id)

    now = utcnow()
    meal_end = _meal_end(session, batch)
    sample = RetainedSample(
        batch_id=batch.id,
        qty_g=req.qty_g if dish.kind != "liquid" else None,
        qty_ml=req.qty_ml if dish.kind == "liquid" else None,
        seal_code=f"S-{secrets.token_urlsafe(6)}",
        fridge_asset_id=req.fridge_asset_id,
        stored_at=now,
        stored_by=principal.username,
        meal_end_at=meal_end,
        eligible_discard_at=eligible_discard_at(now, meal_end, th),
    )
    session.add(sample)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="sample.stored",
        entity_type="sample",
        entity_id=sample.id,
        payload={"batch": batch.batch_code, "seal": sample.seal_code},
    )
    session.commit()
    return sample


def discard_sample(session: Session, principal: Principal, sample_id: uuid.UUID) -> RetainedSample:
    sample = get_or_404(session, RetainedSample, sample_id, "sample", for_update=True)
    if sample.status != SampleStatus.STORED:
        raise AppError(409, ReasonCode.CONFLICT, "Sample already discarded")
    enforce(
        session,
        check_sample_discard(sample.eligible_discard_at, utcnow(), load_thresholds(session)),
        principal,
        "sample",
        sample.id,
    )
    lock_guard.assert_sample_discard_allowed(session, principal, sample.id, session.get(CookingBatch, sample.batch_id))
    sample.status = SampleStatus.DISCARDED
    sample.discarded_at = utcnow()
    sample.discarded_by = principal.username
    append_audit(
        session,
        actor=principal.username,
        action="sample.discarded",
        entity_type="sample",
        entity_id=sample.id,
        payload={"seal": sample.seal_code},
    )
    session.commit()
    return sample


def list_samples(session: Session, day: date) -> list[RetainedSample]:
    return session.scalars(
        select(RetainedSample)
        .join(CookingBatch, CookingBatch.id == RetainedSample.batch_id)
        .where(CookingBatch.service_date == day)
        .order_by(RetainedSample.stored_at)
    ).all()


def seal_svg(session: Session, sample_id: uuid.UUID) -> bytes:
    sample = get_or_404(session, RetainedSample, sample_id, "sample")
    out = io.BytesIO()
    segno.make(sample.seal_code, error="m").save(out, kind="svg", scale=6, border=2)
    return out.getvalue()
