# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Every 30 s, run the registered reconcilers (DB <-> Flowable drift repair).

Example (phase 05): an open incident without a running process gets one
started; a completed Flowable task flips the matching flag in the DB.
"""

import logging
import threading

from app.worker import heartbeat
from app.worker.handler_registry import RECONCILERS

log = logging.getLogger("metrace.worker.reconciler")
INTERVAL_SECONDS = 30.0


def run_reconcilers_once() -> None:
    for fn in RECONCILERS:
        try:
            fn()
        except Exception:
            log.exception("reconciler %s failed", fn.__name__)


def run_reconciler_loop(stop: threading.Event, interval: float = INTERVAL_SECONDS) -> None:
    while not stop.is_set():
        heartbeat.touch("reconciler")
        run_reconcilers_once()
        # Touch while waiting so a long interval never looks like a dead loop.
        waited = 0.0
        while waited < interval and not stop.is_set():
            stop.wait(5.0)
            waited += 5.0
            heartbeat.touch("reconciler")
