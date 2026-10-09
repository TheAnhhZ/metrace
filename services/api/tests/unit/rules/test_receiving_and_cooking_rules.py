# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.reason_codes import ReasonCode as RC
from app.rules.cooking_rules import FinishSnapshot, check_finish
from app.rules.receiving_rules import LineSnapshot, ReceivingSnapshot, SupplierSnapshot, check_receiving
from app.rules.thresholds import DEFAULTS, Thresholds

TH = Thresholds.of(DEFAULTS)
TODAY = date(2026, 10, 9)
CHILLED_OK = LineSnapshot("Thịt lợn", "chilled", Decimal("3.5"))


def supplier(expires_in: int = 200, status: str = "active", locked: bool = False) -> SupplierSnapshot:
    return SupplierSnapshot("NCC-01", status, locked, [TODAY + timedelta(days=expires_in)])


def receive(lines=(CHILLED_OK,), docs: int = 1) -> ReceivingSnapshot:
    return ReceivingSnapshot(docs, list(lines))


def test_clean_receiving_passes_without_warnings():
    result = check_receiving(receive(), supplier(), TH, TODAY)
    assert result.ok and not result.warnings


def test_missing_documents_blocks():
    assert check_receiving(receive(docs=0), supplier(), TH, TODAY).codes() == [RC.P1_MISSING_DOCUMENTS]


def test_blocked_or_locked_supplier_blocks():
    assert RC.P1_SUPPLIER_BLOCKED in check_receiving(receive(), supplier(status="blocked"), TH, TODAY).codes()
    assert RC.P1_SUPPLIER_BLOCKED in check_receiving(receive(), supplier(locked=True), TH, TODAY).codes()


def test_expired_certificate_blocks_and_expiring_warns():
    expired = check_receiving(receive(), supplier(expires_in=-5), TH, TODAY)
    assert expired.codes() == [RC.P1_SUPPLIER_CERT_EXPIRED]
    expiring = check_receiving(receive(), supplier(expires_in=10), TH, TODAY)
    assert expiring.ok
    assert [w.code for w in expiring.warnings] == [RC.P1_SUPPLIER_CERT_EXPIRING]
    assert expiring.warnings[0].details["days_left"] == 10


def test_certificate_expiring_today_is_still_valid_and_boundary_warns():
    assert check_receiving(receive(), supplier(expires_in=0), TH, TODAY).ok
    assert check_receiving(receive(), supplier(expires_in=30), TH, TODAY).warnings
    assert not check_receiving(receive(), supplier(expires_in=31), TH, TODAY).warnings


def test_newest_valid_certificate_wins():
    sup = SupplierSnapshot("NCC-01", "active", False, [TODAY - timedelta(days=400), TODAY + timedelta(days=100)])
    assert check_receiving(receive(), sup, TH, TODAY).ok


def test_temperature_limits_by_storage_kind():
    at_limit = LineSnapshot("Rau", "chilled", Decimal("4"))
    too_warm = LineSnapshot("Rau", "chilled", Decimal("6"))
    frozen_soft = LineSnapshot("Cá", "frozen", Decimal("-12"))
    dry = LineSnapshot("Gạo", "dry", None)
    assert check_receiving(receive([at_limit, dry]), supplier(), TH, TODAY).ok
    result = check_receiving(receive([too_warm, frozen_soft]), supplier(), TH, TODAY)
    assert result.codes() == [RC.P1_TEMP_OUT_OF_RANGE, RC.P1_TEMP_OUT_OF_RANGE]
    assert result.violations[0].details["limit"] == "4"


def test_missing_temperature_for_chilled_goods_blocks():
    result = check_receiving(receive([LineSnapshot("Thịt", "chilled", None)]), supplier(), TH, TODAY)
    assert result.codes() == [RC.P1_TEMP_OUT_OF_RANGE]


START = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)


def test_finish_with_hot_core_passes_and_boundary_is_inclusive():
    assert check_finish(FinishSnapshot("B1", START, START + timedelta(hours=1), Decimal("75")), TH).ok


def test_finish_blocks_cold_core_and_missing_times():
    cold = check_finish(FinishSnapshot("B1", START, START + timedelta(hours=1), Decimal("70")), TH)
    assert cold.codes() == [RC.P2_CORE_TEMP_BELOW_MIN]
    no_times = check_finish(FinishSnapshot("B1", None, None, Decimal("90")), TH)
    assert no_times.codes() == [RC.P2_MISSING_TIMESTAMPS]
    backwards = check_finish(FinishSnapshot("B1", START, START - timedelta(minutes=1), Decimal("90")), TH)
    assert backwards.codes() == [RC.P2_MISSING_TIMESTAMPS]
    assert check_finish(FinishSnapshot("B1", START, START, None), TH).codes() == [RC.P2_CORE_TEMP_BELOW_MIN]
