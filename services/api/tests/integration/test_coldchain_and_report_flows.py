# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Cold chain end to end and the incident report draft flow (worker included)."""

import os
import time
from datetime import UTC, datetime

import httpx
import pytest

from tests.integration.gateway_tokens import GATEWAY, auth, sensor_token, user_token

pytestmark = pytest.mark.integration
ASSET = "TU-MAT-01"  # in the sensor client's asset claim; band 0..5 °C


def call(method: str, path: str, user: str = "qa-lan", **kwargs) -> httpx.Response:
    return httpx.request(method, f"{GATEWAY}/api/v1{path}", headers=auth(user_token(user)), timeout=30, **kwargs)


def wait_for(predicate, seconds: float = 20.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if value := predicate():
            return value
        time.sleep(0.5)
    pytest.fail("condition not met in time")


def open_alert(asset: str):
    return next((a for a in call("GET", "/coldchain/alerts").json() if a["asset_code"] == asset), None)


def post_reading(temp: float) -> httpx.Response:
    return httpx.post(
        f"{GATEWAY}/api/v1/assets/{ASSET}/readings",
        headers=auth(sensor_token()),
        timeout=30,
        json={"ts": datetime.now(UTC).isoformat(), "temp_c": temp},
    )


def test_three_warm_readings_open_one_alert_with_a_process_and_only_qa_can_acknowledge():
    if stale := open_alert(ASSET):  # leftover from an earlier run
        call("POST", f"/coldchain/alerts/{stale['id']}/acknowledge", json={"note": "test cleanup"})
    assert post_reading(4.0).json()["breach"] is False
    results = [post_reading(t).json() for t in (9.5, 10.0, 10.5, 11.0)]
    assert [r["breach"] for r in results] == [False, False, True, False]  # the 4th is deduplicated

    alert = wait_for(lambda: (a := open_alert(ASSET)) and a["process_instance_id"] and a)
    assert alert["max_temp_c"] in ("10.5", "11.0") and alert["nodes"] is not None
    assert call("POST", f"/coldchain/alerts/{alert['id']}/acknowledge", "director-nam", json={}).status_code == 403
    done = call("POST", f"/coldchain/alerts/{alert['id']}/acknowledge", json={"note": "Tủ đã sửa, hàng đã kiểm"})
    assert done.status_code == 200 and done.json()["acknowledged_by"] == "qa-lan"
    assert open_alert(ASSET) is None
    history = call("GET", f"/coldchain/assets/{ASSET}/readings?minutes=10").json()
    assert len(history["readings"]) >= 5


def test_report_draft_is_edited_and_approved_once():
    incident = call("POST", "/incidents", json={"title": "Report probe"}).json()
    assert call("POST", f"/incidents/{incident['id']}/report-draft").status_code == 202
    drafted = wait_for(
        lambda: (d := call("GET", f"/incidents/{incident['id']}").json())["report_draft"] and d,
        seconds=float(os.environ.get("LLM_TIMEOUT_S", "30")) + 15,
    )
    assert drafted["report_model"]
    if drafted["report_model"] == "template":  # no local LLM in CI: the deterministic template
        assert "1. Tóm tắt" in drafted["report_draft"]

    edited = drafted["report_draft"] + "\n\nQA: đã bổ sung kết quả kiểm nghiệm."
    assert call("PUT", f"/incidents/{incident['id']}/report", json={"text": edited}).status_code == 200
    head_before = call("GET", "/audit/head").json()["seq"]
    approved = call("POST", f"/incidents/{incident['id']}/report/approve").json()
    assert approved["report_final"] == edited and approved["report_approved_by"] == "qa-lan"
    assert call("GET", "/audit/head").json()["seq"] > head_before
    assert call("POST", f"/incidents/{incident['id']}/report/approve").status_code == 409
    assert call("PUT", f"/incidents/{incident['id']}/report", json={"text": "late edit"}).status_code == 409
    assert call("POST", f"/incidents/{incident['id']}/report-draft", "chef-hung").status_code == 403
