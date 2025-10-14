from __future__ import annotations


def test_validate_currency_accepts_seeded_code(client):
    response = client.post("/currencies/validate", json={"code": "usd"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["code"] == "USD"
    assert payload["message"] == "Currency code is valid."


def test_validate_currency_rejects_unknown_code(client):
    response = client.post("/currencies/validate", json={"code": "xyz"})
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["code"] == "XYZ"
    assert payload["field"] == "code"
    assert "Unsupported currency code" in payload["message"]


def test_validate_currency_requires_code_field(client):
    response = client.post("/currencies/validate", json={})
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["field"] == "code"
    assert "is required" in payload["message"]
