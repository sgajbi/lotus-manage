from fastapi.testclient import TestClient

import src.api.routers.integration_capabilities as capabilities_router
from src.api.main import app


EXPECTED_FEATURE_KEYS = [
    "dpm.execution.stateful_portfolio_id",
    "dpm.execution.stateless_inline_bundle",
    "dpm.workflow.review_gate",
    "dpm.execution.solver_target_generation",
    "manage.observability.action_register_supportability",
]


def test_integration_capabilities_default_contract(monkeypatch):
    monkeypatch.setattr(capabilities_router, "has_solver_dependencies", lambda: True)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "v1"
    assert body["source_service"] == "lotus-manage"
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"
    assert "features" in body
    assert "workflows" in body
    assert body["supported_input_modes"] == ["inline_bundle"]
    assert [item["key"] for item in body["features"]] == EXPECTED_FEATURE_KEYS
    features = {item["key"]: item["enabled"] for item in body["features"]}
    assert features["dpm.execution.stateful_portfolio_id"] is False
    assert features["dpm.execution.stateless_inline_bundle"] is True
    assert features["dpm.execution.solver_target_generation"] is True
    assert features["manage.observability.action_register_supportability"] is True
    assert body["workflows"] == [
        {
            "workflow_key": "dpm_rebalance_lifecycle",
            "enabled": False,
            "required_features": ["dpm.workflow.review_gate"],
        }
    ]


def test_integration_capabilities_env_overrides(monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "false")
    monkeypatch.setenv("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", "false")
    monkeypatch.setenv("DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_VERSION", "tenant-x-v2")
    monkeypatch.setattr(capabilities_router, "has_solver_dependencies", lambda: False)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integration/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-performance"
    assert body["tenant_id"] == "tenant-x"
    assert body["policy_version"] == "tenant-x-v2"
    features = {item["key"]: item["enabled"] for item in body["features"]}
    assert features["dpm.workflow.review_gate"] is False
    assert features["dpm.execution.stateful_portfolio_id"] is True
    assert features["dpm.execution.stateless_inline_bundle"] is False
    assert features["dpm.execution.solver_target_generation"] is False
    assert body["supported_input_modes"] == ["portfolio_id"]
    assert body["workflows"][0]["enabled"] is False


def test_integration_capabilities_can_publish_both_supported_input_modes(monkeypatch):
    monkeypatch.setenv("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", "true")
    monkeypatch.setenv("DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED", "true")
    monkeypatch.setattr(capabilities_router, "has_solver_dependencies", lambda: False)

    with TestClient(app) as client:
        response = client.get("/api/v1/integration/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["supported_input_modes"] == ["portfolio_id", "inline_bundle"]
    features = {item["key"]: item["enabled"] for item in body["features"]}
    assert features["dpm.execution.stateful_portfolio_id"] is True
    assert features["dpm.execution.stateless_inline_bundle"] is True


def test_integration_capabilities_uses_default_query_resolution_when_omitted():
    with TestClient(app) as client:
        response = client.get("/api/v1/integration/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"


def test_platform_capabilities_alias_is_removed() -> None:
    with TestClient(app) as client:
        platform = client.get(
            "/api/v1/platform/capabilities?consumer_system=lotus-performance&tenant_id=tenant-x"
        )

    assert platform.status_code == 404


def test_integration_capabilities_ignores_noncanonical_camel_case_query_params() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integration/capabilities?consumerSystem=lotus-performance&tenantId=tenant-x"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["consumer_system"] == "lotus-gateway"
    assert body["tenant_id"] == "default"
