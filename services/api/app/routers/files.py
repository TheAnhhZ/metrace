# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""File upload/download. Internal uploads belong to the company; portal uploads
belong to the caller's customer organization. Another org's file is a 404."""

import uuid
from datetime import datetime

from fastapi import File, Query, UploadFile
from pydantic import BaseModel

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, org_scope, portal_router
from app.core.database import DbSession
from app.core.errors import AppError
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.services import file_service

internal = internal_router(prefix="/api/v1/files", tags=["files"])
portal = portal_router(prefix="/api/v1/portal/files", tags=["portal"])


class FileOut(BaseModel):
    id: uuid.UUID
    sha256: str
    content_type: str
    size_bytes: int
    original_name: str
    owner_org: str | None
    uploaded_at: datetime | None


def _out(file) -> FileOut:
    return FileOut(
        id=file.id,
        sha256=file.sha256,
        content_type=file.content_type,
        size_bytes=file.size_bytes,
        original_name=file.original_name,
        owner_org=file.owner_org_alias,
        uploaded_at=file.uploaded_at,
    )


def _customer_org(principal: Principal, requested: str | None) -> str:
    if requested is not None:
        if requested not in principal.org_aliases:
            raise AppError(403, ReasonCode.FORBIDDEN, "Not a member of this organization")
        return requested
    if len(principal.org_aliases) != 1:
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "Specify ?org= (member of several organizations)")
    return next(iter(principal.org_aliases))


@internal.post("", response_model=FileOut, status_code=201)
def upload_company_file(session: DbSession, principal: CurrentPrincipal, file: UploadFile = File(...)) -> FileOut:  # noqa: B008
    return _out(file_service.store_upload(session, principal, file, owner_org_alias=None))


@internal.get("/{file_id}")
def download_any_file(file_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    return file_service.download_response(file_service.get_visible_file(session, file_id, org_scope(principal)))


@portal.post("", response_model=FileOut, status_code=201)
def upload_customer_file(
    session: DbSession,
    principal: CurrentPrincipal,
    file: UploadFile = File(...),  # noqa: B008
    org: str | None = Query(default=None),
) -> FileOut:
    owner = _customer_org(principal, org)
    return _out(file_service.store_upload(session, principal, file, owner_org_alias=owner))


@portal.get("/{file_id}")
def download_own_file(file_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    return file_service.download_response(file_service.get_visible_file(session, file_id, org_scope(principal)))
