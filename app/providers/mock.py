"""Mock provider implementation for testing and local development."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.utils.datetime import utc_now

from .base import BaseRateProvider
from .schemas import RateHistorySeries, RatePoint, RateSnapshot


class MockRateProvider(BaseRateProvider):
    """Deterministic provider returning synthetic FX data."""

    name = "mock"

    def get_latest(self, base: str) -> RateSnapshot:
        base_currency = str(base).upper()
        timestamp = utc_now()
        rates: dict[str, Decimal] = {
            "EUR": Decimal("0.90"),
            "GBP": Decimal("0.78"),
            "JPY": Decimal("150.12"),
        }
        return RateSnapshot(
            base_currency=base_currency,
            source=self.name,
            timestamp=timestamp,
            rates=rates,
        )

    def get_history(self, base: str, symbol: str, days: int) -> RateHistorySeries:
        if days <= 0:
            raise ValueError("days must be a positive integer")

        base_currency = str(base).upper()
        quote_currency = str(symbol).upper()
        now = utc_now()
        points = [
            RatePoint(
                timestamp=now - timedelta(days=offset),
                rate=Decimal("1.00") + Decimal(offset) * Decimal("0.01"),
            )
            for offset in range(days)
        ]

        points.sort(key=lambda p: p.timestamp)
        return RateHistorySeries(
            base_currency=base_currency,
            quote_currency=quote_currency,
            source=self.name,
            points=points,
        )
