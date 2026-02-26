from fastapi.testclient import TestClient
from src.app.main import SERVICE_NAME, app


def test_health_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200


def test_integration_capabilities_contract() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/platform/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["sourceService"] == SERVICE_NAME
    assert isinstance(body["features"], list)
    assert isinstance(body["workflows"], list)
