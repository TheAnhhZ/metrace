# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Minimal Flowable REST client (httpx). Only the worker talks to Flowable.

Swapping the engine (e.g. Operaton) means rewriting this file only.
Callbacks use the PULL pattern: the worker acquires external-worker jobs or
polls tasks, so Flowable never needs the app's URL or credentials.
"""

import hashlib
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.errors import InfraError


class FlowableError(Exception):
    """Flowable answered with an unexpected status (logic error, do not retry blindly)."""


class FlowableUnavailableError(InfraError):
    """Network/5xx problem talking to Flowable: the outbox retries it forever with backoff."""


@dataclass(frozen=True)
class Deployment:
    id: str
    name: str
    created: bool  # False when an identical BPMN was already deployed


def _variables(values: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [{"name": k, "value": v} for k, v in (values or {}).items()]


class FlowableClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 10.0):
        # base_url example: http://flowable:8080/flowable-rest
        self._http = httpx.Client(base_url=base_url.rstrip("/"), auth=(username, password), timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "FlowableClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, expected: tuple[int, ...] = (200,), **kwargs: Any) -> Any:
        try:
            res = self._http.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise FlowableUnavailableError(f"{method} {path}: {exc}") from exc
        if res.status_code >= 500:
            raise FlowableUnavailableError(f"{method} {path}: HTTP {res.status_code} {res.text[:200]}")
        if res.status_code not in expected:
            raise FlowableError(f"{method} {path}: HTTP {res.status_code} {res.text[:300]}")
        return res.json() if res.content and "json" in res.headers.get("content-type", "") else None

    # -- repository ---------------------------------------------------------
    def deploy_if_changed(self, file_name: str, content: bytes) -> Deployment:
        """Idempotent deploy: the deployment name embeds the content hash.

        Re-deploying identical BPMN finds the existing deployment and does not
        create a new process definition version.
        """
        digest = hashlib.sha256(content).hexdigest()[:16]
        name = f"{file_name.removesuffix('.bpmn20.xml')}@{digest}"
        found = self._request("GET", "/service/repository/deployments", params={"name": name})
        if found["data"]:
            return Deployment(id=found["data"][0]["id"], name=name, created=False)
        created = self._request(
            "POST",
            "/service/repository/deployments",
            expected=(201,),
            params={"deploymentName": name},
            files={"file": (file_name, content, "application/xml")},
        )
        return Deployment(id=created["id"], name=name, created=True)

    def process_definitions(self, key: str) -> list[dict[str, Any]]:
        return self._request("GET", "/service/repository/process-definitions", params={"key": key})["data"]

    # -- runtime --------------------------------------------------------------
    def find_process_instance(self, definition_key: str, business_key: str) -> dict[str, Any] | None:
        """Running OR finished instance for this business key (history covers both)."""
        res = self._request(
            "GET",
            "/service/history/historic-process-instances",
            params={"processDefinitionKey": definition_key, "businessKey": business_key},
        )
        return res["data"][0] if res["data"] else None

    def start_process(
        self, definition_key: str, business_key: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Start once per business key: an existing (running or finished) instance is returned as-is."""
        existing = self.find_process_instance(definition_key, business_key)
        if existing:
            return existing
        return self._request(
            "POST",
            "/service/runtime/process-instances",
            expected=(201,),
            json={
                "processDefinitionKey": definition_key,
                "businessKey": business_key,
                "variables": _variables(variables),
            },
        )

    def tasks(self, process_instance_id: str, task_definition_key: str | None = None) -> list[dict[str, Any]]:
        params = {"processInstanceId": process_instance_id}
        if task_definition_key:
            params["taskDefinitionKey"] = task_definition_key
        return self._request("GET", "/service/runtime/tasks", params=params)["data"]

    def complete_task(self, task_id: str, variables: dict[str, Any] | None = None) -> None:
        self._request(
            "POST",
            f"/service/runtime/tasks/{task_id}",
            json={"action": "complete", "variables": _variables(variables)},
        )

    def historic_process_instance(self, process_instance_id: str) -> dict[str, Any]:
        return self._request("GET", f"/service/history/historic-process-instances/{process_instance_id}")

    # -- external worker jobs (pull callbacks) --------------------------------
    def acquire_jobs(self, topic: str, worker_id: str, lock_duration: str = "PT60S", count: int = 5) -> list[dict]:
        return self._request(
            "POST",
            "/external-job-api/acquire/jobs",
            json={"topic": topic, "workerId": worker_id, "lockDuration": lock_duration, "numberOfTasks": count},
        )

    def complete_job(self, job_id: str, worker_id: str, variables: dict[str, Any] | None = None) -> None:
        self._request(
            "POST",
            f"/external-job-api/acquire/jobs/{job_id}/complete",
            expected=(204,),
            json={"workerId": worker_id, "variables": _variables(variables)},
        )
