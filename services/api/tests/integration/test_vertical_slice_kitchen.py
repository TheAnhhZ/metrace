# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Kitchen vertical slice through the gateway, every Poka-yoke stop on the way:
receive -> cook -> sample -> Mẫu 3 -> dispatch (needs the seeded master data)."""

import uuid

import httpx
import pytest

from app.core.business_time import service_date
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 24


def call(method: str, path: str, user: str, **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=30, **kwargs)


def ok(res: httpx.Response, status: int = 200) -> dict:
    assert res.status_code == status, res.text
    return res.json()


def blocked(res: httpx.Response, rule: str, *codes: str) -> dict:
    assert res.status_code == 422, res.text
    error = res.json()["error"]
    assert error["rule"] == rule
    assert {v["code"] for v in error["details"]["violations"]} == set(codes)
    return error


@pytest.fixture(scope="module")
def master():
    suppliers = {s["code"]: s for s in ok(call("GET", "/suppliers", "procurement-mai"))}
    ingredients = {i["code"]: i for i in ok(call("GET", "/ingredients", "procurement-mai"))}
    dishes = {d["code"]: d for d in ok(call("GET", "/dishes", "chef-hung"))}
    points = {p["code"]: p for p in ok(call("GET", "/delivery-points", "chef-hung"))}
    if "NCC-06" not in suppliers or "GA-RANG" not in dishes:
        pytest.skip("seed master data missing")
    return {"s": suppliers, "i": ingredients, "d": dishes, "p": points}


@pytest.fixture(scope="module")
def document_id():
    files = {"file": ("phieu-giao.png", PNG + uuid.uuid4().bytes, "image/png")}
    return ok(call("POST", "/files", "procurement-mai", files=files), 201)["id"]


def receiving(master, supplier: str, ingredient: str, temp, docs: list) -> dict:
    line = {"ingredient_id": master["i"][ingredient]["id"], "qty_kg": "20", "temp_c": temp}
    return {"supplier_id": master["s"][supplier]["id"], "document_file_ids": docs, "lines": [line]}


def test_p1_receiving_blocks_and_warns(master, document_id):
    blocked(
        call("POST", "/receivings", "procurement-mai", json=receiving(master, "NCC-06", "GAO", None, [document_id])),
        "P1",
        "P1_SUPPLIER_CERT_EXPIRED",
    )
    blocked(
        call(
            "POST", "/receivings", "procurement-mai", json=receiving(master, "NCC-01", "THIT-LON", "6", [document_id])
        ),
        "P1",
        "P1_TEMP_OUT_OF_RANGE",
    )
    blocked(
        call("POST", "/receivings", "procurement-mai", json=receiving(master, "NCC-01", "THIT-LON", "3", [])),
        "P1",
        "P1_MISSING_DOCUMENTS",
    )
    expiring = ok(
        call(
            "POST", "/receivings", "procurement-mai", json=receiving(master, "NCC-04", "CA-BASA", "-20", [document_id])
        ),
        201,
    )
    assert [w["code"] for w in expiring["warnings"]] == ["P1_SUPPLIER_CERT_EXPIRING"]


def test_roles_are_enforced_per_step(master):
    body = {
        "dish_id": master["d"]["GA-RANG"]["id"],
        "service_date": str(service_date()),
        "meal_slot": "dinner",
        "portions_planned": 200,
    }
    assert call("POST", "/batches", "driver-tuan", json=body).status_code == 403
    assert call("POST", "/receivings", "chef-hung", json={}).status_code == 403


def test_full_slice_receive_cook_sample_check_dispatch(master, document_id):
    today = str(service_date())
    rec = ok(
        call("POST", "/receivings", "procurement-mai", json=receiving(master, "NCC-03", "GA", "2.5", [document_id])),
        201,
    )
    lot_id = rec["lots"][0]["id"]

    batch = ok(
        call(
            "POST",
            "/batches",
            "chef-hung",
            json={
                "dish_id": master["d"]["GA-RANG"]["id"],
                "service_date": today,
                "meal_slot": "dinner",
                "portions_planned": 200,
            },
        ),
        201,
    )
    ok(call("POST", f"/batches/{batch['id']}/inputs", "chef-hung", json={"lot_id": lot_id, "qty_kg": "20"}), 201)
    blocked(
        call(
            "POST", f"/batches/{batch['id']}/finish", "chef-hung", json={"core_temp_c": "70", "portions_produced": 200}
        ),
        "P2",
        "P2_CORE_TEMP_BELOW_MIN",
    )
    ok(
        call(
            "POST", f"/batches/{batch['id']}/finish", "chef-hung", json={"core_temp_c": "82", "portions_produced": 200}
        )
    )

    shipment = ok(
        call(
            "POST",
            "/shipments",
            "chef-hung",
            json={"delivery_point_id": master["p"]["DP-X"]["id"], "service_date": today, "meal_slot": "dinner"},
        ),
        201,
    )
    ok(
        call(
            "POST", f"/shipments/{shipment['id']}/items", "chef-hung", json={"batch_id": batch["id"], "portions": 200}
        ),
        201,
    )
    blocked(
        call("POST", f"/shipments/{shipment['id']}/dispatch", "driver-tuan"),
        "P3",
        "P3_MISSING_FORM_3",
        "P3_SAMPLE_MISSING",
    )

    blocked(
        call("POST", "/samples", "qa-lan", json={"batch_id": batch["id"], "qty_g": 90}), "P4", "P4_SAMPLE_UNDER_MINIMUM"
    )
    sample = ok(call("POST", "/samples", "qa-lan", json={"batch_id": batch["id"], "qty_g": 150}), 201)
    seal = call("GET", f"/samples/{sample['id']}/seal.svg", "qa-lan")
    assert seal.status_code == 200 and seal.headers["content-type"].startswith("image/svg+xml")
    ok(
        call(
            "POST",
            "/portion-checks",
            "qa-lan",
            json={"batch_id": batch["id"], "shipment_id": shipment["id"], "portions": 200},
        ),
        201,
    )

    before = ok(call("GET", f"/shipments?day={today}&meal_slot=dinner", "driver-tuan"))
    assert next(s for s in before if s["id"] == shipment["id"])["blockers"] == []
    gone = ok(call("POST", f"/shipments/{shipment['id']}/dispatch", "driver-tuan"))
    assert gone["status"] == "dispatched"

    assert call("POST", f"/samples/{sample['id']}/discard", "chef-hung").status_code == 403
    blocked(call("POST", f"/samples/{sample['id']}/discard", "qa-lan"), "P4", "P4_DISCARD_BEFORE_RETENTION")


def test_seeded_lunch_is_ready_to_dispatch_and_status_tracks_it():
    today = str(service_date())
    shipments = ok(call("GET", f"/shipments?day={today}&meal_slot=lunch", "driver-tuan"))
    assert len(shipments) == 4
    assert all(s["blockers"] == [] for s in shipments if s["status"] == "ready")
    status = ok(call("GET", f"/meal-services/{today}/lunch/status", "qa-lan"))
    steps = {s["key"]: s["done"] for s in status["steps"]}
    assert steps["menu"] and steps["cooked"] and steps["samples"] and steps["form3"]
