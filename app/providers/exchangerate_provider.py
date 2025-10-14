"""ExchangeRate.host provider implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Mapping

from app.providers.base import BaseRateProvider, ProviderError
from app.providers.schemas import RateHistorySeries, RatePoint, RateSnapshot

from ..services.currency_registry import registry
from .exchangerate_client import ExchangeRateHostClient, ExchangeRateHostClientConfig


class ExchangeRateHostProvider(BaseRateProvider):
    """Provider that fetches data from ExchangeRate.host."""

    name = "exchangerate_host"
    config_prefix = "RATES_API_"

    def __init__(self, client: ExchangeRateHostClient) -> None:
        self._client = client

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "ExchangeRateHostProvider":
        client_config = cls._build_client_config(config)
        return cls(ExchangeRateHostClient(client_config))

    def get_latest(self, base: str) -> RateSnapshot:
        base_currency = self._normalize_base(base)
        params = {
            "base": base_currency,
            "symbols": self._allowed_symbols(exclude=base_currency),
        }
        payload = self._client.get("/latest", params=params)
        try:
            rates = payload["rates"]
            timestamp = self._parse_date(payload["date"])
        except KeyError as exc:  # pragma: no cover - defensive
            raise ProviderError("Unexpected response payload from ExchangeRate.host") from exc

        return RateSnapshot(
            base_currency=base_currency,
            source=self.name,
            timestamp=timestamp,
            rates=rates,
        )

    def get_history(self, base: str, symbol: str, days: int) -> RateHistorySeries:
        if days <= 0:
            raise ValueError("days must be a positive integer")

        base_currency = self._normalize_base(base)
        quote_currency = self._normalize_symbol(symbol)

        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days - 1)

        params = {
            "base": base_currency,
            "symbols": quote_currency,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        payload = self._client.get("/timeseries", params=params)
        rates_by_date = payload.get("rates") or {}

        points: list[RatePoint] = []
        for date_str, rate_map in rates_by_date.items():
            timestamp = self._parse_date(date_str)
            rate_value = rate_map.get(quote_currency)
            if rate_value is None:
                continue
            points.append(RatePoint(timestamp=timestamp, rate=rate_value))

        points.sort(key=lambda point: point.timestamp)

        return RateHistorySeries(
            base_currency=base_currency,
            quote_currency=quote_currency,
            source=self.name,
            points=points,
        )

    @staticmethod
    def _parse_date(value: str) -> datetime:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)

    def _allowed_symbols(self, exclude: str | None = None) -> str:
        codes: Iterable[str] = registry.codes
        filtered = [code for code in codes if code != exclude]
        return ",".join(sorted(filtered))

    def _normalize_base(self, value: str) -> str:
        normalized = self._normalize_symbol(value)
        if not registry.is_allowed(normalized):
            raise ProviderError(f"Base currency '{normalized}' is not in the allowed currency registry.")
        return normalized

    @staticmethod
    def _normalize_symbol(value: str) -> str:
        if not value or not str(value).strip():
            raise ProviderError("Currency symbol cannot be empty.")
        return str(value).strip().upper()

    @classmethod
    def _build_client_config(cls, config: Mapping[str, Any]) -> ExchangeRateHostClientConfig:
        base_url = config.get("RATES_API_BASE_URL")
        timeout = float(config.get("REQUEST_TIMEOUT_SECONDS", 5))
        max_retries = int(config.get("RATES_API_MAX_RETRIES", 3))
        backoff = float(config.get("RATES_API_BACKOFF_SECONDS", 0.5))
        return ExchangeRateHostClientConfig(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff,
        )

