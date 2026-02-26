from fastapi.testclient import TestClient
from src.app.main import app


def test_e2e_smoke() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_versioned_proposals_surface_exists() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/rebalance/proposals")
    assert response.status_code in {200, 400, 422, 503}
