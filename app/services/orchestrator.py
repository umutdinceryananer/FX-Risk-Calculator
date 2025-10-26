"""Orchestrator service coordinating primary and fallback FX providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from app.logging import provider_log_extra
from app.providers import BaseRateProvider, ProviderError, RateSnapshot
from app.providers.registry import get_provider

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
        fallback: BaseRateProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._last_snapshot: SnapshotRecord | None = None

    def refresh_latest(self, base: str) -> RateSnapshot:
        """Refresh latest rates using primary, fallback, or cached snapshot."""

        primary_name = self._provider_name(self._primary)
        start = perf_counter()
        try:
            snapshot = self._primary.get_latest(base)
            duration = (perf_counter() - start) * 1000
            logger.info(
                "Provider fetch succeeded",
                extra=provider_log_extra(
                    provider=primary_name,
                    base=base,
                    event="provider.fetch",
                    status="success",
                    duration_ms=duration,
                    stale=False,
                ),
            )
            self._store_snapshot(snapshot, stale=False)
            return snapshot
        except ProviderError as primary_err:
            duration = (perf_counter() - start) * 1000
            logger.warning(
                "Primary provider failure: %s",
                primary_err,
                extra=provider_log_extra(
                    provider=primary_name,
                    base=base,
                    event="provider.fetch",
                    status="error",
                    duration_ms=duration,
                    stale=False,
                    error=str(primary_err),
                ),
            )

        if self._fallback is not None:
            fallback_name = self._provider_name(self._fallback)
            start = perf_counter()
            try:
                snapshot = self._fallback.get_latest(base)
                duration = (perf_counter() - start) * 1000
                logger.info(
                    "Fallback provider fetch succeeded",
                    extra=provider_log_extra(
                        provider=fallback_name,
                        base=base,
                        event="provider.fetch",
                        status="success",
                        duration_ms=duration,
                        stale=False,
                    ),
                )
                self._store_snapshot(snapshot, stale=False)
                return snapshot
            except ProviderError as fallback_err:
                duration = (perf_counter() - start) * 1000
                logger.error(
                    "Fallback provider failure: %s",
                    fallback_err,
                    extra=provider_log_extra(
                        provider=fallback_name,
                        base=base,
                        event="provider.fetch",
                        status="error",
                        duration_ms=duration,
                        stale=False,
                        error=str(fallback_err),
                    ),
                )

        if self._last_snapshot is None:
            raise ProviderError(
                "Unable to refresh rates from any provider and no cached snapshot available"
            )

        cached_record = self._last_snapshot
        cached = cached_record.snapshot
        logger.warning(
            "Returning stale snapshot from %s captured at %s",
            cached.source,
            cached.timestamp,
            extra=provider_log_extra(
                provider=cached.source,
                base=base,
                event="provider.stale",
                status="stale",
                duration_ms=None,
                stale=True,
            ),
        )
        self._last_snapshot = SnapshotRecord(snapshot=cached, stale=True)
        return cached

    def get_snapshot_info(self) -> SnapshotRecord | None:
        return self._last_snapshot

    def _store_snapshot(self, snapshot: RateSnapshot, stale: bool) -> None:
        self._last_snapshot = SnapshotRecord(snapshot=snapshot, stale=stale)

    @staticmethod
    def _provider_name(provider: BaseRateProvider | None) -> str:
        if provider is None:
            return "unknown"
        return getattr(provider, "name", provider.__class__.__name__)


def create_orchestrator(
    primary: BaseRateProvider, fallback: BaseRateProvider | None = None
) -> Orchestrator:
    return Orchestrator(primary=primary, fallback=fallback)


def init_orchestrator(app) -> Orchestrator:
    """Create and store an orchestrator on the Flask app context."""

    primary = app.extensions.get("rate_provider")
    if primary is None:
        primary = get_provider(app.config.get("FX_RATE_PROVIDER"))

    fallback_provider = None
    fallback_name = app.config.get("FX_FALLBACK_PROVIDER")
    if fallback_name:
        try:
            with app.app_context():
                fallback_provider = get_provider(fallback_name)
        except ProviderError as exc:
            logger.warning("Configured fallback provider '%s' unavailable: %s", fallback_name, exc)

    orchestrator = Orchestrator(primary=primary, fallback=fallback_provider)
    app.extensions["fx_orchestrator"] = orchestrator
    return orchestrator
