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
    assert body["supported_input_modes"] == ["pas_ref", "inline_bundle"]
    feature_keys = {item["key"] for item in body["features"]}
    assert "dpm.execution.stateful_pas_ref" in feature_keys
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
    assert body["supported_input_modes"] == ["pas_ref"]
