# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Through the gateway: file ownership (IDOR both ways) and who may call what."""

import uuid

import httpx
import pytest

from tests.integration.gateway_tokens import GATEWAY, auth, sensor_token, user_token

pytestmark = pytest.mark.integration

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + uuid.uuid4().bytes + b"\x00" * 16
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _upload(path: str, token: str, data: bytes, mime: str, name: str = "photo.png") -> httpx.Response:
    return httpx.post(f"{GATEWAY}{path}", headers=auth(token), files={"file": (name, data, mime)}, timeout=30)


def test_customer_upload_is_visible_to_owner_and_staff_but_not_other_customer():
    res = _upload("/api/v1/portal/files", user_token("truong-a"), PNG, "image/png")
    assert res.status_code == 201, res.text
    file_id = res.json()["id"]
    assert res.json()["owner_org"] == "truong-a"

    own = httpx.get(f"{GATEWAY}/api/v1/portal/files/{file_id}", headers=auth(user_token("truong-a")))
    assert own.status_code == 200 and own.content == PNG
    assert own.headers["content-disposition"].startswith("attachment")
    assert own.headers["x-content-type-options"] == "nosniff"

    other = httpx.get(f"{GATEWAY}/api/v1/portal/files/{file_id}", headers=auth(user_token("truong-b")))
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "NOT_FOUND"

    staff = httpx.get(f"{GATEWAY}/api/v1/files/{file_id}", headers=auth(user_token("qa-lan")))
    assert staff.status_code == 200


def test_company_file_is_invisible_to_customers():
    res = _upload("/api/v1/files", user_token("procurement-mai"), PNG, "image/png", "gcn.png")
    assert res.status_code == 201, res.text
    file_id = res.json()["id"]
    assert res.json()["owner_org"] is None
    res = httpx.get(f"{GATEWAY}/api/v1/portal/files/{file_id}", headers=auth(user_token("truong-a")))
    assert res.status_code == 404


def test_unknown_file_is_404_not_500():
    res = httpx.get(f"{GATEWAY}/api/v1/files/{uuid.uuid4()}", headers=auth(user_token("qa-lan")))
    assert res.status_code == 404


@pytest.mark.parametrize(
    ("data", "mime", "status", "code"),
    [
        pytest.param(EICAR, "application/pdf", 415, "FILE_TYPE_NOT_ALLOWED", id="eicar-text"),
        pytest.param(PNG, "application/pdf", 415, "FILE_TYPE_MISMATCH", id="png-declared-pdf"),
        pytest.param(
            b"\x89PNG\r\n\x1a\n" + b"\x00" * (10 * 1024 * 1024 + 1),
            "image/png",
            413,
            "FILE_TOO_LARGE",
            id="png-over-10mib",
        ),
    ],
)
def test_bad_uploads_are_rejected_with_reason_code(data, mime, status, code):
    res = _upload("/api/v1/files", user_token("qa-lan"), data, mime)
    assert res.status_code == status
    assert res.json()["error"]["code"] == code
    assert res.json()["error"]["request_id"]


@pytest.mark.parametrize("path", ["/api/v1/files/00000000-0000-0000-0000-000000000000"])
def test_customer_and_sensor_are_forbidden_on_internal_routes(path):
    for token in (user_token("truong-a"), sensor_token()):
        res = httpx.get(f"{GATEWAY}{path}", headers=auth(token))
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"


def test_staff_and_sensor_are_forbidden_on_portal_routes():
    for token in (user_token("qa-lan"), user_token("director-nam"), sensor_token()):
        res = httpx.get(f"{GATEWAY}/api/v1/portal/files/{uuid.uuid4()}", headers=auth(token))
        assert res.status_code == 403


def test_customer_cannot_upload_on_behalf_of_another_org():
    res = _upload("/api/v1/portal/files?org=truong-b", user_token("truong-a"), PNG, "image/png")
    assert res.status_code == 403
