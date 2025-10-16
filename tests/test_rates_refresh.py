from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
        rates={"EUR": 0.9, "GBP": 0.8},
    )


def test_manual_refresh_returns_accepted(client, snapshot):
    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(snapshot=snapshot)
    app.extensions["fx_refresh_state"] = {}

    response = client.post("/rates/refresh")

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["source"] == "mock"
    assert payload["base_currency"] == "USD"
    assert payload["as_of"] == snapshot.timestamp.isoformat()

    state = app.extensions["fx_refresh_state"]
    assert state["last_success"] is not None
    assert state["last_failure"] is None


def test_manual_refresh_throttles_requests(client, snapshot):
    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(snapshot=snapshot)
    app.extensions["fx_refresh_state"] = {"last_success": datetime.now(UTC)}

    response = client.post("/rates/refresh")

    assert response.status_code == 429
    payload = response.get_json()
    assert "retry_after" in payload


def test_manual_refresh_reports_provider_error(client):
    app = client.application
    app.extensions["fx_orchestrator"] = DummyOrchestrator(error=ProviderError("primary down"))
    app.extensions["fx_refresh_state"] = {}

    response = client.post("/rates/refresh")

    assert response.status_code == 503
    payload = response.get_json()
    assert "primary down" in payload["message"]
