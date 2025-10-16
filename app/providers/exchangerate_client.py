from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from app.providers.http_client import HTTPClient, HTTPClientConfig, HTTPClientError

logger = logging.getLogger(__name__)


class ExchangeRateHostError(RuntimeError):
    """Raised when the ExchangeRate.host API returns an error response."""


class ExchangeRateHostClient:
    """HTTP client for ExchangeRate.host built on the shared HTTP wrapper."""

    def __init__(self, config: ExchangeRateHostClientConfig, client: Optional[HTTPClient] = None) -> None:
        self._config = config
        self._client = client or HTTPClient(
            HTTPClientConfig(
                base_url=config.base_url,
                timeout=config.timeout,
                max_retries=config.max_retries,
                backoff_seconds=config.backoff_seconds,
            )
        )

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        try:
            payload = self._client.get(path, params=params)
        except HTTPClientError as exc:
            raise ExchangeRateHostError(str(exc)) from exc

        if not payload.get("success", True):
            error_info = payload.get("error") or {}
            raise ExchangeRateHostError(f"ExchangeRate.host error payload: {error_info}")

        return payload


class ExchangeRateHostClientConfig:
    """Configuration parameters for the API client."""

    def __init__(self, base_url: str, timeout: float, max_retries: int = 3, backoff_seconds: float = 0.5) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
