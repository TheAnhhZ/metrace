# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""File-based heartbeat per loop. `python -m app.worker.heartbeat` is the container healthcheck:
it fails if any expected loop has not touched its file for more than 30 s."""

import os
import sys
import time
from pathlib import Path

# Container-local scratch dir; only this process writes it.
HEARTBEAT_DIR = Path(os.environ.get("WORKER_HEARTBEAT_DIR", "/tmp/metrace-worker"))  # noqa: S108
STALE_AFTER_SECONDS = 30
EXPECTED_LOOPS = os.environ.get("WORKER_LOOPS", "fast,reconciler").split(",")


def touch(name: str) -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    (HEARTBEAT_DIR / name).touch()


def stale_loops(now: float | None = None) -> list[str]:
    now = now or time.time()
    stale = []
    for name in EXPECTED_LOOPS:
        path = HEARTBEAT_DIR / name
        if not path.exists() or now - path.stat().st_mtime > STALE_AFTER_SECONDS:
            stale.append(name)
    return stale


if __name__ == "__main__":
    stale = stale_loops()
    if stale:
        print(f"stale worker loops: {stale}")
        sys.exit(1)
    sys.exit(0)
