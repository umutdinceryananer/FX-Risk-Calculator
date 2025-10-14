"""Provider interfaces and data structures for FX rate sources."""

from .base import BaseRateProvider, ProviderError
from .schemas import RateHistorySeries, RatePoint, RateSnapshot
from .exchangerate_client import (
    ExchangeRateHostClient,
    ExchangeRateHostClientConfig,
    ExchangeRateHostError,
)

__all__ = [
    "BaseRateProvider",
    "ProviderError",
    "RateHistorySeries",
    "RatePoint",
    "RateSnapshot",
    "ExchangeRateHostClient",
    "ExchangeRateHostClientConfig",
    "ExchangeRateHostError",
]
