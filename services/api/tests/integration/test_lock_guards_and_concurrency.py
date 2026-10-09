# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Locks per incident, guards, and lock-vs-dispatch races (through the gateway)."""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import httpx
import pytest

from app.core.business_time import service_date
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 24


def call(method: str, path: str, user: str, **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=60, **kwargs)


def ok(res: httpx.Response, status: int = 200):
    assert res.status_code == status, res.text
    return res.json()


@pytest.fixture(scope="module")
def master():
    return {
        "s": {s["code"]: s for s in ok(call("GET", "/suppliers", "qa-lan"))},
        "i": {i["code"]: i for i in ok(call("GET", "/ingredients", "qa-lan"))},
        "d": {d["code"]: d for d in ok(call("GET", "/dishes", "qa-lan"))},
        "p": {p["code"]: p for p in ok(call("GET", "/delivery-points", "qa-lan"))},
    }


def fresh_lot(master) -> str:
    doc = ok(
        call("POST", "/files", "procurement-mai", files={"file": ("d.png", PNG + uuid.uuid4().bytes, "image/png")}), 201
    )
    rec = ok(
        call(
            "POST",
            "/receivings",
            "procurement-mai",
            json={
                "supplier_id": master["s"]["NCC-03"]["id"],
                "document_file_ids": [doc["id"]],
                "lines": [{"ingredient_id": master["i"]["GA"]["id"], "qty_kg": "30", "temp_c": "2"}],
            },
        ),
        201,
    )
    return rec["lots"][0]["id"]


def cooked_batch(master, lot_id: str, day=None) -> dict:
    batch = ok(
        call(
            "POST",
            "/batches",
            "chef-hung",
            json={
                "dish_id": master["d"]["GA-RANG"]["id"],
                "service_date": str(day or service_date()),
                "meal_slot": "dinner",
                "portions_planned": 40,
            },
        ),
        201,
    )
    ok(call("POST", f"/batches/{batch['id']}/inputs", "chef-hung", json={"lot_id": lot_id, "qty_kg": "4"}), 201)
    return ok(
        call("POST", f"/batches/{batch['id']}/finish", "chef-hung", json={"core_temp_c": "85", "portions_produced": 40})
    )


def ready_shipment(master, batch_id: str) -> str:
    shipment = ok(
        call(
            "POST",
            "/shipments",
            "chef-hung",
            json={
                "delivery_point_id": master["p"]["DP-X"]["id"],
                "service_date": str(service_date()),
                "meal_slot": "dinner",
            },
        ),
        201,
    )
    ok(call("POST", f"/shipments/{shipment['id']}/items", "chef-hung", json={"batch_id": batch_id, "portions": 4}), 201)
    ok(
        call(
            "POST",
            "/portion-checks",
            "qa-lan",
            json={"batch_id": batch_id, "shipment_id": shipment["id"], "portions": 4},
        ),
        201,
    )
    return shipment["id"]


def lock_lot(lot_id: str, title: str) -> tuple[str, dict]:
    incident = ok(call("POST", "/incidents", "qa-lan", json={"title": title}), 201)
    result = ok(
        call(
            "POST",
            f"/incidents/{incident['id']}/confirm-suspects",
            "qa-lan",
            json={"nodes": [{"type": "lot", "id": lot_id}], "lock_lots": False},
        )
    )
    return incident["id"], result


def close(incident_id: str) -> None:
    request = ok(call("POST", f"/incidents/{incident_id}/close-requests", "qa-lan", json={}), 201)
    ok(call("POST", f"/close-requests/{request['id']}/approve", "approver-ha"))


def try_input(master, lot_id: str) -> httpx.Response:
    batch = ok(
        call(
            "POST",
            "/batches",
            "chef-hung",
            json={
                "dish_id": master["d"]["GA-RANG"]["id"],
                "service_date": str(service_date()),
                "meal_slot": "dinner",
                "portions_planned": 10,
            },
        ),
        201,
    )
    return call("POST", f"/batches/{batch['id']}/inputs", "chef-hung", json={"lot_id": lot_id, "qty_kg": "1"})


def test_two_incidents_on_one_lot_release_independently(master):
    lot = fresh_lot(master)
    batch = cooked_batch(master, lot)
    shipment = ready_shipment(master, batch["id"])
    first, result = lock_lot(lot, "Probe 1")
    assert shipment in result["held_shipments"]
    second, _ = lock_lot(lot, "Probe 2")

    res = try_input(master, lot)
    assert res.status_code == 422 and res.json()["error"]["code"] == "P2_INPUT_LOCKED"
    close(first)
    assert try_input(master, lot).status_code == 422  # still locked by the second incident
    close(second)
    assert try_input(master, lot).status_code == 201


def test_lock_and_dispatch_race_never_lets_food_out_unnoticed(master):
    lot = fresh_lot(master)
    batch = cooked_batch(master, lot)
    ok(call("POST", "/samples", "qa-lan", json={"batch_id": batch["id"], "qty_g": 150}), 201)
    shipments = [ready_shipment(master, batch["id"]) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=9) as pool:
        dispatches = [pool.submit(call, "POST", f"/shipments/{s}/dispatch", "driver-tuan") for s in shipments]
        locking = pool.submit(lock_lot, lot, "Race probe")
        codes = [f.result().status_code for f in dispatches]
        incident_id, result = locking.result()

    assert set(codes) <= {200, 422}
    gone = {s for s, code in zip(shipments, codes, strict=True) if code == 200}
    assert set(result["held_shipments"]) == set(shipments) - gone  # every shipment either left or is held
    assert set(result["already_dispatched"]) >= gone
    if gone:  # food that left before the lock gets a recall notice
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            notices = ok(call("GET", f"/incidents/{incident_id}", "qa-lan"))["notices"]
            if notices:
                break
            time.sleep(0.3)
        assert notices
    close(incident_id)


def test_cooked_food_is_not_carried_over_to_another_service_day(master):
    yesterday = cooked_batch(master, fresh_lot(master), day=service_date() - timedelta(days=1))
    today = cooked_batch(master, fresh_lot(master))  # finished; a new cooking batch reuses it below
    batch = ok(
        call(
            "POST",
            "/batches",
            "chef-hung",
            json={
                "dish_id": master["d"]["GA-RANG"]["id"],
                "service_date": str(service_date()),
                "meal_slot": "dinner",
                "portions_planned": 10,
            },
        ),
        201,
    )
    late = call(
        "POST", f"/batches/{batch['id']}/inputs", "chef-hung", json={"input_batch_id": yesterday["id"], "qty_kg": "1"}
    )
    assert late.status_code == 409 and "same service day" in late.json()["error"]["message"]
    same_day = {"input_batch_id": today["id"], "qty_kg": "1"}
    assert call("POST", f"/batches/{batch['id']}/inputs", "chef-hung", json=same_day).status_code == 201
