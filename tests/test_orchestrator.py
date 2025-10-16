from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.providers.base import BaseRateProvider, ProviderError
from app.providers.schemas import RateSnapshot
from app.services.orchestrator import Orchestrator


class FakeProvider(BaseRateProvider):
    name = "fake"

    def __init__(self, responses):
        self.responses = responses

    def get_latest(self, base: str) -> RateSnapshot:
        if not self.responses:
            raise ProviderError("No response available")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def get_history(self, base: str, symbol: str, days: int):
        raise NotImplementedError


def make_snapshot(source: str, base: str) -> RateSnapshot:
    return RateSnapshot(
        base_currency=base,
        source=source,
        timestamp=datetime(2025, 10, 16, 12, 0, tzinfo=UTC),
        rates={"EUR": 0.9, "GBP": 0.8},
    )


def test_orchestrator_primary_success():
    primary = FakeProvider([make_snapshot("primary", "USD")])
    orchestrator = Orchestrator(primary=primary)

    snapshot = orchestrator.refresh_latest("USD")

    assert snapshot.source == "primary"
    record = orchestrator.get_snapshot_info()
    assert record and not record.stale


def test_orchestrator_fallback_used_when_primary_fails():
    primary = FakeProvider([ProviderError("primary down")])
    fallback_snapshot = make_snapshot("fallback", "USD")
    fallback = FakeProvider([fallback_snapshot])

    orchestrator = Orchestrator(primary=primary, fallback=fallback)

    snapshot = orchestrator.refresh_latest("USD")

    assert snapshot is fallback_snapshot
    record = orchestrator.get_snapshot_info()
    assert record and not record.stale


def test_orchestrator_returns_stale_snapshot_when_all_fail(tmp_path):
    first_snapshot = make_snapshot("primary", "USD")
    primary = FakeProvider([first_snapshot, ProviderError("primary down")])
    fallback = FakeProvider([ProviderError("fallback down")])

    orchestrator = Orchestrator(primary=primary, fallback=fallback)

    orchestrator.refresh_latest("USD")
    result = orchestrator.refresh_latest("USD")

    assert result is first_snapshot
    record = orchestrator.get_snapshot_info()
    assert record
    assert record.stale
