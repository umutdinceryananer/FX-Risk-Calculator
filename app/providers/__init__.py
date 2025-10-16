"""Provider interfaces and data structures for FX rate sources."""

from .base import BaseRateProvider, ProviderError
from .exchangerate_client import (
    ExchangeRateHostClient,
    ExchangeRateHostClientConfig,
    ExchangeRateHostError,
)
from .frankfurter_client import (
    FrankfurterAPIError,
    FrankfurterClient,
    FrankfurterClientConfig,
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
    "FrankfurterClient",
    "FrankfurterClientConfig",
    "FrankfurterAPIError",
    "ExchangeRateHostProvider",
]
