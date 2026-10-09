# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Deploy every BPMN in BPMN_DIR at worker start. Idempotent: unchanged files
do not create new process-definition versions (content hash in the name)."""

import logging
from pathlib import Path

from app.workflow.flowable_client import FlowableClient

log = logging.getLogger("metrace.worker.bpmn")


def deploy_all(client: FlowableClient, bpmn_dir: Path) -> list[str]:
    deployed = []
    for path in sorted(bpmn_dir.glob("*.bpmn20.xml")):
        result = client.deploy_if_changed(path.name, path.read_bytes())
        log.info("bpmn %s: %s", path.name, "deployed" if result.created else "unchanged")
        deployed.append(result.name)
    return deployed
