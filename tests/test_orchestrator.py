from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.providers.base import BaseRateProvider, ProviderError
from app.providers.schemas import RateSnapshot
from app.services import orchestrator as orchestrator_module
from app.services.orchestrator import Orchestrator


class FakeProvider(BaseRateProvider):
    def __init__(self, responses, name: str = "fake"):
        self.responses = responses
        self.name = name

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
    primary = FakeProvider([make_snapshot("primary", "USD")], name="primary")
    orchestrator = Orchestrator(primary=primary)

    snapshot = orchestrator.refresh_latest("USD")

    assert snapshot.source == "primary"
    record = orchestrator.get_snapshot_info()
    assert record and not record.stale


def test_orchestrator_fallback_used_when_primary_fails():
    primary = FakeProvider([ProviderError("primary down")], name="primary")
    fallback_snapshot = make_snapshot("fallback", "USD")
    fallback = FakeProvider([fallback_snapshot], name="fallback")

    orchestrator = Orchestrator(primary=primary, fallback=fallback)

    snapshot = orchestrator.refresh_latest("USD")

    assert snapshot is fallback_snapshot
    record = orchestrator.get_snapshot_info()
    assert record and not record.stale


def test_orchestrator_returns_stale_snapshot_when_all_fail(tmp_path):
    first_snapshot = make_snapshot("primary", "USD")
    primary = FakeProvider([first_snapshot, ProviderError("primary down")], name="primary")
    fallback = FakeProvider([ProviderError("fallback down")], name="fallback")

    orchestrator = Orchestrator(primary=primary, fallback=fallback)

    orchestrator.refresh_latest("USD")
    result = orchestrator.refresh_latest("USD")

    assert result is first_snapshot
    record = orchestrator.get_snapshot_info()
    assert record
    assert record.stale


def test_orchestrator_logs_provider_success():
    primary = FakeProvider([make_snapshot("primary", "USD")], name="primary")
    orchestrator = Orchestrator(primary=primary)

    with patch.object(orchestrator_module.logger, "info") as mock_info:
        orchestrator.refresh_latest("USD")

    mock_info.assert_called()
    extra = mock_info.call_args.kwargs.get("extra")
    assert extra["event"] == "provider.fetch"
    assert extra["provider"] == "primary"
    assert extra["status"] == "success"
    assert extra["source"] == "primary"
    assert extra["stale"] is False
    assert extra["duration_ms"] is not None and extra["duration_ms"] >= 0


def test_orchestrator_logs_stale_return():
    first_snapshot = make_snapshot("primary", "USD")
    primary = FakeProvider([first_snapshot, ProviderError("primary down")], name="primary")
    fallback = FakeProvider([ProviderError("fallback down")], name="fallback")
    orchestrator = Orchestrator(primary=primary, fallback=fallback)

    orchestrator.refresh_latest("USD")

    with patch.object(orchestrator_module.logger, "warning") as mock_warning, patch.object(
        orchestrator_module.logger, "error"
    ) as mock_error:
        orchestrator.refresh_latest("USD")

    mock_error.assert_called()
    error_extra = mock_error.call_args.kwargs.get("extra")
    assert error_extra["event"] == "provider.fetch"
    assert error_extra["provider"] == "fallback"
    assert error_extra["status"] == "error"
    assert error_extra["stale"] is False

    warning_extras = [call.kwargs.get("extra") for call in mock_warning.call_args_list]
    stale_extras = [extra for extra in warning_extras if extra and extra.get("event") == "provider.stale"]
    assert stale_extras
    stale_extra = stale_extras[-1]
    assert stale_extra["provider"] == "primary"
    assert stale_extra["stale"] is True
