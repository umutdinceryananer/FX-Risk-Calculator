"""Dataclasses describing normalized FX provider payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Mapping

from app.utils.datetime import ensure_utc


def _normalize_code(code: str) -> str:
    normalized = code.strip().upper()
    if not normalized.isascii():
        raise ValueError(f"Currency code must be ASCII: {code!r}")
    return normalized


def _normalize_rates(rates: Mapping[str, Decimal | float | int]) -> Dict[str, Decimal]:
    normalized: Dict[str, Decimal] = {}
    for code, value in rates.items():
        normalized[_normalize_code(code)] = Decimal(str(value))
    return normalized


@dataclass(frozen=True)
class RateSnapshot:
    """Normalized payload representing the latest FX rates for a base currency."""

    base_currency: str
    source: str
    timestamp: datetime
    rates: Dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_currency", _normalize_code(self.base_currency))
        object.__setattr__(self, "rates", _normalize_rates(self.rates))
        normalized_timestamp = ensure_utc(self.timestamp)
        object.__setattr__(self, "timestamp", normalized_timestamp)
        if not self.source or not self.source.strip():
            raise ValueError("source must be provided for RateSnapshot")


@dataclass(frozen=True)
class RatePoint:
    """Single historical rate observation."""

    timestamp: datetime
    rate: Decimal

    def __post_init__(self) -> None:
        normalized_timestamp = ensure_utc(self.timestamp)
        object.__setattr__(self, "timestamp", normalized_timestamp)
        object.__setattr__(self, "rate", Decimal(str(self.rate)))


@dataclass(frozen=True)
class RateHistorySeries:
    """Normalized timeseries for a currency pair."""

    base_currency: str
    quote_currency: str
    source: str
    points: List[RatePoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_currency", _normalize_code(self.base_currency))
        object.__setattr__(self, "quote_currency", _normalize_code(self.quote_currency))
        if not self.source or not self.source.strip():
            raise ValueError("source must be provided for RateHistorySeries")
        object.__setattr__(self, "points", list(self._normalize_points(self.points)))

    @staticmethod
    def _normalize_points(points: Iterable[RatePoint]) -> Iterable[RatePoint]:
        for point in points:
            if not isinstance(point, RatePoint):
                raise TypeError("points must contain RatePoint instances")
            yield point
