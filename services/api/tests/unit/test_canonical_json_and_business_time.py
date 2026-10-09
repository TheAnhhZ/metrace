# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
import uuid
from datetime import UTC, date, datetime, time

from app.core.business_time import local_datetime, service_date
from app.core.canonical_json import canonical_json, normalise


def test_canonical_json_is_order_independent_and_compact():
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1}) == '{"a":[1,2],"b":1}'


def test_canonical_json_keeps_vietnamese_text():
    assert canonical_json({"món": "Canh chua"}) == '{"món":"Canh chua"}'


def test_normalise_turns_rich_types_into_json_values():
    value = normalise({"id": uuid.UUID(int=1), "at": datetime(2026, 10, 9, tzinfo=UTC), "tags": {"b", "a"}})
    assert value == {"id": str(uuid.UUID(int=1)), "at": "2026-10-09T00:00:00+00:00", "tags": ["a", "b"]}


def test_service_date_uses_business_time_zone_around_midnight():
    # 23:30 and 00:30 Vietnam time (UTC+7) on either side of midnight.
    before = datetime(2026, 10, 9, 16, 30, tzinfo=UTC)  # 23:30 local, 9 Oct
    after = datetime(2026, 10, 9, 17, 30, tzinfo=UTC)  # 00:30 local, 10 Oct
    assert service_date(before) == date(2026, 10, 9)
    assert service_date(after) == date(2026, 10, 10)


def test_local_datetime_returns_utc():
    assert local_datetime(date(2026, 10, 9), time(11, 0)) == datetime(2026, 10, 9, 4, 0, tzinfo=UTC)
