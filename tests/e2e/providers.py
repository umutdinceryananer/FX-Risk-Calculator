"""Helpers and stub providers for end-to-end tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.providers import (
    BaseRateProvider,
    ProviderError,
    RateHistorySeries,
    RatePoint,
    RateSnapshot,
)

LatestQueueItem = RateSnapshot | Exception


@dataclass(slots=True)
class ProviderCall:
    """Record of a provider interaction captured for assertions."""

    method: str
    base: str
    symbol: str | None = None
    days: int | None = None


class SequencedProvider(BaseRateProvider):
    """Provider that yields predefined responses in sequence."""

    def __init__(
        self,
        name: str,
        latest: Iterable[LatestQueueItem] | None = None,
        history: Mapping[tuple[str, str], RateHistorySeries] | None = None,
    ) -> None:
        self.name = name
        self._latest: deque[LatestQueueItem] = deque(latest or [])
        self._history: MutableMapping[tuple[str, str], RateHistorySeries] = dict(history or {})
        self.calls: list[ProviderCall] = []

    def get_latest(self, base: str) -> RateSnapshot:
        normalized_base = base.strip().upper()
        self.calls.append(ProviderCall(method="get_latest", base=normalized_base))
        if not self._latest:
            raise ProviderError(f"{self.name} exhausted: no snapshot available")
        item = self._latest.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    def get_history(self, base: str, symbol: str, days: int) -> RateHistorySeries:
        normalized_base = base.strip().upper()
        normalized_symbol = symbol.strip().upper()
        self.calls.append(
            ProviderCall(
                method="get_history",
                base=normalized_base,
                symbol=normalized_symbol,
                days=days,
            )
        )
        key = (normalized_base, normalized_symbol)
        try:
            return self._history[key]
        except KeyError as exc:
            raise ProviderError(
                f"{self.name} has no history for {normalized_base}/{normalized_symbol}"
            ) from exc

    def preload_latest(self, snapshots: Iterable[LatestQueueItem]) -> None:
        """Extend the queue of latest snapshots."""

        self._latest.extend(snapshots)

    def preload_history(
        self,
        base: str,
        symbol: str,
        series: RateHistorySeries,
    ) -> None:
        """Register a history series for later retrieval."""

        self._history[(base.strip().upper(), symbol.strip().upper())] = series


def build_snapshot(
    *,
    base_currency: str = "USD",
    source: str = "primary",
    rates: Mapping[str, Decimal | float | int] | None = None,
    as_of: datetime | None = None,
) -> RateSnapshot:
    """Convenience helper for constructing `RateSnapshot` instances."""

    snapshot_rates = rates or {"EUR": Decimal("0.9"), "GBP": Decimal("0.8")}
    timestamp = as_of or datetime.now(UTC)
    return RateSnapshot(
        base_currency=base_currency,
        source=source,
        timestamp=timestamp,
        rates={code: Decimal(str(value)) for code, value in snapshot_rates.items()},
    )


def build_history_series(
    *,
    base_currency: str = "USD",
    quote_currency: str = "EUR",
    source: str = "primary",
    points: Iterable[tuple[datetime, Decimal | float | int]] | None = None,
) -> RateHistorySeries:
    """Construct a `RateHistorySeries` with normalized timestamps and rates."""

    series_points = points or (
        (datetime(2025, 10, 1, tzinfo=UTC), Decimal("0.9")),
        (datetime(2025, 10, 2, tzinfo=UTC), Decimal("0.91")),
    )
    normalized = [
        RatePoint(timestamp=timestamp, rate=Decimal(str(value)))
        for timestamp, value in series_points
    ]
    return RateHistorySeries(
        base_currency=base_currency,
        quote_currency=quote_currency,
        source=source,
        points=normalized,
    )
