"""Services to backfill historical FX rates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Iterable

from app.providers import ProviderError
from app.services.orchestrator import Orchestrator
from app.services.rate_store import persist_snapshot

logger = logging.getLogger(__name__)


def run_backfill(days: int, base_currency: str) -> None:
    """Backfill historical FX rates for the given number of days."""

    from flask import current_app

    app = current_app
    orchestrator: Orchestrator | None = app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
    if orchestrator is None:
        raise RuntimeError("Orchestrator is not initialised")

    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days - 1)

    logger.info("Backfilling rates from %s to %s", start_date, end_date)

    for single_date in _daterange(start_date, end_date):
        try:
            snapshot = orchestrator.refresh_latest(base_currency)
        except ProviderError as exc:
            logger.error("Backfill failed for %s: %s", single_date, exc)
            continue

        persist_snapshot(snapshot)
        logger.info("Stored snapshot for %s from %s", snapshot.timestamp.isoformat(), snapshot.source)


def _daterange(start_date, end_date) -> Iterable[datetime]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
