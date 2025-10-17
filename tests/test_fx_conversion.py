from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.fx_conversion import (
    RebaseError,
    convert_amount,
    convert_position_amount,
    normalize_currency,
    rebase_rates,
    rebase_snapshot,
)


def test_convert_amount_long_side():
    result = convert_amount("100", "1.25", side="LONG")
    assert result == Decimal("125")


def test_convert_amount_short_side():
    result = convert_amount(Decimal("50"), Decimal("2.0"), side="short")
    assert result == Decimal("-100")


def test_convert_amount_invalid_side():
    with pytest.raises(ValueError):
        convert_amount("10", "1.0", side="flat")


def test_convert_position_same_currency():
    amount = convert_position_amount(
        native_amount=Decimal("100"),
        position_currency="USD",
        portfolio_base="USD",
        rate_lookup={"USD": Decimal("1")},
        side="LONG",
    )
    assert amount == Decimal("100")


def test_convert_position_missing_rate():
    with pytest.raises(RebaseError):
        convert_position_amount(
            native_amount=Decimal("100"),
            position_currency="JPY",
            portfolio_base="USD",
            rate_lookup={"EUR": Decimal("1.1")},
            side="LONG",
        )


def test_convert_position_with_rate_lookup():
    amount = convert_position_amount(
        native_amount=Decimal("100"),
        position_currency="EUR",
        portfolio_base="USD",
        rate_lookup={"EUR": Decimal("1.2")},
        side="SHORT",
    )
    assert amount == Decimal("-120")


def test_rebase_rates_success():
    rates = {"USD": Decimal("1"), "EUR": Decimal("0.9"), "GBP": Decimal("0.8")}
    rebased = rebase_rates(rates, "EUR")
    assert rebased["EUR"] == Decimal("1")
    assert rebased["USD"] == Decimal("1") / Decimal("0.9")
    assert rebased["GBP"] == Decimal("0.8") / Decimal("0.9")


def test_rebase_rates_missing_currency():
    with pytest.raises(RebaseError):
        rebase_rates({"USD": Decimal("1")}, "JPY")


def test_rebase_rates_zero_rate():
    rates = {"USD": Decimal("1"), "EUR": Decimal("0"), "GBP": Decimal("0.8")}
    with pytest.raises(RebaseError):
        rebase_rates(rates, "EUR")


def test_rebase_snapshot_converts_usd_snapshot():
    rates = {"USD": Decimal("1"), "EUR": Decimal("0.9"), "GBP": Decimal("0.8")}
    rebased = rebase_snapshot(rates, "EUR")
    assert rebased["USD"] == Decimal("1")
    assert rebased["GBP"] == Decimal("0.8") / Decimal("0.9")
    assert "EUR" not in rebased


def test_rebase_snapshot_missing_target_currency():
    with pytest.raises(RebaseError):
        rebase_snapshot({"USD": Decimal("1"), "JPY": Decimal("150")}, "CHF")


def test_normalize_currency_rejects_blank():
    with pytest.raises(ValueError):
        normalize_currency(" ")
