from fastapi.testclient import TestClient

from src.api.main import app


def test_integration_capabilities_default_contract():
    with TestClient(app) as client:
        response = client.get(
            "/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "v1"
    assert body["source_service"] == "lotus-manage"
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"
    assert "features" in body
    assert "workflows" in body
    assert body["supported_input_modes"] == ["portfolio_id", "inline_bundle"]
    feature_keys = {item["key"] for item in body["features"]}
    assert "dpm.execution.stateful_portfolio_id" in feature_keys
    assert "dpm.execution.stateless_inline_bundle" in feature_keys


def test_integration_capabilities_env_overrides(monkeypatch):
    monkeypatch.setenv("DPM_CAP_PROPOSAL_LIFECYCLE_ENABLED", "false")
    monkeypatch.setenv("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_VERSION", "tenant-x-v2")

    with TestClient(app) as client:
        response = client.get(
            "/integration/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-performance"
    assert body["tenant_id"] == "tenant-x"
    assert body["policy_version"] == "tenant-x-v2"
    features = {item["key"]: item["enabled"] for item in body["features"]}
    assert features["dpm.proposals.lifecycle"] is False
    assert body["supported_input_modes"] == ["portfolio_id"]


def test_integration_capabilities_uses_default_query_resolution_when_omitted():
    with TestClient(app) as client:
        response = client.get("/integration/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"


def test_platform_capabilities_alias_matches_integration_contract_payload() -> None:
    with TestClient(app) as client:
        integration = client.get(
            "/integration/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
        )
        platform = client.get(
            "/platform/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
        )

    assert integration.status_code == 200
    assert platform.status_code == 200

    integration_body = integration.json()
    platform_body = platform.json()
    assert platform_body["contract_version"] == integration_body["contract_version"]
    assert platform_body["source_service"] == integration_body["source_service"]
    assert platform_body["consumer_system"] == "lotus-performance"
    assert platform_body["tenant_id"] == "tenant-x"
    assert platform_body["policy_version"] == integration_body["policy_version"]
    assert platform_body["supported_input_modes"] == integration_body["supported_input_modes"]
    assert platform_body["features"] == integration_body["features"]
    assert platform_body["workflows"] == integration_body["workflows"]


def test_platform_capabilities_ignores_noncanonical_camel_case_query_params() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/platform/capabilities?consumerSystem=lotus-performance&tenantId=tenant-x"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"
