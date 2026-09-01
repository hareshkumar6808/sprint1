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

