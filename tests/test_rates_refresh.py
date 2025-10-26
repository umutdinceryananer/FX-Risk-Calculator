from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.providers.base import ProviderError
from app.providers.schemas import RateSnapshot


class DummyOrchestrator:
    def __init__(self, snapshot: RateSnapshot | None = None, error: ProviderError | None = None):
        self.snapshot = snapshot
        self.error = error
        self.calls = 0

    def refresh_latest(self, base: str) -> RateSnapshot:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.snapshot is not None
        return self.snapshot


@pytest.fixture
def snapshot():
    return RateSnapshot(
        base_currency="USD",
        source="mock",
        timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
        rates={"EUR": Decimal("0.9"), "GBP": Decimal("0.8")},
    )


def _increment_persist_counter(counter: dict[str, int]) -> Callable[[RateSnapshot], None]:
    def _increment(_snapshot: RateSnapshot) -> None:
        counter["persist"] += 1

    return _increment


def _raise_should_not_persist(_snapshot: RateSnapshot) -> None:
    raise RuntimeError("should not persist")


def test_manual_refresh_returns_accepted(client, snapshot, monkeypatch):
    calls = {"persist": 0}
    monkeypatch.setattr(
        "app.rates.routes.persist_snapshot",
        _increment_persist_counter(calls),
    )

    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(snapshot=snapshot)
    app.extensions["fx_refresh_state"] = {}

    response = client.post("/rates/refresh")

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["source"] == "mock"
    assert payload["base_currency"] == "USD"
    assert payload["as_of"] == snapshot.timestamp.isoformat()
    assert calls["persist"] == 1

    state = app.extensions["fx_refresh_state"]
    assert state["last_success"] is not None
    assert state["last_failure"] is None
    assert state["throttle_until"] > state["last_success"]


def test_manual_refresh_throttles_requests(client, snapshot, monkeypatch):
    monkeypatch.setattr(
        "app.rates.routes.persist_snapshot",
        _raise_should_not_persist,
    )

    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(snapshot=snapshot)
    app.extensions["fx_refresh_state"] = {"last_success": datetime.now(UTC)}

    response = client.post("/rates/refresh")

    assert response.status_code == 429
    payload = response.get_json()
    assert "retry_after" in payload
    assert app.extensions["fx_refresh_state"]["throttle_until"] is not None


def test_manual_refresh_reports_provider_error(client, monkeypatch):
    monkeypatch.setattr("app.rates.routes.persist_snapshot", lambda _snapshot: None)

    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(error=ProviderError("primary down"))
    app.extensions["fx_refresh_state"] = {}

    response = client.post("/rates/refresh")

    assert response.status_code == 503
    payload = response.get_json()
    assert "primary down" in payload["message"]


def test_manual_refresh_respects_zero_throttle(client, snapshot, monkeypatch):
    calls = {"persist": 0}
    monkeypatch.setattr(
        "app.rates.routes.persist_snapshot",
        _increment_persist_counter(calls),
    )

    app = client.application
    app.config["REFRESH_THROTTLE_SECONDS"] = 0
    app.extensions["fx_orchestrator"] = DummyOrchestrator(snapshot=snapshot)
    app.extensions["fx_refresh_state"] = {}

    first = client.post("/rates/refresh")
    second = client.post("/rates/refresh")

    assert first.status_code == 202
    assert second.status_code == 202
    assert calls["persist"] == 2

    state = app.extensions["fx_refresh_state"]
    assert state["last_success"] is not None
    assert state.get("throttle_until") is None
