# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""One-shot (part of `migrate`): make sure the S3 bucket exists. Idempotent."""

import logging
import time

from botocore.exceptions import BotoCoreError, ClientError

from app.core.object_storage import ensure_bucket

log = logging.getLogger("storage-bootstrap")


def main(attempts: int = 20, delay_seconds: float = 3.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    for attempt in range(1, attempts + 1):
        try:
            ensure_bucket()
            log.info("bucket ready")
            return
        except (BotoCoreError, ClientError) as exc:
            log.info("object storage not ready (%s), attempt %d/%d", exc, attempt, attempts)
            time.sleep(delay_seconds)
    raise SystemExit("object storage unavailable")


if __name__ == "__main__":
    main()
