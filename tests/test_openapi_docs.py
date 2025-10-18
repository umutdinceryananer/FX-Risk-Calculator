from __future__ import annotations


def test_docs_swagger_ui(client):
    response = client.get("/docs/")
    assert response.status_code == 200
    assert b"Swagger" in response.data


def test_openapi_spec_lists_endpoints(client):
    response = client.get("/docs/openapi.json")
    assert response.status_code == 200
    data = response.get_json()
    assert any(path.startswith("/health") for path in data["paths"].keys())
    assert "/currencies/validate" in data["paths"]
    assert "/api/v1/portfolios" in data["paths"]
    assert "/api/v1/portfolios/{portfolio_id}" in data["paths"]
    assert "/api/v1/portfolios/{portfolio_id}/positions" in data["paths"]
    assert "/api/v1/portfolios/{portfolio_id}/positions/{position_id}" in data["paths"]
    assert "/api/v1/metrics/portfolio/{portfolio_id}/value" in data["paths"]
    assert "/api/v1/metrics/portfolio/{portfolio_id}/exposure" in data["paths"]
    assert "/api/v1/metrics/portfolio/{portfolio_id}/pnl/daily" in data["paths"]
    assert "/api/v1/metrics/portfolio/{portfolio_id}/whatif" in data["paths"]
