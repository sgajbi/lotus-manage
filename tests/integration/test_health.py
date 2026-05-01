from fastapi.testclient import TestClient
from src.app.main import SERVICE_NAME, app


def test_health_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_integration_capabilities_contract() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/integration/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["source_service"] == SERVICE_NAME
    assert isinstance(body["features"], list)
    assert isinstance(body["workflows"], list)


def test_integration_capabilities_honors_explicit_query_context() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/v1/integration/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-performance"
    assert body["tenant_id"] == "tenant-x"
