# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.core.reason_codes import ReasonCode as RC
from app.rules.dispatch_rules import DispatchItem, DispatchSnapshot, check_dispatch
from app.rules.sample_rules import check_sample_discard, check_sample_quantity, eligible_discard_at
from app.rules.thresholds import DEFAULTS, Thresholds

TH = Thresholds.of(DEFAULTS)
NOW = datetime(2026, 10, 9, 4, 0, tzinfo=UTC)
GOOD = DispatchItem("B1", True, NOW - timedelta(minutes=30), True, True, 1300, True)


def ship(*items: DispatchItem, status: str = "ready") -> DispatchSnapshot:
    return DispatchSnapshot("SHP-1", status, list(items))


def test_complete_shipment_passes():
    assert check_dispatch(ship(GOOD), TH, NOW).ok


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"form1_complete": False}, RC.P3_MISSING_FORM_1),
        ({"finished_at": None}, RC.P3_MISSING_FORM_2),
        ({"form3_done": False}, RC.P3_MISSING_FORM_3),
        ({"in_menu": False}, RC.P3_DISH_NOT_IN_MENU),
        ({"has_sample": False}, RC.P3_SAMPLE_MISSING),
        ({"finished_at": NOW - timedelta(minutes=121)}, RC.P3_HOLD_TIME_EXCEEDED),
    ],
)
def test_each_missing_piece_blocks(change, code):
    assert check_dispatch(ship(replace(GOOD, **change)), TH, NOW).codes() == [code]


def test_hold_time_boundary_and_small_meals_need_no_sample():
    assert check_dispatch(ship(replace(GOOD, finished_at=NOW - timedelta(minutes=120))), TH, NOW).ok
    assert check_dispatch(ship(replace(GOOD, batch_portions=29, has_sample=False)), TH, NOW).ok
    assert not check_dispatch(ship(replace(GOOD, batch_portions=30, has_sample=False)), TH, NOW).ok


def test_held_or_empty_shipment_blocks():
    assert check_dispatch(ship(GOOD, status="held"), TH, NOW).codes() == [RC.P3_SHIPMENT_HELD]
    assert check_dispatch(ship(), TH, NOW).codes() == [RC.P3_SHIPMENT_EMPTY]


def test_all_violations_are_reported_together():
    bad = replace(GOOD, form1_complete=False, form3_done=False, in_menu=False)
    assert len(check_dispatch(ship(bad, GOOD), TH, NOW).violations) == 3


def test_sample_quantity_by_dish_kind():
    assert check_sample_quantity("solid", 100, None, TH).ok
    assert check_sample_quantity("solid", 99, None, TH).codes() == [RC.P4_SAMPLE_UNDER_MINIMUM]
    assert check_sample_quantity("liquid", None, 150, TH).ok
    assert check_sample_quantity("liquid", None, 149, TH).codes() == [RC.P4_SAMPLE_UNDER_MINIMUM]
    assert check_sample_quantity("liquid", 500, None, TH).codes() == [RC.P4_SAMPLE_UNDER_MINIMUM]


def test_retention_counts_from_the_later_of_storage_and_meal_end():
    stored, meal_end = NOW, NOW + timedelta(hours=3)
    eligible = eligible_discard_at(stored, meal_end, TH)
    assert eligible == meal_end + timedelta(hours=24)
    # 24 h after storage but before meal_end + 24 h: still blocked (RT-14).
    too_early = check_sample_discard(eligible, stored + timedelta(hours=25), TH)
    assert too_early.codes() == [RC.P4_DISCARD_BEFORE_RETENTION]
    assert too_early.violations[0].details["remaining_minutes"] > 0
    assert check_sample_discard(eligible, eligible, TH).ok
