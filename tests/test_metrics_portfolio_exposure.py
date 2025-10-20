from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.database import get_session
from app.models import FxRate, Portfolio, Position, PositionType


@pytest.fixture()
def seeded_portfolio(app):
    with app.app_context():
        session = get_session()

        portfolio = Portfolio(name="Exposure Book", base_currency_code="USD")
        session.add(portfolio)
        session.flush()

        positions = [
            Position(
                portfolio_id=portfolio.id,
                currency_code="USD",
                amount=Decimal("150"),
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
                amount=Decimal("40"),
                side=PositionType.SHORT,
            ),
            Position(
                portfolio_id=portfolio.id,
                currency_code="JPY",
                amount=Decimal("1000"),
                side=PositionType.LONG,
            ),
        ]
        session.add_all(positions)

        rates = [
            FxRate(
                base_currency_code="USD",
                target_currency_code="EUR",
                rate=Decimal("0.9"),
                timestamp=datetime(2025, 10, 17, 12, 0, tzinfo=UTC),
                source="mock",
            ),
            FxRate(
                base_currency_code="USD",
                target_currency_code="GBP",
                rate=Decimal("0.6"),
                timestamp=datetime(2025, 10, 17, 12, 0, tzinfo=UTC),
                source="mock",
            ),
            FxRate(
                base_currency_code="USD",
                target_currency_code="JPY",
                rate=Decimal("120"),
                timestamp=datetime(2025, 10, 17, 12, 0, tzinfo=UTC),
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


def test_exposure_default_base(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/exposure")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "USD"
    exposures = {item["currency_code"]: item for item in payload["exposures"]}
    assert "OTHER" not in exposures
    assert Decimal(exposures["USD"]["net_native"]) == Decimal("150")
    assert Decimal(exposures["USD"]["base_equivalent"]) == Decimal("150")
    assert Decimal(exposures["EUR"]["base_equivalent"]).quantize(Decimal("0.000000000001")) == Decimal("222.222222222222")
    assert Decimal(exposures["GBP"]["base_equivalent"]).quantize(Decimal("0.1")) == Decimal("-66.7")
    assert Decimal(exposures["JPY"]["base_equivalent"]).quantize(Decimal("0.000000000001")) == Decimal("8.333333333333")
    assert payload["priced"] == 4
    assert payload["unpriced"] == 0
    assert payload["unpriced_reasons"] == {}


def test_exposure_with_custom_base_and_topn(client, seeded_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/exposure?base=eur&top_n=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view_base"] == "EUR"
    exposures = payload["exposures"]
    assert exposures[-1]["currency_code"] == "OTHER"
    codes = [item["currency_code"] for item in exposures]
    assert len(exposures) == 3
    assert codes.count("OTHER") == 1
    assert payload["unpriced_reasons"] == {}


def test_exposure_missing_rates(client, app, seeded_portfolio):
    with app.app_context():
        session = get_session()
        session.query(FxRate).delete()
        session.commit()

    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/exposure")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["priced"] == 0
    assert payload["unpriced"] == 4
    assert payload["exposures"] == []
    assert payload["as_of"] is None
    reasons = payload["unpriced_reasons"]
    assert "missing_rate" in reasons
    assert set(reasons["missing_rate"]) == {"USD", "EUR", "GBP", "JPY"}


def test_exposure_missing_portfolio(client):
    response = client.get("/api/v1/metrics/portfolio/999/exposure")
    assert response.status_code == 404


def test_exposure_unknown_currency_reason(client, app, seeded_portfolio):
    with app.app_context():
        session = get_session()
        session.query(Position).filter(Position.currency_code == "JPY").update({"currency_code": "ZZZ"})
        session.commit()

    response = client.get(f"/api/v1/metrics/portfolio/{seeded_portfolio}/exposure")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["unpriced"] == 1
    reasons = payload["unpriced_reasons"]
    assert set(reasons.get("unknown_currency", [])) == {"ZZZ"}
