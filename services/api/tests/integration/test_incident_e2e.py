# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Incident scene end to end through the gateway (needs `make demo-reset` with
baseline,outbreak): third complaint -> suggestion -> incident -> lock -> held +
recall notices -> guards -> four-eyes close -> locks released."""

import time
from datetime import timedelta

import httpx
import pytest

from app.core.business_time import service_date
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration


def call(method: str, path: str, user: str, **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=30, **kwargs)


def ok(res: httpx.Response, status: int = 200):
    assert res.status_code == status, res.text
    return res.json()


def wait_for(predicate, seconds: float = 10.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.3)
    pytest.fail("condition not met in time")


@pytest.fixture(scope="module")
def scene():
    yesterday = str(service_date() - timedelta(days=1))
    points = {p["code"]: p for p in ok(call("GET", "/delivery-points", "cskh-thu"))}
    batches = ok(call("GET", f"/batches?day={yesterday}", "qa-lan"))
    broth = next((b for b in batches if b["batch_code"].endswith("lunch-NUOC-DUNG")), None)
    seeded = [c for c in ok(call("GET", "/complaints?status=open", "qa-lan")) if c["code"].startswith("PA-DEMO-")]
    if broth is None or len(seeded) < 2:
        pytest.skip("run `scripts/demo-reset.sh baseline,outbreak` first")
    return {"yesterday": yesterday, "points": points, "broth": broth, "seeded": seeded}


def test_incident_scene(scene):
    third = ok(
        call(
            "POST",
            "/complaints",
            "cskh-thu",
            json={
                "delivery_point_id": scene["points"]["DP-C"]["id"],
                "channel": "phone",
                "service_date": scene["yesterday"],
                "meal_slot": "lunch",
                "affected_count": 3,
                "description": "3 học sinh đau bụng",
            },
        ),
        201,
    )

    suggestions = ok(call("GET", "/complaints/cluster-suggestions?min_points=3", "qa-lan"))
    canh = next(s for s in suggestions if s["batch_code"].endswith("lunch-CANH-RAU"))
    assert canh["n_points"] == 3
    assert any(u["id"] == scene["broth"]["id"] for u in canh["upstream"])

    complaint_ids = [c["id"] for c in scene["seeded"]] + [third["id"]]
    incident = ok(
        call("POST", "/incidents", "qa-lan", json={"title": "Đau bụng sau bữa trưa", "complaint_ids": complaint_ids}),
        201,
    )
    wait_for(lambda: ok(call("GET", f"/incidents/{incident['id']}", "qa-lan"))["process_instance_id"])

    started = time.monotonic()
    result = ok(
        call(
            "POST",
            f"/incidents/{incident['id']}/confirm-suspects",
            "qa-lan",
            json={"nodes": [{"type": "batch", "id": scene["broth"]["id"]}], "lock_lots": True},
        )
    )
    assert result["incident"]["status"] == "contained"
    assert len(result["held_shipments"]) == 4  # today's lunch, all 4 points, still in the kitchen
    assert len(result["already_dispatched"]) == 5  # yesterday's lunch x4 + factory dinner
    assert result["elapsed_ms"] < 1000
    detail = wait_for(
        lambda: (
            (d := ok(call("GET", f"/incidents/{incident['id']}", "qa-lan")))["notices"] and len(d["notices"]) == 4 and d
        )
    )
    assert time.monotonic() - started < 5

    held = result["held_shipments"][0]
    blocked = call("POST", f"/shipments/{held}/dispatch", "driver-tuan")
    assert blocked.status_code == 422
    assert {v["code"] for v in blocked.json()["error"]["details"]["violations"]} >= {"P3_SHIPMENT_HELD"}

    request = ok(call("POST", f"/incidents/{incident['id']}/close-requests", "qa-lan", json={"note": "Đã xử lý"}), 201)
    assert call("POST", f"/close-requests/{request['id']}/approve", "chef-hung").status_code == 403
    closed = ok(call("POST", f"/close-requests/{request['id']}/approve", "approver-ha"))
    assert closed["status"] == "closed"
    final = ok(call("GET", f"/incidents/{incident['id']}", "qa-lan"))
    assert final["locks"] and not any(lock["active"] for lock in final["locks"])
    assert len(detail["shipments"]) >= 9


def test_requester_cannot_approve_own_close_request(scene):
    incident = ok(call("POST", "/incidents", "approver-ha", json={"title": "Four-eyes probe"}), 201)
    request = ok(call("POST", f"/incidents/{incident['id']}/close-requests", "approver-ha", json={}), 201)
    res = call("POST", f"/close-requests/{request['id']}/approve", "approver-ha")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "P5_SAME_PERSON"
