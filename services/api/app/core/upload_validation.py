# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Validate uploaded bytes by content (magic bytes), not by name or header.

Allow-list: JPEG, PNG, PDF. The declared Content-Type must match what the
bytes actually are. This is type checking, NOT malware scanning: an EICAR test
string is rejected because it is plain text, not because it is a virus.
"""

import hashlib
from dataclasses import dataclass

import filetype

from app.core.errors import AppError
from app.core.reason_codes import ReasonCode

ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "application/pdf"})


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    content_type: str
    sha256: str
    size: int


def validate_upload(data: bytes, declared_type: str | None, max_bytes: int) -> ValidatedUpload:
    if not data:
        raise AppError(422, ReasonCode.FILE_EMPTY, "Empty file")
    if len(data) > max_bytes:
        raise AppError(413, ReasonCode.FILE_TOO_LARGE, "File too large", details={"max_bytes": max_bytes})

    kind = filetype.guess(data)
    sniffed = kind.mime if kind else None
    if sniffed not in ALLOWED_TYPES:
        raise AppError(
            415,
            ReasonCode.FILE_TYPE_NOT_ALLOWED,
            "Only JPEG, PNG or PDF files are accepted",
            details={"detected": sniffed, "allowed": sorted(ALLOWED_TYPES)},
        )
    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream" and declared != sniffed:
        raise AppError(
            415,
            ReasonCode.FILE_TYPE_MISMATCH,
            "Declared type does not match file content",
            details={"declared": declared, "detected": sniffed},
        )
    return ValidatedUpload(data=data, content_type=sniffed, sha256=hashlib.sha256(data).hexdigest(), size=len(data))
