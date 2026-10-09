# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""`python -m app.seed --scenario baseline` (one-shot `seed` in compose). Idempotent.

All data is synthetic and relative to now() in BUSINESS_TZ, so a fresh seed
always shows "today".
"""

import argparse
import logging
from datetime import datetime

from app.core.audit_hash_chain import append_audit
from app.core.business_time import service_date, utcnow
from app.core.database import new_session
from app.seed.baseline_scenario import seed_baseline
from app.seed.master_data_loader import load_master_data
from app.seed.outbreak_scenario import seed_outbreak

log = logging.getLogger("seed")
SCENARIOS = {"baseline": seed_baseline, "outbreak": seed_outbreak}


def run(scenarios: list[str], now: datetime | None = None) -> dict[str, object]:
    now = now or utcnow()
    unknown = [s for s in scenarios if s not in SCENARIOS]
    if unknown:
        raise SystemExit(f"unknown scenario(s): {unknown}; available: {sorted(SCENARIOS)}")
    with new_session() as session:
        master = load_master_data(session, service_date(now))
        summary: dict[str, object] = {}
        for name in scenarios:
            summary[name] = SCENARIOS[name](session, master, now)
        append_audit(
            session, actor="seed", action="seed.run", entity_type="seed", entity_id=",".join(scenarios), payload=summary
        )
        session.commit()
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m app.seed")
    parser.add_argument("--scenario", default="baseline", help="comma separated: " + ",".join(SCENARIOS))
    parser.add_argument("--now", type=datetime.fromisoformat, help="pretend time (ISO 8601 with offset), for tests")
    args = parser.parse_args()
    summary = run([s.strip() for s in args.scenario.split(",") if s.strip()], args.now)
    log.info("seed done: %s", summary)


if __name__ == "__main__":
    main()
