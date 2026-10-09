# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
import hashlib

import pytest

from app.core.errors import AppError
from app.core.reason_codes import ReasonCode
from app.core.upload_validation import validate_upload

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 32
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
CAP = 1024


@pytest.mark.parametrize(
    ("data", "declared", "mime"),
    [(PNG, "image/png", "image/png"), (JPEG, None, "image/jpeg"), (PDF, "application/pdf", "application/pdf")],
)
def test_allowed_types_pass_and_are_hashed(data, declared, mime):
    result = validate_upload(data, declared, CAP)
    assert result.content_type == mime
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.size == len(data)


def test_octet_stream_declaration_is_accepted_and_sniffed():
    assert validate_upload(PNG, "application/octet-stream", CAP).content_type == "image/png"


def _code(data, declared, cap=CAP):
    with pytest.raises(AppError) as err:
        validate_upload(data, declared, cap)
    return err.value.status, err.value.code


def test_declared_type_must_match_content():
    assert _code(PNG, "application/pdf") == (415, ReasonCode.FILE_TYPE_MISMATCH)


def test_eicar_is_rejected_as_wrong_type_not_as_virus():
    assert _code(EICAR, "application/pdf") == (415, ReasonCode.FILE_TYPE_NOT_ALLOWED)


def test_html_disguised_as_image_is_rejected():
    assert _code(b"<html><script>alert(1)</script></html>", "image/png") == (415, ReasonCode.FILE_TYPE_NOT_ALLOWED)


def test_too_large_and_empty():
    assert _code(PNG + b"\x00" * CAP, "image/png") == (413, ReasonCode.FILE_TOO_LARGE)
    assert _code(b"", "image/png") == (422, ReasonCode.FILE_EMPTY)
