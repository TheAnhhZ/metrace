# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Business time: storage is UTC, business dates are computed in BUSINESS_TZ."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.settings import get_settings


def business_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().business_tz)


def utcnow() -> datetime:
    return datetime.now(UTC)


def service_date(at: datetime | None = None) -> date:
    """The business day an instant belongs to (00:00–23:59 local time)."""
    return (at or utcnow()).astimezone(business_tz()).date()


def local_datetime(day: date, at: time) -> datetime:
    """A local wall-clock time on a business day, returned in UTC."""
    return datetime.combine(day, at, tzinfo=business_tz()).astimezone(UTC)


def days_from_today(days: int, now: datetime | None = None) -> date:
    return service_date(now) + timedelta(days=days)
