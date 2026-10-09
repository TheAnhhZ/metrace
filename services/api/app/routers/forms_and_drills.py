# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""#1 printable Mẫu 2 (PDF) and #2 recall drills."""

import uuid

from fastapi import Depends, Response
from pydantic import BaseModel

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role
from app.core.database import DbSession
from app.core.errors import not_found
from app.pdf_forms.form_2_cooking import form_2_pdf
from app.schemas.lineage import LineageNodeType
from app.services.lineage_presenter import resolve_node
from app.services.recall_drill import run_drill

router = internal_router(prefix="/api/v1", tags=["forms and drills"])


class DrillIn(BaseModel):
    type: LineageNodeType
    ref: str  # UUID or business code


@router.get("/forms/2/{batch_id}.pdf", response_class=Response)
def form_2(batch_id: uuid.UUID, session: DbSession):
    pdf = form_2_pdf(session, batch_id)
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="mau-2-{batch_id}.pdf"'}
    )


@router.post("/recall-drills", dependencies=[Depends(require_any_role({"qa", "director"}))])
def recall_drill(req: DrillIn, session: DbSession, principal: CurrentPrincipal) -> dict:
    root = resolve_node(session, req.type.value, req.ref)
    if root is None:
        raise not_found(req.type.value)
    return run_drill(session, principal, root)
