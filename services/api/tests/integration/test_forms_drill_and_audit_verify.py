# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Mẫu 2 PDF, recall drill (dry run) and audit verification against anchors."""

import httpx
import pytest
from sqlalchemy import text

from tests.integration.conftest import owner_execute
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration


def call(method: str, path: str, user: str = "qa-lan", **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=30, **kwargs)


@pytest.fixture(scope="module")
def broth_lot() -> str:
    lots = call("GET", "/lots").json()
    lot = next((x for x in lots if x["ingredient_code"] == "XUONG-LON"), None)
    if lot is None:
        pytest.skip("seed data missing")
    return lot["lot_code"]


def test_form_2_pdf_carries_the_audit_anchor():
    batch = call("GET", "/batches").json()[0]
    res = call("GET", f"/forms/2/{batch['id']}.pdf")
    assert res.status_code == 200 and res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF") and res.elapsed.total_seconds() < 2


def _lock_state(lot_code: str) -> bool:
    return next(x["locked"] for x in call("GET", "/lots").json() if x["lot_code"] == lot_code)


def test_recall_drill_is_a_dry_run(broth_lot):
    incidents_before, locked_before = {i["id"] for i in call("GET", "/incidents").json()}, _lock_state(broth_lot)
    result = call("POST", "/recall-drills", json={"type": "lot", "ref": broth_lot}).json()
    assert result["forward"]["delivery_point"] >= 1
    assert result["lock_preview"] is not None and 0 <= result["coverage"]["coverage_pct"] <= 100
    # Dry run: no incident, no lock left behind.
    assert {i["id"] for i in call("GET", "/incidents").json()} == incidents_before
    assert _lock_state(broth_lot) == locked_before
    assert call("POST", "/recall-drills", "driver-tuan", json={"type": "lot", "ref": broth_lot}).status_code == 403


def test_audit_verify_detects_tampering_after_an_anchor(owner_engine):
    head = call("GET", "/audit/head").json()
    assert call("GET", "/audit/verify", params={"anchor_seq": head["seq"], "anchor_hash": head["hash"]}).json()["ok"]
    with owner_engine.begin() as conn:
        original = conn.execute(text("SELECT actor FROM audit_event WHERE seq = :s"), {"s": head["seq"]}).scalar()
    owner_execute(owner_engine, "UPDATE audit_event SET actor = 'tampered' WHERE seq = :s", s=head["seq"])
    try:
        result = call("GET", "/audit/verify").json()
        assert result["ok"] is False and result["first_bad_seq"] == head["seq"]
    finally:
        owner_execute(owner_engine, "UPDATE audit_event SET actor = :a WHERE seq = :s", a=original, s=head["seq"])
    assert call("GET", "/audit/verify").json()["ok"]
    assert call("GET", "/audit/verify", "chef-hung").status_code == 403
