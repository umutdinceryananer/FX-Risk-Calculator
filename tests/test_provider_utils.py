from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.fx_conversion import RebaseError, rebase_rates


def test_rebase_rates_success():
    rates = {
        "USD": Decimal("1"),
        "EUR": Decimal("0.9"),
        "GBP": Decimal("0.8"),
    }
    rebased = rebase_rates(rates, "EUR")
    assert rebased["EUR"] == Decimal("1")
    assert rebased["USD"] == Decimal("1") / Decimal("0.9")
    assert rebased["GBP"] == Decimal("0.8") / Decimal("0.9")


def test_rebase_rates_missing_base():
    rates = {"USD": Decimal("1"), "GBP": Decimal("0.8")}
    with pytest.raises(RebaseError):
        rebase_rates(rates, "EUR")


def test_rebase_rates_zero_rate():
    rates = {"USD": Decimal("1"), "EUR": Decimal("0"), "GBP": Decimal("0.8")}
    with pytest.raises(RebaseError):
        rebase_rates(rates, "EUR")
