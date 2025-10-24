from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.database import get_session
from app.models import FxRate, Portfolio, Position, PositionType
from app.services.currency_registry import registry


@pytest.fixture()
def seeded_portfolio(app):
    with app.app_context():
        registry.update({"USD", "EUR", "GBP", "TRY"})

        session = get_session()

        portfolio = Portfolio(name="WhatIf Book", base_currency_code="USD")
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
            Position(
                portfolio_id=portfolio.id,
                currency_code="GBP",
                amount=Decimal("50"),
                side=PositionType.SHORT,
            ),
        ]
        session.add_all(positions)

        rates = [
            FxRate(
                base_currency_code="USD",
                target_currency_code="EUR",
                rate=Decimal("0.80"),
                timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
                source="mock",
            ),
            FxRate(
                base_currency_code="USD",
                target_currency_code="GBP",
                rate=Decimal("0.50"),
                timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
                source="mock",
            ),
        ]
        session.add_all(rates)
        session.commit()

        yield portfolio.id

        session.query(FxRate).delete()
        session.query(Position).delete()
        session.query(Portfolio).delete()
        session.commit()


def test_portfolio_whatif_positive_shock(client, seeded_portfolio):
    payload = {"currency": "EUR", "shock_pct": "5"}
    response = client.post(
        f"/api/v1/metrics/portfolio/{seeded_portfolio}/whatif",
        json=payload,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["portfolio_id"] == seeded_portfolio
    assert data["shocked_currency"] == "EUR"
    assert data["shock_pct"] == "5"
    assert Decimal(data["current_value"]) == Decimal("250")
    # EUR position goes to 210 in USD terms => delta +10, new value 260
    assert Decimal(data["new_value"]) == Decimal("262.5")
    assert Decimal(data["delta_value"]) == Decimal("12.5")
    assert data["as_of"] is not None


def test_portfolio_whatif_negative_shock_with_base(client, seeded_portfolio):
    payload = {"currency": "GBP", "shock_pct": "-10"}
    response = client.post(
        f"/api/v1/metrics/portfolio/{seeded_portfolio}/whatif?base=eur",
        json=payload,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["view_base"] == "EUR"
    assert data["shocked_currency"] == "GBP"
    assert data["shock_pct"] == "-10"
    assert Decimal(data["current_value"]) == Decimal("200")
    # GBP short loses magnitude when GBP weakens => EUR P&L adjusts accordingly
    assert Decimal(data["new_value"]) == Decimal("208")
    assert Decimal(data["delta_value"]) == Decimal("8")


def test_portfolio_whatif_rejects_out_of_range_shock(client, seeded_portfolio):
    payload = {"currency": "EUR", "shock_pct": "15"}
    response = client.post(
        f"/api/v1/metrics/portfolio/{seeded_portfolio}/whatif",
        json=payload,
    )
    assert response.status_code == 422
    data = response.get_json()
    assert data["errors"]["json"]["shock_pct"]


def test_portfolio_whatif_fails_when_no_positions(client, app, seeded_portfolio):
    with app.app_context():
        session = get_session()
        session.query(Position).delete()
        session.commit()

    response = client.post(
        f"/api/v1/metrics/portfolio/{seeded_portfolio}/whatif",
        json={"currency": "EUR", "shock_pct": "1"},
    )
    assert response.status_code == 422
    assert response.get_json()["message"] == "Portfolio has no positions to simulate."


def test_portfolio_whatif_missing_portfolio(client):
    response = client.post(
        "/api/v1/metrics/portfolio/999/whatif",
        json={"currency": "USD", "shock_pct": "1"},
    )
    assert response.status_code == 404


def test_portfolio_whatif_rejects_missing_base_rate(client, seeded_portfolio):
    payload = {"currency": "EUR", "shock_pct": "5"}
    response = client.post(
        f"/api/v1/metrics/portfolio/{seeded_portfolio}/whatif?base=TRY",
        json=payload,
    )
    assert response.status_code == 422
    data = response.get_json()
    assert data["view_base"] == "TRY"
    assert data["field"] == "base"
    assert data["as_of"] == "2025-10-16T12:00:00+00:00"
