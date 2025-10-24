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
        session = get_session()

        portfolio = Portfolio(name="Metrics Book", base_currency_code="USD")
        session.add(portfolio)
        session.flush()

        registry.update({"USD", "EUR", "GBP", "TRY"})

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
                rate=Decimal("0.8"),
                timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
                source="mock",
            ),
            FxRate(
                base_currency_code="USD",
                target_currency_code="GBP",
                rate=Decimal("0.5"),
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


def test_portfolio_value_default_base(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["portfolio_base"] == "USD"
    assert payload["view_base"] == "USD"
    assert payload["priced"] == 3
    assert payload["unpriced"] == 0
    assert Decimal(payload["value"]) == Decimal("250")
    assert payload["as_of"] is not None
    assert payload["unpriced_reasons"] == {}


def test_portfolio_value_with_custom_base(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value?base=eur")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "EUR"
    # USD 100 -> EUR 80, EUR 200 -> EUR 200, GBP short 50 -> rate 0.5 => USD -25 -> EUR -20
    assert Decimal(payload["value"]) == Decimal("200")
    assert payload["unpriced_reasons"] == {}


def test_portfolio_value_with_gbp_base(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value?base=GBP")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "GBP"
    assert Decimal(payload["value"]) == Decimal("125.00")
    assert payload["unpriced_reasons"] == {}


def test_portfolio_value_handles_missing_rates(client, app, seeded_portfolio):
    with app.app_context():
        session = get_session()
        session.query(FxRate).delete()
        session.commit()

    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["priced"] == 0
    assert payload["unpriced"] == 3
    assert payload["value"] == "0.00"
    assert payload["as_of"] is None
    reasons = payload["unpriced_reasons"]
    assert "missing_rate" in reasons
    assert set(reasons["missing_rate"]) == {"USD", "EUR", "GBP"}


def test_portfolio_value_returns_404_for_missing_portfolio(client):
    response = client.get("/api/v1/metrics/portfolio/999/value")
    assert response.status_code == 404


def test_portfolio_value_rejects_missing_base_rate(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value?base=TRY")
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["view_base"] == "TRY"
    assert payload["field"] == "base"
    assert payload["as_of"] == "2025-10-16T12:00:00+00:00"
    assert "FX rates are unavailable" in payload["message"]


def test_portfolio_value_flags_unknown_currency(client, app, seeded_portfolio):
    with app.app_context():
        session = get_session()
        session.query(Position).filter(Position.currency_code == "GBP").update(
            {"currency_code": "ZZZ"}
        )
        session.commit()

    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/value")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["unpriced"] == 1
    reasons = payload["unpriced_reasons"]
    assert set(reasons.get("unknown_currency", [])) == {"ZZZ"}
