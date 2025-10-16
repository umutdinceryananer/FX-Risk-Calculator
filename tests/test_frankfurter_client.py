from __future__ import annotations

import pytest
import responses
from responses import matchers

from app.providers.frankfurter_client import (
    FrankfurterAPIError,
    FrankfurterClient,
    FrankfurterClientConfig,
)


@pytest.fixture()
def client():
    config = FrankfurterClientConfig(
        base_url="https://api.frankfurter.app",
        timeout=2,
        max_retries=1,
        backoff_seconds=0,
    )
    return FrankfurterClient(config)


@responses.activate
def test_frankfurter_client_returns_payload(client):
    responses.add(
        responses.GET,
        "https://api.frankfurter.app/latest",
        json={
            "amount": 1.0,
            "base": "EUR",
            "date": "2025-10-13",
            "rates": {"USD": 1.0623, "GBP": 0.87},
        },
        match=[matchers.query_param_matcher({"base": "EUR", "symbols": "USD,GBP"})],
        status=200,
    )

    data = client.get("/latest", params={"base": "EUR", "symbols": "USD,GBP"})

    assert data["base"] == "EUR"
    assert data["rates"]["USD"] == 1.0623


@responses.activate
def test_frankfurter_client_raises_on_http_error(client):
    responses.add(
        responses.GET,
        "https://api.frankfurter.app/latest",
        status=500,
    )

    with pytest.raises(FrankfurterAPIError):
        client.get("/latest")


@responses.activate
def test_frankfurter_client_validates_payload(client):
    responses.add(
        responses.GET,
        "https://api.frankfurter.app/latest",
        json={"amount": 1.0, "date": "2025-10-13"},
        status=200,
    )

    with pytest.raises(FrankfurterAPIError) as exc_info:
        client.get("/latest")

    assert "missing 'rates'" in str(exc_info.value)
