# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Spike a (W0 gate): Flowable 8 REST does everything the worker needs.

Run against the stack with dev ports: `make test-integration`.
"""

import os
import time
import uuid
from pathlib import Path

import pytest

from app.workflow.flowable_client import FlowableClient

pytestmark = pytest.mark.integration

BPMN = Path(__file__).parents[4] / "workflows" / "bpmn" / "spike-timer-escalation.bpmn20.xml"
PROCESS_KEY = "spike-timer-escalation"
TOPIC = "metrace-spike"
WORKER = "pytest-worker"


@pytest.fixture(scope="module")
def flowable():
    client = FlowableClient(
        os.environ.get("FLOWABLE_URL", "http://localhost:8081/flowable-rest"),
        "rest-admin",
        os.environ["FLOWABLE_ADMIN_PASSWORD"],
    )
    client.deploy_if_changed(BPMN.name, BPMN.read_bytes())
    yield client
    client.close()


def _start_and_release_worker_step(flowable: FlowableClient, timeout: str) -> str:
    business_key = f"spike-{uuid.uuid4()}"
    instance = flowable.start_process(PROCESS_KEY, business_key, {"reviewTimeout": timeout})
    # Same business key again returns the same instance (idempotent start).
    assert flowable.start_process(PROCESS_KEY, business_key)["id"] == instance["id"]

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        jobs = [j for j in flowable.acquire_jobs(TOPIC, WORKER) if j["processInstanceId"] == instance["id"]]
        if jobs:
            flowable.complete_job(jobs[0]["id"], WORKER, {"notified": True})
            return instance["id"]
        time.sleep(0.5)
    pytest.fail("external-worker job was never acquired")


def _wait_for_task(flowable: FlowableClient, instance_id: str, key: str, seconds: float) -> dict:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        tasks = flowable.tasks(instance_id, key)
        if tasks:
            return tasks[0]
        time.sleep(1)
    pytest.fail(f"task {key!r} did not appear within {seconds}s")


def test_redeploy_identical_bpmn_creates_no_new_version(flowable):
    before = len(flowable.process_definitions(PROCESS_KEY))
    again = flowable.deploy_if_changed(BPMN.name, BPMN.read_bytes())
    assert again.created is False
    assert len(flowable.process_definitions(PROCESS_KEY)) == before


def test_external_worker_then_user_task_completes_process(flowable):
    instance_id = _start_and_release_worker_step(flowable, "PT10M")
    review = _wait_for_task(flowable, instance_id, "review", 10)
    flowable.complete_task(review["id"], {"approved": True})
    history = flowable.historic_process_instance(instance_id)
    assert history["endTime"] is not None
    assert history["endActivityId"] == "done"


def test_boundary_timer_escalates_within_30_seconds(flowable):
    instance_id = _start_and_release_worker_step(flowable, "PT10S")
    _wait_for_task(flowable, instance_id, "review", 10)
    escalate = _wait_for_task(flowable, instance_id, "escalate", 30)
    assert escalate["taskDefinitionKey"] == "escalate"
    assert flowable.tasks(instance_id, "review") == []
