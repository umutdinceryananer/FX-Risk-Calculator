from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.providers.schemas import RateHistorySeries, RatePoint, RateSnapshot


def test_rate_snapshot_normalizes_codes_and_rates():
    snapshot = RateSnapshot(
        base_currency="usd",
        source="test",
        timestamp=datetime.now(UTC),
        rates={"eur": 0.9, "jpy": "150.123"},
    )
    assert snapshot.base_currency == "USD"
    assert snapshot.rates == {"EUR": Decimal("0.9"), "JPY": Decimal("150.123")}


def test_rate_snapshot_requires_source():
    with pytest.raises(ValueError):
        RateSnapshot(base_currency="usd", source="", timestamp=datetime.now(UTC))


def test_rate_history_series_requires_rate_points():
    points = [RatePoint(timestamp=datetime.now(UTC), rate=1.2345)]
    series = RateHistorySeries(
        base_currency="usd",
        quote_currency="eur",
        source="provider",
        points=points,
    )
    assert series.base_currency == "USD"
    assert series.quote_currency == "EUR"
    assert series.points == points


def test_rate_history_series_rejects_invalid_point():
    with pytest.raises(TypeError):
        RateHistorySeries(
            base_currency="usd",
            quote_currency="eur",
            source="provider",
            points=[{"timestamp": datetime.now(UTC), "rate": 1.0}],
        )
