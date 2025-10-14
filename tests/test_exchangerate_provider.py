from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import responses
from responses import matchers

from app.providers.base import ProviderError
from app.providers.exchangerate_client import ExchangeRateHostClient, ExchangeRateHostClientConfig
from app.providers.exchangerate_provider import ExchangeRateHostProvider
from app.services.currency_registry import registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _seed_registry_codes():
    original_codes = set(registry.codes)
    registry.codes = {
        "USD",
        "EUR",
        "GBP",
        "JPY",
    }
    yield
    registry.codes = original_codes


@pytest.fixture()
def provider():
    config = ExchangeRateHostClientConfig(
        base_url="https://api.exchangerate.host",
        timeout=2,
        max_retries=1,
        backoff_seconds=0,
    )
    client = ExchangeRateHostClient(config)
    return ExchangeRateHostProvider(client)


def load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text())


@responses.activate
def test_get_latest_returns_normalized_snapshot(provider):
    responses.add(
        responses.GET,
        "https://api.exchangerate.host/latest",
        json=load_fixture("latest_usd.json"),
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


@responses.activate
def test_get_history_returns_chronological_series(provider):
    fixed_end = datetime(2025, 10, 13, tzinfo=UTC)

    class FixedProvider(ExchangeRateHostProvider):
        @staticmethod
        def _current_date():
            return fixed_end.date()

    fixed_provider = FixedProvider(provider._client)  # type: ignore[attr-defined]

    responses.add(
        responses.GET,
        "https://api.exchangerate.host/timeseries",
        json=load_fixture("history_usd_eur.json"),
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

    series = fixed_provider.get_history("USD", "EUR", days=3)

    assert series.base_currency == "USD"
    assert series.quote_currency == "EUR"
    assert len(series.points) == 3
    assert all(isinstance(point.rate, Decimal) for point in series.points)
    timestamps = [point.timestamp for point in series.points]
    assert timestamps == sorted(timestamps)
    assert timestamps[-1] == datetime(2025, 10, 13, tzinfo=UTC)


@responses.activate
def test_provider_wraps_http_errors(provider):
    responses.add(
        responses.GET,
        "https://api.exchangerate.host/latest",
        status=500,
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.get_latest("USD")

    assert "ExchangeRate.host" in str(exc_info.value)
