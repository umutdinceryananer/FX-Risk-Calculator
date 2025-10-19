from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.database import get_session
from app.models import FxRate, Portfolio, Position, PositionType


@pytest.fixture()
def value_series_portfolio(app):
    with app.app_context():
        session = get_session()

        portfolio = Portfolio(name="Timeline Book", base_currency_code="USD")
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

        def add_rate(ts: datetime, rate: str) -> None:
            session.add(
                FxRate(
                    base_currency_code="USD",
                    target_currency_code="EUR",
                    rate=Decimal(rate),
                    timestamp=ts,
                    source="mock",
                )
            )

        add_rate(datetime(2025, 10, 17, 9, 0, tzinfo=UTC), "0.5200")
        add_rate(datetime(2025, 10, 17, 16, 30, tzinfo=UTC), "0.5000")
        add_rate(datetime(2025, 10, 18, 8, 15, tzinfo=UTC), "0.4500")
        add_rate(datetime(2025, 10, 18, 18, 45, tzinfo=UTC), "0.4000")
        add_rate(datetime(2025, 10, 20, 12, 0, tzinfo=UTC), "0.2500")

        session.commit()

        yield portfolio.id

        session.query(FxRate).delete()
        session.query(Position).delete()
        session.query(Portfolio).delete()
        session.commit()


def test_value_series_default_base(client, value_series_portfolio):
    response = client.get(f"/api/v1/metrics/portfolio/{value_series_portfolio}/value/series")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["portfolio_id"] == value_series_portfolio
    assert payload["view_base"] == "USD"

    series = payload["series"]
    assert [point["date"] for point in series] == ["2025-10-17", "2025-10-18", "2025-10-20"]

    expected = [
        Decimal("100") + Decimal("200") / Decimal("0.5000"),
        Decimal("100") + Decimal("200") / Decimal("0.4000"),
        Decimal("100") + Decimal("200") / Decimal("0.2500"),
    ]

    for point, expected_value in zip(series, expected):
        assert Decimal(point["value"]) == expected_value


def test_value_series_custom_base_and_days(client, value_series_portfolio):
    response = client.get(
        f"/api/v1/metrics/portfolio/{value_series_portfolio}/value/series?base=eur&days=2"
    )
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["view_base"] == "EUR"
    series = payload["series"]
    assert [point["date"] for point in series] == ["2025-10-18", "2025-10-20"]

    expected = [
        Decimal("200") + (Decimal("100") * Decimal("0.4000")),
        Decimal("200") + (Decimal("100") * Decimal("0.2500")),
    ]
    for point, expected_value in zip(series, expected):
        assert Decimal(point["value"]) == expected_value


def test_value_series_validation(client, value_series_portfolio):
    response = client.get(
        f"/api/v1/metrics/portfolio/{value_series_portfolio}/value/series?days=0"
    )
    assert response.status_code == 422


def test_value_series_missing_portfolio(client):
    response = client.get("/api/v1/metrics/portfolio/999/value/series")
    assert response.status_code == 404


def test_value_series_empty_positions(app, client, value_series_portfolio):
    with app.app_context():
        session = get_session()
        session.query(Position).delete()
        session.commit()

    response = client.get(
        f"/api/v1/metrics/portfolio/{value_series_portfolio}/value/series"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["series"] == []

