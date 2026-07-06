from fastapi.testclient import TestClient
from src.app.main import SERVICE_NAME, app


def test_health_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_version_endpoint_exposes_image_release_metadata(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_IMAGE_GIT_SHA", "abc123")
    monkeypatch.setenv("LOTUS_IMAGE_GIT_BRANCH", "feature/supply-chain")
    monkeypatch.setenv("LOTUS_IMAGE_BUILD_TIMESTAMP", "2026-07-06T00:00:00Z")
    monkeypatch.setenv("LOTUS_IMAGE_REPO_URL", "https://github.com/sgajbi/lotus-manage")
    monkeypatch.setenv("LOTUS_IMAGE_DIGEST", "ghcr.io/sgajbi/lotus-manage@sha256:abc")
    monkeypatch.setenv("LOTUS_IMAGE_CI_PIPELINE_ID", "12345")

    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "service_name": "lotus-manage",
        "version": "0.1.0",
        "git_commit_sha": "abc123",
        "git_branch": "feature/supply-chain",
        "build_timestamp": "2026-07-06T00:00:00Z",
        "repo_url": "https://github.com/sgajbi/lotus-manage",
        "image_digest": "ghcr.io/sgajbi/lotus-manage@sha256:abc",
        "ci_pipeline_id": "12345",
    }


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


def test_integration_capabilities_accepts_lotus_idea_context() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/v1/integration/capabilities?consumer_system=lotus-idea&tenant_id=default"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-idea"
    assert body["tenant_id"] == "default"
