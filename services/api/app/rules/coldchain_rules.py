# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Cold chain: a breach is N CONSECUTIVE readings (by server receive time) outside
the asset's safe band. One stray reading is noise, not an alarm."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.rules.thresholds import Thresholds


@dataclass(frozen=True)
class Band:
    min_c: Decimal | None
    max_c: Decimal | None

    def contains(self, temp: Decimal) -> bool:
        return (self.min_c is None or temp >= self.min_c) and (self.max_c is None or temp <= self.max_c)


def clock_skew_ok(device_ts: datetime, server_now: datetime, th: Thresholds) -> bool:
    return abs((server_now - device_ts).total_seconds()) <= float(th.get("coldchain_max_skew_s"))


def is_breach(latest_first: Sequence[Decimal], band: Band, th: Thresholds) -> bool:
    """`latest_first`: newest readings first (ordered by received_at DESC)."""
    n = int(th.get("coldchain_consecutive_n"))
    window = list(latest_first[:n])
    return len(window) == n and all(not band.contains(t) for t in window)
