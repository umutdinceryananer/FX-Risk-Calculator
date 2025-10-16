"""Orchestrator service coordinating primary and fallback FX providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from app.providers import BaseRateProvider, ProviderError, RateSnapshot

logger = logging.getLogger(__name__)


@dataclass
class SnapshotRecord:
    snapshot: RateSnapshot
    stale: bool


class Orchestrator:
    """Coordinate between primary and fallback providers with stale cache."""

    def __init__(
        self,
        primary: BaseRateProvider,
        fallback: Optional[BaseRateProvider] = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._last_snapshot: Optional[SnapshotRecord] = None

    def refresh_latest(self, base: str) -> RateSnapshot:
        """Refresh latest rates using primary, fallback, or cached snapshot."""

        try:
            snapshot = self._primary.get_latest(base)
            self._store_snapshot(snapshot, stale=False)
            return snapshot
        except ProviderError as primary_err:
            logger.warning("Primary provider failure: %s", primary_err)

        if self._fallback is not None:
            try:
                snapshot = self._fallback.get_latest(base)
                self._store_snapshot(snapshot, stale=False)
                return snapshot
            except ProviderError as fallback_err:
                logger.error("Fallback provider failure: %s", fallback_err)

        if self._last_snapshot is None:
            raise ProviderError("Unable to refresh rates from any provider and no cached snapshot available")

        cached_record = self._last_snapshot
        cached = cached_record.snapshot
        logger.warning("Returning stale snapshot from %s captured at %s", cached.source, cached.timestamp)
        self._last_snapshot = SnapshotRecord(snapshot=cached, stale=True)
        return cached

    def get_snapshot_info(self) -> Optional[SnapshotRecord]:
        return self._last_snapshot

    def _store_snapshot(self, snapshot: RateSnapshot, stale: bool) -> None:
        self._last_snapshot = SnapshotRecord(snapshot=snapshot, stale=stale)


def create_orchestrator(primary: BaseRateProvider, fallback: Optional[BaseRateProvider] = None) -> Orchestrator:
    return Orchestrator(primary=primary, fallback=fallback)
