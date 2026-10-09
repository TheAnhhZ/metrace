# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""#6: verify the audit hash chain, optionally against an anchor (seq, hash) that
was printed outside the database (recall notice, PDF footer, drill result)."""

from fastapi import Depends, Query
from pydantic import BaseModel

from app.core.audit_hash_chain import chain_head, verify_chain
from app.core.authorization import internal_router, require_any_role
from app.core.database import DbSession

router = internal_router(
    prefix="/api/v1/audit", tags=["audit"], dependencies=[Depends(require_any_role({"qa", "director", "approver"}))]
)


class VerifyOut(BaseModel):
    ok: bool
    checked: int
    head_seq: int | None
    head_hash: str | None
    first_bad_seq: int | None
    reason: str | None


@router.get("/head")
def head(session: DbSession) -> dict:
    current = chain_head(session)
    return {"seq": current[0], "hash": current[1]} if current else {"seq": None, "hash": None}


@router.get("/verify", response_model=VerifyOut)
def verify(
    session: DbSession,
    anchor_seq: int | None = Query(None, ge=1),
    anchor_hash: str | None = Query(None, min_length=64, max_length=64, pattern="^[0-9a-f]{64}$"),
):
    anchor = (anchor_seq, anchor_hash) if anchor_seq is not None and anchor_hash is not None else None
    result = verify_chain(session, anchor)
    return VerifyOut(**result.__dict__)
