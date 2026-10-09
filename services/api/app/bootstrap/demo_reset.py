# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""`python -m app.bootstrap.demo_reset --scenario baseline[,outbreak]`

Wipes transactional data (keeps master data and thresholds), removes metrace's
Flowable process instances and reseeds relative to now(). Runs as the schema
owner because the runtime role may not truncate the audit chain. The worker
must be stopped first (scripts/demo-reset.sh does that).
"""

import argparse
import logging
import os

from sqlalchemy import create_engine, text

from app.core.settings import get_settings
from app.seed.__main__ import run as run_seed
from app.workflow.flowable_client import FlowableClient, FlowableUnavailableError

log = logging.getLogger("demo-reset")

TRANSACTIONAL_TABLES = [
    "recall_notice",
    "incident_close_request",
    "lock",
    "incident_complaint",
    "incident",
    "complaint",
    "portion_check",
    "shipment_item",
    "shipment",
    "retained_sample",
    "batch_input",
    "cooking_batch",
    "ingredient_lot",
    "receiving",
    "menu_item",
    "menu",
    "poka_yoke_event",
    "outbox_event",
    "audit_event",
]
BUSINESS_KEY_PREFIXES = ("incident:", "coldchain:")


def clear_flowable() -> int:
    s = get_settings()
    removed = 0
    try:
        with FlowableClient(s.flowable_url, s.flowable_user, s.flowable_password) as client:
            for prefix in BUSINESS_KEY_PREFIXES:
                removed += client.delete_process_instances(business_key_like=f"{prefix}%")
    except FlowableUnavailableError as exc:
        log.warning("flowable unavailable, skipped process cleanup: %s", exc)
    return removed


def truncate() -> None:
    engine = create_engine(os.environ["MIGRATOR_DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TRANSACTIONAL_TABLES)} RESTART IDENTITY CASCADE"))
    engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m app.bootstrap.demo_reset")
    parser.add_argument("--scenario", default="baseline")
    args = parser.parse_args()
    log.info("flowable instances removed: %d", clear_flowable())
    truncate()
    log.info("transactional tables truncated")
    summary = run_seed([s.strip() for s in args.scenario.split(",") if s.strip()])
    log.info("reseeded: %s", summary)


if __name__ == "__main__":
    main()
