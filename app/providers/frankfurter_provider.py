"""ECB (Frankfurter) provider implementation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.providers.base import BaseRateProvider, ProviderError
from app.providers.schemas import RateHistorySeries, RatePoint, RateSnapshot
from app.services.fx_conversion import RebaseError, rebase_rates

from ..services.currency_registry import registry
from .frankfurter_client import FrankfurterAPIError, FrankfurterClient, FrankfurterClientConfig


class FrankfurterProvider(BaseRateProvider):
    """Provider that fetches ECB rates via the Frankfurter API."""

    name = "ecb"

    def __init__(self, client: FrankfurterClient, canonical_base: str = "USD") -> None:
        self._client = client
        self._canonical_base = canonical_base.upper()

    @classmethod
    def from_config(cls, config: Mapping[str, str | int | float]) -> FrankfurterProvider:
        client_config = FrankfurterClientConfig(
            base_url=str(config.get("FRANKFURTER_API_BASE_URL")),
            timeout=float(config.get("REQUEST_TIMEOUT_SECONDS", 5)),
            max_retries=int(config.get("FRANKFURTER_API_MAX_RETRIES", 3)),
            backoff_seconds=float(config.get("FRANKFURTER_API_BACKOFF_SECONDS", 0.5)),
        )
        canonical_base = str(config.get("FX_CANONICAL_BASE", "USD"))
        return cls(FrankfurterClient(client_config), canonical_base=canonical_base)

    def get_latest(self, base: str) -> RateSnapshot:
        target_base = base.strip().upper()
        self._ensure_supported(target_base)

        symbols = self._allowed_symbols(exclude=self._canonical_base)
        timestamp, rates = self._fetch_latest(symbols)

        snapshot_rates = self._transform_rates(rates, target_base)

        return RateSnapshot(
            base_currency=target_base,
            source=self.name,
            timestamp=timestamp,
            rates=snapshot_rates,
        )

    def get_history(self, base: str, symbol: str, days: int) -> RateHistorySeries:
        if days <= 0:
            raise ValueError("days must be a positive integer")

        base_currency = base.strip().upper()
        quote_currency = symbol.strip().upper()
        self._ensure_supported(base_currency)
        self._ensure_supported(quote_currency)

        end_date = self._current_date()
        start_date = end_date - timedelta(days=days - 1)

        params = {
            "from": self._canonical_base,
            "to": ",".join(sorted({base_currency, quote_currency} - {self._canonical_base})),
        }
        path = f"{start_date.isoformat()}..{end_date.isoformat()}"
        try:
            payload = self._client.get(path, params=params)
        except FrankfurterAPIError as exc:
            raise ProviderError(str(exc)) from exc

        rates_by_date = payload.get("rates", {})

        points: list[RatePoint] = []
        for date_str, rate_map in rates_by_date.items():
            normalized_rates = self._normalize_rates(rate_map)
            normalized_rates[self._canonical_base] = Decimal("1")
            try:
                rebased = self._transform_rates(normalized_rates, base_currency, include_base=True)
            except ProviderError:
                continue

            rate_value = rebased.get(quote_currency)
            if rate_value is None:
                continue

            points.append(
                RatePoint(
                    timestamp=self._parse_date(date_str),
                    rate=rate_value,
                )
            )

        points.sort(key=lambda point: point.timestamp)

        return RateHistorySeries(
            base_currency=base_currency,
            quote_currency=quote_currency,
            source=self.name,
            points=points,
        )

    def _fetch_latest(self, symbols: Iterable[str]) -> tuple[datetime, dict[str, Decimal]]:
        params: dict[str, str] = {"from": self._canonical_base}
        targets = sorted(set(symbols) - {self._canonical_base})
        if targets:
            params["to"] = ",".join(targets)

        try:
            payload = self._client.get("/latest", params=params)
        except FrankfurterAPIError as exc:
            raise ProviderError(str(exc)) from exc

        rates = self._normalize_rates(payload["rates"])
        rates[self._canonical_base] = Decimal("1")

        timestamp = self._parse_date(payload["date"])
        return timestamp, rates

    def _transform_rates(
        self,
        rates: Mapping[str, Decimal],
        target_base: str,
        *,
        include_base: bool = False,
    ) -> dict[str, Decimal]:
        if target_base == self._canonical_base:
            result = {code: value for code, value in rates.items() if code != self._canonical_base}
            return result if include_base else result

        try:
            rebased = rebase_rates(rates, target_base)
        except RebaseError as exc:
            raise ProviderError(str(exc)) from exc

        if not include_base:
            rebased.pop(target_base, None)
        return rebased

    def _normalize_rates(self, rates: Mapping[str, float | Decimal]) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        for code, value in rates.items():
            normalized[code.upper()] = Decimal(str(value))
        return normalized

    def _allowed_symbols(self, exclude: str | None = None) -> Iterable[str]:
        codes: Iterable[str] = registry.codes or []
        for code in codes:
            if exclude and code.upper() == exclude.upper():
                continue
            yield code.upper()

    def _ensure_supported(self, code: str) -> None:
        normalized = code.upper()
        if normalized == self._canonical_base:
            return
        if not registry.is_allowed(normalized):
            raise ProviderError(f"Currency '{normalized}' is not supported by the registry.")

    @staticmethod
    def _parse_date(value: str) -> datetime:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt

    @staticmethod
    def _current_date() -> date:
        return datetime.now(UTC).date()
