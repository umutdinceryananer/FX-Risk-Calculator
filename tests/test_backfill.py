from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.providers.schemas import RateHistorySeries, RatePoint
from app.services.backfill import run_backfill
from app.services.currency_registry import registry


class DummyProvider:
    def __init__(self, history_map):
        self.history_map = history_map
        self.calls = []

    def get_history(self, base, symbol, days):
        self.calls.append((base, symbol, days))
        return self.history_map[symbol]


class DummyOrchestrator:
    def __init__(self, provider):
        self._primary = provider


@pytest.fixture
def history_series():
    return {
        "EUR": RateHistorySeries(
            base_currency="USD",
            quote_currency="EUR",
            source="primary",
            points=[
                RatePoint(timestamp=datetime(2025, 10, 1, tzinfo=UTC), rate=Decimal("0.9")),
                RatePoint(timestamp=datetime(2025, 10, 2, tzinfo=UTC), rate=Decimal("0.91")),
            ],
        )
    }


def test_run_backfill_persists_history(client, monkeypatch, history_series):
    app = client.application
    provider = DummyProvider(history_series)
    dummy_orchestrator = DummyOrchestrator(provider)

    original_orchestrator = app.extensions.get("fx_orchestrator")
    app.extensions["fx_orchestrator"] = dummy_orchestrator

    original_codes = registry.codes
    registry.codes = {"USD", "EUR"}

    persisted: list = []

    def _capture_snapshot(snapshot):
        persisted.append(snapshot)

    monkeypatch.setattr("app.services.backfill.persist_snapshot", _capture_snapshot)

    try:
        with app.app_context():
            run_backfill(days=2, base_currency="usd")
    finally:
        registry.codes = original_codes
        if original_orchestrator is not None:
            app.extensions["fx_orchestrator"] = original_orchestrator

    assert provider.calls == [("USD", "EUR", 2)]
    assert len(persisted) == 2
    assert persisted[0].rates == {"EUR": Decimal("0.9")}
