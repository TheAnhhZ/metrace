# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Portal isolation, both directions: reading another org's data and writing
references to another org's resources are 404; staff on portal routes are 403."""

import uuid
from datetime import timedelta

import httpx
import pytest

from app.core.business_time import service_date
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 24


def call(method: str, path: str, user: str, **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=30, **kwargs)


def ok(res: httpx.Response, status: int = 200):
    assert res.status_code == status, res.text
    return res.json()


@pytest.fixture(scope="module")
def points():
    return {p["customer_alias"]: p for p in ok(call("GET", "/delivery-points", "qa-lan"))}


def complaint_body(point_id: str, **extra) -> dict:
    return {
        "delivery_point_id": point_id,
        "service_date": str(service_date() - timedelta(days=1)),
        "meal_slot": "lunch",
        "affected_count": 1,
        "description": "IDOR probe",
        **extra,
    }


def test_deliveries_show_only_own_org(points):
    rows = ok(call("GET", "/portal/deliveries", "truong-a"))
    assert rows and {r["delivery_point"] for r in rows} == {points["truong-a"]["name"]}
    factory = ok(call("GET", "/portal/deliveries", "nha-may-x"))
    assert {r["meal_slot"] for r in factory} >= {"lunch"}
    assert all(r["delivery_point"] == points["nha-may-x"]["name"] for r in factory)


def test_complaint_for_own_point_is_created_with_portal_channel(points):
    created = ok(call("POST", "/portal/complaints", "truong-a", json=complaint_body(points["truong-a"]["id"])), 201)
    assert created["channel"] == "portal" and created["reported_by"] == "truong-a"
    listed = ok(call("GET", "/portal/complaints", "truong-a"))
    assert created["id"] in {c["id"] for c in listed["complaints"]}
    other = ok(call("GET", "/portal/complaints", "truong-b"))
    assert created["id"] not in {c["id"] for c in other["complaints"]}


def test_write_reference_to_another_orgs_point_is_404(points):
    res = call("POST", "/portal/complaints", "truong-a", json=complaint_body(points["truong-b"]["id"]))
    assert res.status_code == 404
    assert call("POST", "/portal/complaints", "truong-a", json=complaint_body(str(uuid.uuid4()))).status_code == 404


def test_write_reference_to_another_orgs_file_is_404(points):
    foreign = ok(
        call("POST", "/portal/files", "truong-b", files={"file": ("x.png", PNG + uuid.uuid4().bytes, "image/png")}), 201
    )
    company = ok(
        call("POST", "/files", "qa-lan", files={"file": ("y.png", PNG + uuid.uuid4().bytes, "image/png")}), 201
    )
    for file_id in (foreign["id"], company["id"]):
        body = complaint_body(points["truong-a"]["id"], file_ids=[file_id])
        assert call("POST", "/portal/complaints", "truong-a", json=body).status_code == 404
    own = ok(
        call("POST", "/portal/files", "truong-a", files={"file": ("z.png", PNG + uuid.uuid4().bytes, "image/png")}), 201
    )
    body = complaint_body(points["truong-a"]["id"], file_ids=[own["id"]])
    assert ok(call("POST", "/portal/complaints", "truong-a", json=body), 201)


def test_notices_are_isolated_and_ack_is_404_across_orgs():
    a_notices = ok(call("GET", "/portal/notices", "truong-a"))
    b_notices = ok(call("GET", "/portal/notices", "truong-b"))
    assert not {n["id"] for n in a_notices} & {n["id"] for n in b_notices}
    if not b_notices:
        pytest.skip("no recall notice for truong-b yet (run the incident scene first)")
    assert call("POST", f"/portal/notices/{b_notices[0]['id']}/acknowledge", "truong-a").status_code == 404
    acked = ok(call("POST", f"/portal/notices/{b_notices[0]['id']}/acknowledge", "truong-b"))
    assert acked["acknowledged_by"] == "truong-b"


@pytest.mark.parametrize("path", ["/portal/deliveries", "/portal/complaints", "/portal/notices"])
def test_staff_cannot_use_portal_routes(path):
    assert call("GET", path, "qa-lan").status_code == 403
    assert call("GET", path, "director-nam").status_code == 403
