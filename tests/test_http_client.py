from __future__ import annotations

import itertools
from unittest.mock import MagicMock

import pytest
from requests import Response

from app.providers.http_client import HTTPClient, HTTPClientConfig, HTTPClientError


def make_response(status_code: int, json_data: dict | None = None) -> Response:
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.text = "error"
    if json_data is None:
        resp.json.side_effect = ValueError("no json")  # type: ignore[attr-defined]
    else:
        resp.json.return_value = json_data  # type: ignore[attr-defined]
    return resp


def test_http_client_success(monkeypatch):
    session = MagicMock()
    config = HTTPClientConfig(base_url="https://example.com", max_retries=1)
    client = HTTPClient(config=config, session=session)
    session.get.return_value = make_response(200, {"ok": True})

    payload = client.get("/latest", params={"foo": "bar"})

    assert payload == {"ok": True}
    session.get.assert_called_once()


def test_http_client_retries_then_succeeds(monkeypatch):
    session = MagicMock()
    config = HTTPClientConfig(base_url="https://example.com", max_retries=2, backoff_seconds=0)
    client = HTTPClient(config=config, session=session)

    responses = [make_response(500), make_response(200, {"value": 1})]
    session.get.side_effect = responses

    monkeypatch.setattr("time.sleep", lambda *_: None)
    monkeypatch.setattr("random.uniform", lambda *_: 0)

    payload = client.get("/data")

    assert payload == {"value": 1}
    assert session.get.call_count == 2


def test_http_client_raises_after_retries_exhausted(monkeypatch):
    session = MagicMock()
    config = HTTPClientConfig(base_url="https://example.com", max_retries=2, backoff_seconds=0)
    client = HTTPClient(config=config, session=session)
    session.get.return_value = make_response(500)

    monkeypatch.setattr("time.sleep", lambda *_: None)

    with pytest.raises(HTTPClientError) as exc_info:
        client.get("/data")

    assert "Failed to fetch" in str(exc_info.value)
    assert exc_info.value.status_code is None
    assert session.get.call_count == 2
