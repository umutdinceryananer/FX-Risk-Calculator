from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

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


def test_rate_snapshot_coerces_timestamps_to_utc():
    naive = datetime(2025, 1, 1, 12, 30, 15)
    snapshot = RateSnapshot(
        base_currency="usd",
        source="test",
        timestamp=naive,
        rates={},
    )
    assert snapshot.timestamp.tzinfo == UTC
    assert snapshot.timestamp == naive.replace(tzinfo=UTC)

    aware = datetime(2025, 1, 1, 12, 30, tzinfo=ZoneInfo("Europe/Istanbul"))
    snapshot = RateSnapshot(
        base_currency="usd",
        source="test",
        timestamp=aware,
        rates={},
    )
    assert snapshot.timestamp.tzinfo == UTC
    assert snapshot.timestamp == aware.astimezone(UTC)


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


def test_rate_point_coerces_timestamp_to_utc():
    naive = datetime(2025, 2, 3, 5, 6)
    point = RatePoint(timestamp=naive, rate=Decimal("1.23"))
    assert point.timestamp.tzinfo == UTC
    assert point.timestamp == naive.replace(tzinfo=UTC)
