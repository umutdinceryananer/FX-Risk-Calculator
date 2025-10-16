"""Shared HTTP client wrapper with retries, backoff, and jitter."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import requests
from requests import Response, Session
from requests.exceptions import JSONDecodeError, RequestException

logger = logging.getLogger(__name__)


class HTTPClientError(RuntimeError):
    """Raised when the HTTP client cannot satisfy a request."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class HTTPClientConfig:
    """Configuration for the shared HTTP client."""

    base_url: str
    timeout: float = 5.0
    max_retries: int = 3
    backoff_seconds: float = 0.5
    backoff_jitter: float = 0.2


class HTTPClient:
    """Small HTTP client that applies retry/backoff/jitter policies."""

    def __init__(
        self,
        config: HTTPClientConfig,
        session: Optional[Session] = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        url = self._build_url(path)
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < self._config.max_retries:
            attempt += 1
            try:
                response = self._session.get(url, params=params, timeout=self._config.timeout)
                return self._handle_response(response)
            except (RequestException, HTTPClientError) as exc:
                last_error = exc
                if attempt >= self._config.max_retries:
                    break
                sleep_for = self._compute_backoff(attempt)
                logger.warning(
                    "HTTP request to %s failed (attempt %s/%s): %s. Retrying in %.2fs.",
                    url,
                    attempt,
                    self._config.max_retries,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)

        raise HTTPClientError(f"Failed to fetch {url}: {last_error}") from last_error

    def _compute_backoff(self, attempt: int) -> float:
        base = self._config.backoff_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(-self._config.backoff_jitter, self._config.backoff_jitter)
        delay = max(base + jitter, 0.0)
        return delay

    def _build_url(self, path: str) -> str:
        base = self._config.base_url.rstrip("/")
        suffix = path.lstrip("/")
        return f"{base}/{suffix}"

    @staticmethod
    def _handle_response(response: Response) -> Dict[str, Any]:
        status = response.status_code
        if status >= 500:
            raise HTTPClientError(f"Server error {status}", status_code=status)
        if status >= 400:
            raise HTTPClientError(f"Client error {status}: {response.text}", status_code=status)

        try:
            payload: Dict[str, Any] = response.json()
        except JSONDecodeError as exc:  # pragma: no cover
            raise HTTPClientError("Invalid JSON response") from exc

        return payload
