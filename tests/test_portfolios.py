from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.database import get_session
from app.models import Portfolio, Position


@pytest.fixture(autouse=True)
def _cleanup_portfolios(app):
    """Ensure portfolio-related tables are clean before and after each test."""

    with app.app_context():
        session = get_session()
        session.query(Position).delete()
        session.query(Portfolio).delete()
        session.commit()
    yield
    with app.app_context():
        session = get_session()
        session.query(Position).delete()
        session.query(Portfolio).delete()
        session.commit()


def _create_portfolio(client, name: str, base_currency: str = "USD") -> dict[str, Any]:
    response = client.post(
        "/api/v1/portfolios",
        json={"name": name, "base_currency": base_currency},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert isinstance(payload, dict)
    return payload


def test_create_portfolio_success(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Alpha Fund", "base_currency": "USD"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Alpha Fund"
    assert data["base_currency"] == "USD"
    location = response.headers.get("Location")
    assert location == f"/api/v1/portfolios/{data['id']}"

    fetch = client.get(location)
    assert fetch.status_code == 200
    assert fetch.get_json() == data


def test_create_portfolio_rejects_invalid_currency(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Invalid Fund", "base_currency": "XXX"},
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "Unsupported currency code" in payload["message"]


def test_get_portfolio_returns_404_for_missing(client):
    response = client.get("/api/v1/portfolios/9999")
    assert response.status_code == 404


def test_update_portfolio_allows_partial(client):
    created = _create_portfolio(client, "Beta Fund", "USD")

    response = client.put(
        f"/api/v1/portfolios/{created['id']}",
        json={"name": "Beta Growth", "base_currency": "eur"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "Beta Growth"
    assert payload["base_currency"] == "EUR"

    check = client.get(f"/api/v1/portfolios/{created['id']}")
    assert check.status_code == 200
    assert check.get_json() == payload


def test_list_portfolios_supports_pagination(client):
    _create_portfolio(client, "Fund A", "USD")
    _create_portfolio(client, "Fund B", "EUR")
    _create_portfolio(client, "Fund C", "GBP")

    response = client.get("/api/v1/portfolios?page=1&page_size=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert len(payload["items"]) == 2

    response_page_2 = client.get("/api/v1/portfolios?page=2&page_size=2")
    assert response_page_2.status_code == 200
    payload_page_2 = response_page_2.get_json()
    assert payload_page_2["page"] == 2
    assert len(payload_page_2["items"]) == 1


def test_delete_portfolio_cascades_positions(client):
    created = _create_portfolio(client, "Gamma Fund", "USD")
    portfolio_id = created["id"]

    session = get_session()
    session.add(
        Position(
            portfolio_id=portfolio_id,
            currency_code="EUR",
            amount=Decimal("1000.00"),
        )
    )
    session.commit()

    count = session.query(Position).filter_by(portfolio_id=portfolio_id).count()
    assert count == 1

    response = client.delete(f"/api/v1/portfolios/{portfolio_id}")
    assert response.status_code == 204

    remaining = session.query(Position).filter_by(portfolio_id=portfolio_id).count()
    assert remaining == 0

    verify = client.get(f"/api/v1/portfolios/{portfolio_id}")
    assert verify.status_code == 404


def test_create_portfolio_requires_name(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "   ", "base_currency": "USD"},
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "Portfolio name cannot be blank" in payload["message"]


def test_create_portfolio_enforces_unique_name(client):
    _create_portfolio(client, "Alpha Fund", "USD")
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Alpha Fund", "base_currency": "EUR"},
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "Portfolio name must be unique" in payload["message"]
