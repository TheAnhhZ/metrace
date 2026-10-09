# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.core.principal import principal_from_claims
from app.rules.coldchain_rules import Band, clock_skew_ok, is_breach
from app.rules.thresholds import DEFAULTS, Thresholds

TH = Thresholds.of(DEFAULTS)
FRIDGE = Band(D("2"), D("8"))


def test_three_consecutive_out_of_band_readings_are_a_breach():
    assert is_breach([D("9.1"), D("8.5"), D("10")], FRIDGE, TH)


def test_one_good_reading_in_the_window_is_not_a_breach():
    assert not is_breach([D("9.1"), D("7.9"), D("10")], FRIDGE, TH)


def test_too_few_readings_or_band_edges_are_not_a_breach():
    assert not is_breach([D("12"), D("12")], FRIDGE, TH)
    assert not is_breach([D("8"), D("2"), D("8")], FRIDGE, TH)
    assert is_breach([D("1.9"), D("1.5"), D("0")], FRIDGE, TH)  # too cold also breaks the band


def test_open_band_side():
    assert not is_breach([D("-30")] * 3, Band(None, D("-15")), TH)


def test_clock_skew_window():
    now = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)
    assert clock_skew_ok(now - timedelta(seconds=60), now, TH)
    assert not clock_skew_ok(now - timedelta(seconds=61), now, TH)
    assert not clock_skew_ok(now + timedelta(minutes=5), now, TH)


def test_asset_codes_claim_is_parsed():
    p = principal_from_claims({"sub": "s", "realm_access": {"roles": ["sensor"]}, "asset_codes": "TU-MAU-01, XE-01"})
    assert p.asset_codes == {"TU-MAU-01", "XE-01"}
    assert principal_from_claims({"sub": "s"}).asset_codes == frozenset()
