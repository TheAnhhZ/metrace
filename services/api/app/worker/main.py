# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Worker process: deploy BPMN, then run the outbox lane(s) and the reconciler.

Only the worker talks to Flowable. If Flowable is down, deploy is retried and
outbox rows wait (InfraError backoff); the API keeps working.
"""

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

from app.core.database import new_session
from app.core.settings import get_settings
from app.worker import handlers  # noqa: F401  (registers domain handlers)
from app.worker.handler_registry import HANDLERS
from app.worker.outbox_claim_loop import run_lane
from app.worker.reconciler import run_reconciler_loop
from app.workflow.bpmn_deployer import deploy_all
from app.workflow.flowable_client import FlowableClient, FlowableUnavailableError

log = logging.getLogger("metrace.worker")
BPMN_DIR = Path(os.environ.get("BPMN_DIR", "/srv/workflows/bpmn"))


def flowable_client() -> FlowableClient:
    s = get_settings()
    return FlowableClient(s.flowable_url, s.flowable_user, s.flowable_password)


def deploy_with_retry(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            with flowable_client() as client:
                deploy_all(client, BPMN_DIR)
            return
        except FlowableUnavailableError as exc:
            log.warning("flowable unavailable, retrying deploy in 5s: %s", exc)
            stop.wait(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    threads = [
        threading.Thread(target=run_lane, args=(new_session, "fast", HANDLERS, stop), name="lane-fast"),
        threading.Thread(target=run_reconciler_loop, args=(stop,), name="reconciler"),
    ]
    for thread in threads:
        thread.daemon = True  # never keep a broken process alive behind a green healthcheck
        thread.start()
    exit_code = 0
    try:
        deploy_with_retry(stop)
        while not stop.is_set():
            if not all(t.is_alive() for t in threads):
                raise RuntimeError("a worker loop died")
            time.sleep(1)
    except Exception:
        log.exception("worker failed; exiting so the container restarts")
        exit_code = 1
    stop.set()
    for thread in threads:
        thread.join(timeout=10)
    log.info("worker stopped (exit %s)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
