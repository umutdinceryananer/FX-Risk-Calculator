"""ExchangeRate.host provider unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import responses
from freezegun import freeze_time
from responses import matchers

from app.providers.base import ProviderError
from app.providers.exchangerate_client import ExchangeRateHostClient, ExchangeRateHostClientConfig
from app.providers.exchangerate_provider import ExchangeRateHostProvider
from app.services.currency_registry import registry
from tests.fixtures import load_json

pytestmark = pytest.mark.providers


@pytest.fixture(autouse=True)
def _seed_registry_codes():
    original_codes = set(registry.codes)
    registry.codes = {"USD", "EUR", "GBP", "JPY"}
    yield
    registry.codes = original_codes


@pytest.fixture()
def provider() -> ExchangeRateHostProvider:
    config = ExchangeRateHostClientConfig(
        base_url="https://api.exchangerate.host",
        timeout=2,
        max_retries=1,
        backoff_seconds=0,
    )
    client = ExchangeRateHostClient(config)
    return ExchangeRateHostProvider(client)


@responses.activate
def test_get_latest_normalizes_snapshot(provider: ExchangeRateHostProvider) -> None:
    responses.add(
        responses.GET,
        "https://api.exchangerate.host/latest",
        json=load_json("latest_usd.json"),
        match=[matchers.query_param_matcher({"base": "USD", "symbols": "EUR,GBP,JPY"})],
        status=200,
    )

    snapshot = provider.get_latest("usd")

    assert snapshot.base_currency == "USD"
    assert snapshot.source == provider.name
    assert snapshot.timestamp.tzinfo is UTC
    assert snapshot.rates == {
        "EUR": Decimal("0.94"),
        "GBP": Decimal("0.81"),
        "JPY": Decimal("148.12"),
    }


@freeze_time("2025-10-13T09:00:00Z")
@responses.activate
def test_get_history_returns_sorted_points(provider: ExchangeRateHostProvider) -> None:
    responses.add(
        responses.GET,
        "https://api.exchangerate.host/timeseries",
        json=load_json("history_usd_eur.json"),
        match=[
            matchers.query_param_matcher(
                {
                    "base": "USD",
                    "symbols": "EUR",
                    "start_date": "2025-10-11",
                    "end_date": "2025-10-13",
                }
            )
        ],
        status=200,
    )

    series = provider.get_history("USD", "EUR", days=3)

    assert series.base_currency == "USD"
    assert series.quote_currency == "EUR"
    assert [point.timestamp for point in series.points] == [
        datetime(2025, 10, 11, tzinfo=UTC),
        datetime(2025, 10, 12, tzinfo=UTC),
        datetime(2025, 10, 13, tzinfo=UTC),
    ]
    assert all(isinstance(point.rate, Decimal) for point in series.points)


@responses.activate
def test_get_latest_wraps_http_errors(provider: ExchangeRateHostProvider) -> None:
    responses.add(
        responses.GET,
        "https://api.exchangerate.host/latest",
        status=500,
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.get_latest("USD")

    assert "Failed to fetch" in str(exc_info.value)
