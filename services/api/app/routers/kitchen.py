# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Kitchen flow endpoints (Mẫu 1-2, samples). Poka-yoke violations answer 422."""

import uuid
from datetime import date

from fastapi import Depends, Response
from sqlalchemy import select

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role
from app.core.business_time import service_date, utcnow
from app.core.database import DbSession
from app.models.cooking import BatchInput, CookingBatch
from app.schemas.kitchen_operations import (
    BatchFinishIn,
    BatchIn,
    BatchInputIn,
    BatchOut,
    ReceivingIn,
    ReceivingOut,
    SampleIn,
    SampleListOut,
    SampleOut,
)
from app.services import cooking_service, receiving_service, sample_service

router = internal_router(prefix="/api/v1", tags=["kitchen"])

PROCUREMENT = [Depends(require_any_role({"procurement", "qa"}))]
CHEF = [Depends(require_any_role({"chef"}))]
SAMPLER = [Depends(require_any_role({"chef", "qa"}))]
QA = [Depends(require_any_role({"qa"}))]


@router.post("/receivings", response_model=ReceivingOut, status_code=201, dependencies=PROCUREMENT)
def create_receiving(req: ReceivingIn, session: DbSession, principal: CurrentPrincipal):
    return receiving_service.create_receiving(session, principal, req)


@router.post("/batches", response_model=BatchOut, status_code=201, dependencies=CHEF)
def start_batch(req: BatchIn, session: DbSession, principal: CurrentPrincipal):
    return cooking_service.create_batch(session, principal, req)


@router.get("/batches", response_model=list[BatchOut])
def list_batches(session: DbSession, day: date | None = None):
    return session.scalars(
        select(CookingBatch)
        .where(CookingBatch.service_date == (day or service_date()))
        .order_by(CookingBatch.batch_code)
    ).all()


@router.post("/batches/{batch_id}/inputs", status_code=201, dependencies=CHEF)
def add_batch_input(batch_id: uuid.UUID, req: BatchInputIn, session: DbSession, principal: CurrentPrincipal):
    row: BatchInput = cooking_service.add_input(session, principal, batch_id, req)
    return {
        "id": row.id,
        "batch_id": row.batch_id,
        "lot_id": row.lot_id,
        "input_batch_id": row.input_batch_id,
        "qty_kg": row.qty_kg,
    }


@router.post("/batches/{batch_id}/finish", response_model=BatchOut, dependencies=CHEF)
def finish_batch(batch_id: uuid.UUID, req: BatchFinishIn, session: DbSession, principal: CurrentPrincipal):
    return cooking_service.finish_batch(session, principal, batch_id, req)


@router.post("/samples", response_model=SampleOut, status_code=201, dependencies=SAMPLER)
def store_sample(req: SampleIn, session: DbSession, principal: CurrentPrincipal):
    return sample_service.store_sample(session, principal, req)


@router.get("/samples", response_model=SampleListOut)
def list_samples(session: DbSession, day: date | None = None):
    samples = sample_service.list_samples(session, day or service_date())
    return SampleListOut(server_now=utcnow(), samples=[SampleOut.model_validate(s) for s in samples])


@router.get("/samples/{sample_id}/seal.svg", response_class=Response)
def sample_seal(sample_id: uuid.UUID, session: DbSession):
    return Response(sample_service.seal_svg(session, sample_id), media_type="image/svg+xml")


@router.post("/samples/{sample_id}/discard", response_model=SampleOut, dependencies=QA)
def discard_sample(sample_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    return sample_service.discard_sample(session, principal, sample_id)
