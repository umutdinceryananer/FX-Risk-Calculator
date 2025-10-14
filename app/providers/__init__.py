"""Provider interfaces and data structures for FX rate sources."""

from .base import BaseRateProvider, ProviderError
from .exchangerate_client import (
    ExchangeRateHostClient,
    ExchangeRateHostClientConfig,
    ExchangeRateHostError,
)
from .exchangerate_provider import ExchangeRateHostProvider
from .schemas import RateHistorySeries, RatePoint, RateSnapshot

__all__ = [
    "BaseRateProvider",
    "ProviderError",
    "RateHistorySeries",
    "RatePoint",
    "RateSnapshot",
    "ExchangeRateHostClient",
    "ExchangeRateHostClientConfig",
    "ExchangeRateHostError",
    "ExchangeRateHostProvider",
]
