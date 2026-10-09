# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Settings that shape recalls are bounded: a typo in .env must stop the service, not widen a recall."""

import pytest
from pydantic import ValidationError

from app.core.settings import Settings


@pytest.mark.parametrize("days", ["-1", "31"])
def test_recall_window_out_of_range_is_rejected(monkeypatch, days):
    monkeypatch.setenv("RECALL_WINDOW_DAYS", days)
    with pytest.raises(ValidationError):
        Settings()


def test_recall_window_defaults_to_three_days(monkeypatch):
    monkeypatch.delenv("RECALL_WINDOW_DAYS", raising=False)
    assert Settings().recall_window_days == 3
