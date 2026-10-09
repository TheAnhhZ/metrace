# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Store and serve files that always have an owner (company or one customer org)."""

import uuid
from urllib.parse import quote

from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core import object_storage
from app.core.audit_hash_chain import append_audit
from app.core.authorization import OrgScope
from app.core.errors import AppError, InfraError, not_found
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.core.settings import get_settings
from app.core.upload_validation import validate_upload
from app.models.platform import FileObject


def store_upload(session: Session, principal: Principal, upload: UploadFile, owner_org_alias: str | None) -> FileObject:
    """Sync on purpose: FastAPI runs it in the threadpool, so S3 I/O never blocks the event loop."""
    max_bytes = get_settings().upload_max_bytes
    data = upload.file.read(max_bytes + 1)  # never buffer more than cap + 1
    checked = validate_upload(data, upload.content_type, max_bytes)
    key = object_storage.storage_key_for(checked.sha256)
    object_storage.put_bytes(key, checked.data, checked.content_type)

    file = FileObject(
        storage_key=key,
        sha256=checked.sha256,
        content_type=checked.content_type,
        size_bytes=checked.size,
        original_name=(upload.filename or "upload")[:255],
        owner_org_alias=owner_org_alias,
        uploaded_by=principal.sub,
    )
    session.add(file)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="file.uploaded",
        entity_type="file",
        entity_id=file.id,
        payload={"sha256": checked.sha256, "size": checked.size, "owner_org": owner_org_alias},
    )
    session.commit()
    return file


def get_visible_file(session: Session, file_id: uuid.UUID, scope: OrgScope) -> FileObject:
    file = session.get(FileObject, file_id)
    # Internal staff see everything; customers only their own org (company-owned files have no org).
    if file is None or not scope.allows(file.owner_org_alias):
        raise not_found("file")
    return file


def download_response(session: Session, file: FileObject) -> StreamingResponse:
    filename = quote(file.original_name)
    try:
        stream = object_storage.open_stream(file.storage_key)
    except object_storage.ObjectMissingError as exc:
        raise not_found("file") from exc
    except InfraError as exc:
        raise AppError(503, ReasonCode.SERVICE_UNAVAILABLE, "File storage unavailable") from exc
    # Give the DB connection back before streaming: a slow download must not hold the pool.
    session.close()
    return StreamingResponse(
        stream,
        media_type=file.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
