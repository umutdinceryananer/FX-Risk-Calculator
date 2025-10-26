"""Services to backfill historical FX rates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from app.providers import BaseRateProvider, ProviderError
from app.providers.schemas import RateHistorySeries, RatePoint, RateSnapshot
from app.services.currency_registry import registry
from app.services.orchestrator import Orchestrator
from app.services.rate_store import persist_snapshot

logger = logging.getLogger(__name__)


def run_backfill(days: int, base_currency: str) -> None:
    """Backfill historical FX rates for the given number of days."""

    from flask import current_app

    app = current_app
    orchestrator = cast(Orchestrator | None, app.extensions.get("fx_orchestrator"))
    if orchestrator is None:
        raise RuntimeError("Orchestrator is not initialised")

    providers = _history_capable_providers(orchestrator)
    if not providers:
        raise RuntimeError("No configured providers support history backfill")

    base_upper = base_currency.upper()

    codes = sorted({code.upper() for code in (registry.codes or set())} - {base_upper})
    logger.info("Backfilling %s-days history for %s against %s symbols", days, base_upper, codes)

    for symbol in codes:
        series = None
        for provider in providers:
            provider_name = getattr(provider, "name", provider.__class__.__name__)
            try:
                series = provider.get_history(base_upper, symbol, days)
                logger.info(
                    "Fetched %s-day history for %s/%s via provider '%s'",
                    days,
                    base_upper,
                    symbol,
                    provider_name,
                )
                break
            except ProviderError as exc:
                logger.warning(
                    "History fetch for %s/%s failed via provider '%s': %s",
                    base_upper,
                    symbol,
                    provider_name,
                    exc,
                )

        if series is None:
            logger.error(
                "Falling back to synthetic history for %s/%s after all providers failed.",
                base_upper,
                symbol,
            )
            series = _generate_synthetic_series(base_upper, symbol, days)

        _persist_series(series)


def _history_capable_providers(orchestrator: Orchestrator) -> list[BaseRateProvider]:
    providers: list[BaseRateProvider] = []
    primary = getattr(orchestrator, "_primary", None)
    if primary is not None and hasattr(primary, "get_history"):
        providers.append(primary)

    fallback = getattr(orchestrator, "_fallback", None)
    if fallback is not None and hasattr(fallback, "get_history"):
        providers.append(fallback)

    return providers


def _persist_series(series: RateHistorySeries) -> None:
    for point in series.points:
        snapshot = RateSnapshot(
            base_currency=series.base_currency,
            source=series.source,
            timestamp=point.timestamp,
            rates={series.quote_currency: point.rate},
        )
        persist_snapshot(snapshot)


def _generate_synthetic_series(base_currency: str, symbol: str, days: int) -> RateHistorySeries:
    start = datetime.now(UTC) - timedelta(days=days - 1)
    points: list[RatePoint] = []
    base_currency = base_currency.upper()
    symbol = symbol.upper()

    for offset in range(days):
        timestamp = start + timedelta(days=offset)
        # Deterministic pseudo rate oscillating gently around 1.0
        rate = Decimal("1") + Decimal("0.01") * Decimal((offset % 7) - 3) / Decimal("10")
        if symbol == base_currency:
            rate = Decimal("1")
        points.append(
            RatePoint(
                timestamp=timestamp,
                rate=rate,
            )
        )

    return RateHistorySeries(
        base_currency=base_currency,
        quote_currency=symbol,
        source="synthetic",
        points=points,
    )
