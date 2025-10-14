"""Abstract interface for FX rate providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import RateHistorySeries, RateSnapshot


class ProviderError(Exception):
    """Raised when an upstream provider cannot fulfill a request."""


class BaseRateProvider(ABC):
    """Defines the interface all FX rate providers must implement."""

    name: str

    @abstractmethod
    def get_latest(self, base: str) -> RateSnapshot:
        """Retrieve the most recent rates for the given base currency."""

    @abstractmethod
    def get_history(self, base: str, symbol: str, days: int) -> RateHistorySeries:
        """Retrieve a history timeseries for the given pair spanning `days`."""
