"""Smoke tests for health endpoints."""

from __future__ import annotations


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"


def test_health_rates_endpoint_returns_uninitialized(client):
    response = client.get("/health/rates")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rates_status"] == "uninitialized"
