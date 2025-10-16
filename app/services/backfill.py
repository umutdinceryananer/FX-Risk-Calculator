"""Services to backfill historical FX rates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Iterable, Sequence

from app.providers import BaseRateProvider, ProviderError
from app.providers.schemas import RateHistorySeries, RateSnapshot
from app.services.orchestrator import Orchestrator
from app.services.rate_store import persist_snapshot
from app.services.currency_registry import registry

logger = logging.getLogger(__name__)


def run_backfill(days: int, base_currency: str) -> None:
    """Backfill historical FX rates for the given number of days."""

    from flask import current_app

    app = current_app
    orchestrator: Orchestrator | None = app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
    if orchestrator is None:
        raise RuntimeError("Orchestrator is not initialised")

    provider = _primary_provider(orchestrator)
    base_upper = base_currency.upper()

    codes = sorted({code.upper() for code in (registry.codes or set())} - {base_upper})
    logger.info("Backfilling %s-days history for %s against %s symbols", days, base_upper, codes)

    for symbol in codes:
        try:
            series = provider.get_history(base_upper, symbol, days)
        except ProviderError as exc:
            logger.warning("History fetch for %s failed: %s", symbol, exc)
            continue

        _persist_series(series)


def _primary_provider(orchestrator: Orchestrator) -> BaseRateProvider:
    primary = getattr(orchestrator, "_primary", None)
    if primary is None or not hasattr(primary, "get_history"):
        raise RuntimeError("Primary provider does not support history backfill")
    return primary


def _persist_series(series: RateHistorySeries) -> None:
    for point in series.points:
        snapshot = RateSnapshot(
            base_currency=series.base_currency,
            source=series.source,
            timestamp=point.timestamp,
            rates={series.quote_currency: point.rate},
        )
        persist_snapshot(snapshot)
