from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.providers.http_client import HTTPClient, HTTPClientConfig, HTTPClientError

logger = logging.getLogger(__name__)


class FrankfurterAPIError(RuntimeError):
    """Raised when the Frankfurter API returns an error response."""


class FrankfurterClientConfig:
    """Configuration parameters for the Frankfurter client."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds


class FrankfurterClient:
    """HTTP client for Frankfurter built on the shared wrapper."""

    def __init__(
        self,
        config: FrankfurterClientConfig,
        client: HTTPClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or HTTPClient(
            HTTPClientConfig(
                base_url=config.base_url,
                timeout=config.timeout,
                max_retries=config.max_retries,
                backoff_seconds=config.backoff_seconds,
            )
        )

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            payload = self._client.get(path, params=params)
        except HTTPClientError as exc:
            raise FrankfurterAPIError(str(exc)) from exc

        if "rates" not in payload:
            raise FrankfurterAPIError("Frankfurter API response missing 'rates' field")

        if "error" in payload:
            raise FrankfurterAPIError(f"Frankfurter API error payload: {payload['error']}")

        return payload
