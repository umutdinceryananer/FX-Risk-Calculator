from __future__ import annotations

from decimal import Decimal

import pytest

from app.database import get_session
from app.models import Portfolio, Position


@pytest.fixture(autouse=True)
def _cleanup_db(app):
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


@pytest.fixture()
def portfolio(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Test Book", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.get_json()


def _create_position(client, portfolio_id: int, payload: dict):
    response = client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json=payload)
    assert response.status_code == 201
    return response.get_json()


def test_create_position_success(client, portfolio):
    payload = {"currency_code": "EUR", "amount": "1500.25", "side": "LONG"}
    created = _create_position(client, portfolio["id"], payload)
    assert created["currency_code"] == "EUR"
    assert Decimal(created["amount"]) == Decimal("1500.25")
    assert created["side"] == "LONG"
    assert created["id"] is not None


def test_create_position_validates_amount(client, portfolio):
    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/positions",
        json={"currency_code": "EUR", "amount": "-10"},
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "Amount must be greater than zero." in payload["errors"]["json"]["amount"][0]


def test_create_position_validates_currency(client, portfolio):
    response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/positions",
        json={"currency_code": "XXX", "amount": "10"},
    )
    assert response.status_code == 422
    assert "Unsupported currency code" in response.get_json()["message"]


def test_list_positions_supports_filters(client, portfolio):
    _create_position(client, portfolio["id"], {"currency_code": "EUR", "amount": "10"})
    _create_position(client, portfolio["id"], {"currency_code": "GBP", "amount": "5", "side": "SHORT"})

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/positions")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["total"] == 2

    eur_response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/positions?currency=eur"
    )
    eur_payload = eur_response.get_json()
    assert eur_payload["total"] == 1
    assert eur_payload["items"][0]["currency_code"] == "EUR"

    short_response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/positions?side=short"
    )
    short_payload = short_response.get_json()
    assert short_payload["total"] == 1
    assert short_payload["items"][0]["side"] == "SHORT"


def test_get_position_returns_404_for_wrong_portfolio(client, portfolio):
    created = _create_position(client, portfolio["id"], {"currency_code": "EUR", "amount": "10"})

    other_portfolio = client.post(
        "/api/v1/portfolios",
        json={"name": "Other Book", "base_currency": "USD"},
    ).get_json()

    response = client.get(f"/api/v1/portfolios/{other_portfolio['id']}/positions/{created['id']}")
    assert response.status_code == 404


def test_update_position(client, portfolio):
    created = _create_position(client, portfolio["id"], {"currency_code": "EUR", "amount": "100"})

    response = client.put(
        f"/api/v1/portfolios/{portfolio['id']}/positions/{created['id']}",
        json={"amount": "250.5", "side": "short"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert Decimal(payload["amount"]) == Decimal("250.5")
    assert payload["side"] == "SHORT"

    fetch = client.get(f"/api/v1/portfolios/{portfolio['id']}/positions/{created['id']}")
    assert fetch.status_code == 200
    assert Decimal(fetch.get_json()["amount"]) == Decimal("250.5")


def test_delete_position_removes_record(client, portfolio):
    created = _create_position(client, portfolio["id"], {"currency_code": "EUR", "amount": "50"})
    session = get_session()

    response = client.delete(f"/api/v1/portfolios/{portfolio['id']}/positions/{created['id']}")
    assert response.status_code == 204

    remaining = (
        session.query(Position)
        .filter(Position.portfolio_id == portfolio["id"], Position.id == created["id"])
        .count()
    )
    assert remaining == 0
