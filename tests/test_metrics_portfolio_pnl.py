from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.database import get_session
from app.models import FxRate, Portfolio, Position, PositionType


@pytest.fixture()
def seeded_portfolio(app):
    with app.app_context():
        session = get_session()

        portfolio = Portfolio(name="PnL Book", base_currency_code="USD")
        session.add(portfolio)
        session.flush()

        positions = [
            Position(
                portfolio_id=portfolio.id,
                currency_code="USD",
                amount=Decimal("100"),
                side=PositionType.LONG,
            ),
            Position(
                portfolio_id=portfolio.id,
                currency_code="EUR",
                amount=Decimal("200"),
                side=PositionType.LONG,
            ),
        ]
        session.add_all(positions)

        now = datetime(2025, 10, 20, 12, 0, tzinfo=UTC)
        previous = now - timedelta(days=1)

        rates = [
            FxRate(
                base_currency_code="USD",
                target_currency_code="EUR",
                rate=Decimal("1.25"),
                timestamp=now,
                source="mock",
            ),
            FxRate(
                base_currency_code="USD",
                target_currency_code="EUR",
                rate=Decimal("1.1764705882352941"),
                timestamp=previous,
                source="mock",
            ),
        ]
        session.add_all(rates)
        session.commit()

        yield portfolio.id, now, previous

        session.query(FxRate).delete()
        session.query(Position).delete()
        session.query(Portfolio).delete()
        session.commit()


def test_daily_pnl_default_base(client, seeded_portfolio):
    portfolio_id, now, previous = seeded_portfolio
    response = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/pnl/daily")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "USD"
    assert payload["as_of"] == now.isoformat()
    assert payload["prev_date"] == previous.isoformat()
    assert Decimal(payload["value_current"]).quantize(Decimal("0.001")) == Decimal("260.000")
    assert Decimal(payload["value_previous"]).quantize(Decimal("0.001")) == Decimal("270.000")
    assert Decimal(payload["pnl"]).quantize(Decimal("0.001")) == Decimal("-10.000")
    assert payload["positions_changed"] is False
    assert payload["priced_current"] == 2
    assert payload["unpriced_current"] == 0
    assert payload["unpriced_current_reasons"] == {}
    assert payload["unpriced_previous_reasons"] == {}


def test_daily_pnl_custom_base(client, seeded_portfolio):
    portfolio_id, _, _ = seeded_portfolio
    response = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/pnl/daily?base=eur")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "EUR"
    assert Decimal(payload["pnl"]).quantize(Decimal("0.000001")) == Decimal("7.352941")
    assert payload["unpriced_current_reasons"] == {}
    assert payload["unpriced_previous_reasons"] == {}


def test_daily_pnl_missing_rates(client, app, seeded_portfolio):
    portfolio_id, _, _ = seeded_portfolio
    with app.app_context():
        session = get_session()
        session.query(FxRate).delete()
        session.commit()

    response = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/pnl/daily")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["value_previous"] is None
    assert payload["value_current"] == "0"
    assert payload["priced_current"] == 0
    assert payload["unpriced_current"] == 2
    reasons_current = payload["unpriced_current_reasons"]
    reasons_previous = payload["unpriced_previous_reasons"]
    assert set(reasons_current["missing_rate"]) == {"USD", "EUR"}
    assert set(reasons_previous["missing_rate"]) == {"USD", "EUR"}


def test_daily_pnl_missing_portfolio(client):
    response = client.get("/api/v1/metrics/portfolio/999/pnl/daily")
    assert response.status_code == 404
