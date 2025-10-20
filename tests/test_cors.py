from __future__ import annotations


def test_cors_allows_configured_origin(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "Origin" in (response.headers.get("Vary") or "")


def test_cors_blocks_unlisted_origin(client):
    response = client.get("/health", headers={"Origin": "http://malicious.local"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_handles_preflight_options(client):
    response = client.options(
        "/rates/refresh",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 204
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "POST" in (response.headers.get("Access-Control-Allow-Methods") or "")
    assert "Content-Type" in (response.headers.get("Access-Control-Allow-Headers") or "")
