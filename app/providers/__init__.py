"""Provider interfaces and data structures for FX rate sources."""

from .base import BaseRateProvider, ProviderError
from .schemas import RateHistorySeries, RatePoint, RateSnapshot

__all__ = [
    "BaseRateProvider",
    "ProviderError",
    "RateHistorySeries",
    "RatePoint",
    "RateSnapshot",
]
