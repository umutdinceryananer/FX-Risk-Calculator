"""Fixtures powering end-to-end tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Optional

import pytest

from app.providers import RateHistorySeries, RateSnapshot
from app.services.orchestrator import Orchestrator

from .providers import LatestQueueItem, SequencedProvider


@pytest.fixture()
def orchestrator_stub(app):
    """Configure the application orchestrator with stub providers for E2E flows."""

    def _factory(
        *,
        primary_latest: Iterable[LatestQueueItem] = (),
        fallback_latest: Optional[Iterable[LatestQueueItem]] = None,
        primary_history: Mapping[tuple[str, str], RateHistorySeries] | None = None,
        fallback_history: Mapping[tuple[str, str], RateHistorySeries] | None = None,
        attach: bool = True,
    ) -> tuple[Orchestrator, SequencedProvider, SequencedProvider | None]:
        primary = SequencedProvider(
            name="primary",
            latest=primary_latest,
            history=primary_history,
        )
        fallback_provider: SequencedProvider | None = None
        if fallback_latest is not None:
            fallback_provider = SequencedProvider(
                name="fallback",
                latest=fallback_latest,
                history=fallback_history,
            )
        orchestrator = Orchestrator(primary=primary, fallback=fallback_provider)
        if attach:
            app.extensions["fx_orchestrator"] = orchestrator
        return orchestrator, primary, fallback_provider

    return _factory
