"""Smoke tests for health endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from app.providers.schemas import RateSnapshot
from app.services.orchestrator import SnapshotRecord


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"


def test_health_rates_endpoint_returns_uninitialized_when_no_snapshot(client):
    app = client.application
    orchestrator = app.extensions.get("fx_orchestrator")
    assert orchestrator is not None
    orchestrator._last_snapshot = None  # type: ignore[attr-defined]

    response = client.get("/health/rates")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "uninitialized"
    assert payload["source"] is None
    assert payload["last_updated"] is None
    assert payload["stale"] is None


def test_health_rates_endpoint_returns_snapshot_metadata(client):
    app = client.application
    orchestrator = app.extensions.get("fx_orchestrator")
    assert orchestrator is not None
    snapshot = RateSnapshot(
        base_currency="USD",
        source="mock",
        timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
        rates={"EUR": 0.9},
    )
    orchestrator._last_snapshot = SnapshotRecord(snapshot=snapshot, stale=False)  # type: ignore[attr-defined]

    response = client.get("/health/rates")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "status": "ok",
        "source": "mock",
        "base_currency": "USD",
        "last_updated": snapshot.timestamp.isoformat(),
        "stale": False,
    }

def test_health_rates_marks_stale_when_cached_snapshot_used(client):
    app = client.application
    orchestrator = app.extensions.get("fx_orchestrator")
    assert orchestrator is not None
    snapshot = RateSnapshot(
        base_currency="USD",
        source="fallback",
        timestamp=datetime(2025, 10, 16, 13, 0, tzinfo=UTC),
        rates={"EUR": 0.9},
    )
    orchestrator._last_snapshot = SnapshotRecord(snapshot=snapshot, stale=True)  # type: ignore[attr-defined]

    response = client.get("/health/rates")
    payload = response.get_json()
    assert payload["stale"] is True
    assert payload["source"] == "fallback"
    assert payload["last_updated"] == snapshot.timestamp.isoformat()
