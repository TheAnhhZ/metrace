# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Tiny synthetic PDF "delivery notes" so seeded receivings carry documents (Mẫu 1)."""

from sqlalchemy.orm import Session

from app.core import object_storage
from app.core.upload_validation import validate_upload
from app.models.platform import FileObject


def _pdf(title: str) -> bytes:
    text = f"DEMO delivery note {title} - synthetic data".encode("ascii", "replace")
    stream = b"BT /F1 12 Tf 20 100 Td (" + text + b") Tj ET"
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    body = b"%PDF-1.4\n" + b"".join(f"{n} 0 obj".encode() + o + b"endobj\n" for n, o in enumerate(objects, 1))
    return body + b"trailer<</Root 1 0 R>>\n%%EOF\n"


def store_delivery_note(session: Session, receiving_code: str) -> FileObject:
    data = _pdf(receiving_code)
    checked = validate_upload(data, "application/pdf", max_bytes=1024 * 1024)
    key = object_storage.storage_key_for(checked.sha256)
    object_storage.put_bytes(key, data, checked.content_type)
    file = FileObject(
        storage_key=key,
        sha256=checked.sha256,
        content_type=checked.content_type,
        size_bytes=checked.size,
        original_name=f"{receiving_code}.pdf",
        owner_org_alias=None,
        uploaded_by="seed",
    )
    session.add(file)
    session.flush()
    return file
