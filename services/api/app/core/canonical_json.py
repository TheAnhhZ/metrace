# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic JSON for hashing: sorted keys, no whitespace, UTF-8."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _default(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, set | frozenset):
        return sorted(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    # allow_nan=False: NaN/Infinity are not JSON and jsonb rejects them; fail loudly here.
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_default, allow_nan=False
    )


def normalise(value: Any) -> Any:
    """JSON-safe copy (UUIDs, dates, sets become JSON values). Not for hashing: hash what PG returns."""
    return json.loads(canonical_json(value))
