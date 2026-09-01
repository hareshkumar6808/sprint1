from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "finsync-intelligence-api", "version": "0.1.0"}


def test_stocks_are_simulated() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/stocks")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert all(stock["simulated_data"] for stock in response.json())


def test_cors_supports_both_local_frontend_hosts() -> None:
    with TestClient(app) as client:
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            response = client.options("/api/v1/stocks", headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            })
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
