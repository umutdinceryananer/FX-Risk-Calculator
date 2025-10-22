"""Unit tests targeting portfolio metric calculation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models import Currency, FxRate, Portfolio, Position, PositionType
from app.services.portfolio_metrics import (
    calculate_currency_exposure,
    calculate_daily_pnl,
    calculate_portfolio_value,
)

pytestmark = pytest.mark.calculations


def _create_sample_portfolio(db_session) -> Portfolio:
    portfolio = Portfolio(name="Calc Portfolio", base_currency_code="USD")
    db_session.add(portfolio)
    db_session.flush()

    positions = [
        Position(
            portfolio_id=portfolio.id,
            currency_code="EUR",
            amount=Decimal("1000"),
            side=PositionType.LONG,
        ),
        Position(
            portfolio_id=portfolio.id,
            currency_code="GBP",
            amount=Decimal("500"),
            side=PositionType.SHORT,
        ),
        Position(
            portfolio_id=portfolio.id,
            currency_code="USD",
            amount=Decimal("2000"),
            side=PositionType.LONG,
        ),
    ]
    db_session.add_all(positions)
    db_session.flush()
    return portfolio


def _insert_rate_snapshot(
    db_session,
    timestamp: datetime,
    rates: dict[str, Decimal],
    *,
    source: str = "unit",
) -> None:
    rows = [
        FxRate(
            base_currency_code="USD",
            target_currency_code=code,
            timestamp=timestamp,
            rate=rate,
            source=source,
        )
        for code, rate in rates.items()
    ]
    db_session.add_all(rows)
    db_session.flush()


def test_calculate_portfolio_value_rebases_to_view_base(app, db_session):
    portfolio = _create_sample_portfolio(db_session)
    as_of = datetime(2025, 10, 21, 12, 0, tzinfo=UTC)
    _insert_rate_snapshot(
        db_session,
        as_of,
        {
            "EUR": Decimal("0.90"),
            "GBP": Decimal("0.80"),
        },
    )

    with app.app_context():
        app.config["FX_CANONICAL_BASE"] = "USD"
        result = calculate_portfolio_value(portfolio.id, view_base="EUR")

    assert result.portfolio_id == portfolio.id
    assert result.portfolio_base == "USD"
    assert result.view_base == "EUR"
    assert result.as_of.replace(tzinfo=None) == as_of.replace(tzinfo=None)
    assert result.value == Decimal("2237.50")
    assert result.priced == 3
    assert result.unpriced == 0
    assert result.unpriced_reasons == {}


def test_calculate_currency_exposure_groups_tail(app, db_session):
    portfolio = _create_sample_portfolio(db_session)
    snapshot_time = datetime(2025, 10, 22, 9, 0, tzinfo=UTC)
    _insert_rate_snapshot(
        db_session,
        snapshot_time,
        {
            "EUR": Decimal("0.90"),
            "GBP": Decimal("0.80"),
        },
    )

    with app.app_context():
        app.config["FX_CANONICAL_BASE"] = "USD"
        result = calculate_currency_exposure(portfolio.id, top_n=2, view_base="EUR")

    assert result.portfolio_id == portfolio.id
    assert result.as_of.replace(tzinfo=None) == snapshot_time.replace(tzinfo=None)
    assert result.priced == 3
    assert result.unpriced == 0
    assert [ex.currency_code for ex in result.exposures] == ["USD", "EUR", "OTHER"]

    usd_exposure, eur_exposure, other_exposure = result.exposures
    assert usd_exposure.net_native == Decimal("2000.0000")
    assert usd_exposure.base_equivalent == Decimal("1800.00")

    assert eur_exposure.net_native == Decimal("1000.0000")
    assert eur_exposure.base_equivalent == Decimal("1000.00")

    assert other_exposure.currency_code == "OTHER"
    assert other_exposure.net_native == Decimal("-500.0000")
    assert other_exposure.base_equivalent == Decimal("-562.50")
    assert result.unpriced_reasons == {}


def test_calculate_daily_pnl_returns_expected_delta(app, db_session):
    portfolio = _create_sample_portfolio(db_session)
    prev_ts = datetime(2025, 10, 20, 12, 0, tzinfo=UTC)
    latest_ts = datetime(2025, 10, 21, 12, 0, tzinfo=UTC)

    _insert_rate_snapshot(
        db_session,
        prev_ts,
        {
            "EUR": Decimal("0.90"),
            "GBP": Decimal("0.80"),
        },
        source="pricing",
    )
    _insert_rate_snapshot(
        db_session,
        latest_ts,
        {
            "EUR": Decimal("0.95"),
            "GBP": Decimal("0.78"),
        },
        source="pricing",
    )

    with app.app_context():
        app.config["FX_CANONICAL_BASE"] = "USD"
        result = calculate_daily_pnl(portfolio.id, view_base="USD")

    assert result.as_of.replace(tzinfo=None) == latest_ts.replace(tzinfo=None)
    assert result.prev_date.replace(tzinfo=None) == prev_ts.replace(tzinfo=None)
    assert result.priced_current == 3
    assert result.priced_previous == 3
    assert result.unpriced_current == 0
    assert result.unpriced_previous == 0
    assert result.unpriced_reasons_current == {}
    assert result.unpriced_reasons_previous == {}
    assert result.value_previous == Decimal("2486.11")
    assert result.value_current == Decimal("2411.61")
    assert result.pnl == Decimal("-74.50")


def test_calculate_portfolio_value_marks_unknown_currencies(app, db_session):
    currency = Currency(code="XOT", name="Experimental Token")
    db_session.add(currency)
    db_session.flush()

    portfolio = Portfolio(name="Unknown CCY", base_currency_code="USD")
    db_session.add(portfolio)
    db_session.flush()

    position = Position(
        portfolio_id=portfolio.id,
        currency_code="XOT",
        amount=Decimal("100"),
        side=PositionType.LONG,
    )
    db_session.add(position)
    db_session.flush()

    as_of = datetime(2025, 10, 23, 8, 0, tzinfo=UTC)
    _insert_rate_snapshot(
        db_session,
        as_of,
        {
            "EUR": Decimal("0.92"),
        },
    )

    with app.app_context():
        app.config["FX_CANONICAL_BASE"] = "USD"
        result = calculate_portfolio_value(portfolio.id, view_base="USD")

    assert result.value == Decimal("0.00")
    assert result.priced == 0
    assert result.unpriced == 1
    assert result.unpriced_reasons == {"unknown_currency": ["XOT"]}
    assert result.as_of.replace(tzinfo=None) == as_of.replace(tzinfo=None)
