from __future__ import annotations

from decimal import Decimal

import pytest

from app.providers import (
    BaseRateProvider,
    ExchangeRateHostProvider,
    ProviderError,
    RateHistorySeries,
    RateSnapshot,
)
from app.providers.frankfurter_provider import FrankfurterProvider
from app.providers.mock import MockRateProvider
from app.providers.registry import (
    get_provider,
    init_provider,
    list_providers,
    register_provider,
    reset_registry,
)


@pytest.fixture(autouse=True)
def _reset_providers():
    reset_registry()
    yield
    reset_registry()


def test_default_provider_is_mock():
    provider = get_provider()
    assert isinstance(provider, MockRateProvider)
    snapshot = provider.get_latest("usd")
    assert isinstance(snapshot, RateSnapshot)
    assert snapshot.base_currency == "USD"
    assert snapshot.source == provider.name
    assert {"EUR", "GBP", "JPY"}.issubset(snapshot.rates.keys())


def test_get_provider_respects_environment(monkeypatch):
    class AlternateProvider(MockRateProvider):
        name = "alternate"

    register_provider("alternate", AlternateProvider)
    monkeypatch.setenv("FX_RATE_PROVIDER", "alternate")

    provider = get_provider()
    assert isinstance(provider, AlternateProvider)


def test_get_provider_unknown_name_raises():
    with pytest.raises(ProviderError):
        get_provider("does-not-exist")


def test_history_contract_returns_series():
    provider = get_provider()
    series = provider.get_history("usd", "eur", days=5)
    assert isinstance(series, RateHistorySeries)
    assert series.base_currency == "USD"
    assert series.quote_currency == "EUR"
    assert len(series.points) == 5
    assert all(point.rate >= Decimal("1.00") for point in series.points)
    timestamps = [point.timestamp for point in series.points]
    assert timestamps == sorted(timestamps)


def test_init_provider_attaches_to_app(app):
    provider = init_provider(app)
    assert isinstance(provider, BaseRateProvider)
    assert app.extensions["rate_provider"] is provider
    assert ExchangeRateHostProvider.name in list_providers()
    assert FrankfurterProvider.name in list_providers()
