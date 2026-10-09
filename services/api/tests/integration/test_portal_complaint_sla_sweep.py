# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P6: the worker flags a complaint once its answer deadline passes (no BPMN)."""

import time
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.core.business_time import service_date
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration


def test_overdue_complaint_is_flagged_by_the_worker(app_engine):
    headers = auth(user_token("truong-c"))
    point = next(
        p
        for p in httpx.get(f"{GATEWAY}/api/v1/delivery-points", headers=auth(user_token("qa-lan"))).json()
        if p["customer_alias"] == "truong-c"
    )
    created = httpx.post(
        f"{GATEWAY}/api/v1/portal/complaints",
        headers=headers,
        json={
            "delivery_point_id": point["id"],
            "service_date": str(service_date() - timedelta(days=1)),
            "meal_slot": "lunch",
            "affected_count": 1,
            "description": "SLA probe",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["sla_breached"] is False
    with app_engine.begin() as conn:  # pretend the 24 h deadline is already behind us
        conn.execute(
            text("UPDATE complaint SET sla_due_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": created.json()["id"]},
        )

    deadline = time.monotonic() + 45  # one reconciler cycle is 30 s
    while time.monotonic() < deadline:
        mine = httpx.get(f"{GATEWAY}/api/v1/portal/complaints", headers=headers).json()["complaints"]
        if next(c for c in mine if c["id"] == created.json()["id"])["sla_breached"]:
            return
        time.sleep(2)
    pytest.fail("complaint was not flagged as overdue within one sweep")
