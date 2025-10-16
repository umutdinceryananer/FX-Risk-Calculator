"""HTTP client for the ECB Frankfurter API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import requests
from requests import Response, Session
from requests.exceptions import JSONDecodeError, RequestException

logger = logging.getLogger(__name__)


class FrankfurterAPIError(RuntimeError):
    """Raised when the Frankfurter API returns an error response."""


@dataclass(frozen=True)
class FrankfurterClientConfig:
    """Configuration parameters for the Frankfurter client."""

    base_url: str
    timeout: float
    max_retries: int = 3
    backoff_seconds: float = 0.5


class FrankfurterClient:
    """Minimal HTTP client with retry/backoff semantics for the Frankfurter API."""

    def __init__(self, config: FrankfurterClientConfig, session: Optional[Session] = None) -> None:
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
            except (RequestException, FrankfurterAPIError) as exc:
                last_error = exc
                if attempt >= self._config.max_retries:
                    break
                sleep_for = self._config.backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Frankfurter request failed (attempt %s/%s): %s. Retrying in %.2fs.",
                    attempt,
                    self._config.max_retries,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)

        raise FrankfurterAPIError(f"Failed to fetch data from Frankfurter API: {last_error}") from last_error

    def _build_url(self, path: str) -> str:
        base = self._config.base_url.rstrip("/")
        suffix = path.lstrip("/")
        return f"{base}/{suffix}"

    @staticmethod
    def _handle_response(response: Response) -> Dict[str, Any]:
        status = response.status_code
        if status >= 500:
            raise FrankfurterAPIError(f"Frankfurter API returned {status}")
        if status >= 400:
            raise FrankfurterAPIError(
                f"Frankfurter API client error {status}: {response.text}"
            )

        try:
            payload: Dict[str, Any] = response.json()
        except JSONDecodeError as exc:  # pragma: no cover - defensive
            raise FrankfurterAPIError("Invalid JSON response from Frankfurter API") from exc

        if "error" in payload:
            raise FrankfurterAPIError(f"Frankfurter API error payload: {payload['error']}")

        if "rates" not in payload:
            raise FrankfurterAPIError("Frankfurter API response missing 'rates' field")

        return payload
