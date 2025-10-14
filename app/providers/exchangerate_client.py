"""HTTP client for the ExchangeRate.host API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import requests
from requests import Response, Session
from requests.exceptions import JSONDecodeError, RequestException

logger = logging.getLogger(__name__)


class ExchangeRateHostError(RuntimeError):
    """Raised when the ExchangeRate.host API returns an error response."""


@dataclass
class ExchangeRateHostClientConfig:
    """Configuration parameters for the API client."""

    base_url: str
    timeout: float
    max_retries: int = 3
    backoff_seconds: float = 0.5


class ExchangeRateHostClient:
    """Minimal HTTP client with retry/backoff for ExchangeRate.host."""

    def __init__(
        self,
        config: ExchangeRateHostClientConfig,
        session: Optional[Session] = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Perform a GET request with retry/backoff semantics."""

        url = self._build_url(path)
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < self._config.max_retries:
            attempt += 1
            try:
                response = self._session.get(
                    url,
                    params=params,
                    timeout=self._config.timeout,
                )
                return self._handle_response(response)
            except (RequestException, ExchangeRateHostError) as err:
                last_error = err
                if attempt >= self._config.max_retries:
                    break
                sleep_for = self._config.backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "ExchangeRate.host request failed (attempt %s/%s): %s. Retrying in %.2fs.",
                    attempt,
                    self._config.max_retries,
                    err,
                    sleep_for,
                )
                time.sleep(sleep_for)

        raise ExchangeRateHostError(f"Failed to fetch data from ExchangeRate.host: {last_error}") from last_error

    def _build_url(self, path: str) -> str:
        base = self._config.base_url.rstrip("/")
        suffix = path.lstrip("/")
        return f"{base}/{suffix}"

    @staticmethod
    def _handle_response(response: Response) -> Dict[str, Any]:
        status = response.status_code
        if status >= 500:
            raise ExchangeRateHostError(f"ExchangeRate.host returned {status}")
        if status >= 400:
            raise ExchangeRateHostError(
                f"ExchangeRate.host client error {status}: {response.text}"
            )

        try:
            payload: Dict[str, Any] = response.json()
        except JSONDecodeError as exc:  # pragma: no cover - unlikely but guarded
            raise ExchangeRateHostError("Invalid JSON response from ExchangeRate.host") from exc

        if not payload.get("success", True):
            error_info = payload.get("error") or {}
            raise ExchangeRateHostError(
                f"ExchangeRate.host error payload: {error_info}",
            )

        return payload
