from datetime import date

from src.api.services.integration_capabilities_service import (
    build_capabilities_response,
    stateful_execution_publishable,
    supported_input_modes,
)


def test_supported_input_modes_preserves_stateful_first_ordering() -> None:
    assert supported_input_modes(stateful_enabled=True, stateless_enabled=True) == [
        "stateful",
        "stateless",
    ]
    assert supported_input_modes(stateful_enabled=False, stateless_enabled=True) == ["stateless"]
    assert supported_input_modes(stateful_enabled=True, stateless_enabled=False) == ["stateful"]
    assert supported_input_modes(stateful_enabled=False, stateless_enabled=False) == []


def test_stateful_execution_publishable_is_false_without_required_flags() -> None:
    assert not stateful_execution_publishable(
        env_get=lambda name: {
            "DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED": "true",
            "DPM_STATEFUL_CORE_SOURCING_ENABLED": "false",
            "DPM_CORE_BASE_URL": "http://core.example",
            "DPM_CORE_RESOLVER_PATH_TEMPLATE": "/integration/portfolios/{portfolio_id}/core-snapshot",
        }.get(name)
    )


def test_stateful_execution_publishable_is_false_for_legacy_resolver_route() -> None:
    assert not stateful_execution_publishable(
        env_get=lambda name: {
            "DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED": "true",
            "DPM_STATEFUL_CORE_SOURCING_ENABLED": "true",
            "DPM_CORE_BASE_URL": "http://core.example",
            "DPM_CORE_RESOLVER_PATH_TEMPLATE": "/integration/portfolios/{portfolio_id}/dpm-execution-context",
        }.get(name)
    )


def test_stateful_execution_publishable_is_true_when_all_requirements_match() -> None:
    assert stateful_execution_publishable(
        env_get=lambda name: {
            "DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED": "true",
            "DPM_STATEFUL_CORE_SOURCING_ENABLED": "true",
            "DPM_CORE_BASE_URL": "http://core.example",
            "DPM_CORE_RESOLVER_PATH_TEMPLATE": "/integration/portfolios/{portfolio_id}/core-snapshot",
        }.get(name)
    )


def test_build_capabilities_response_applies_defaults_and_supplies_all_sections() -> None:
    response = build_capabilities_response(
        consumer_system="lotus-gateway",
        tenant_id="tenant-a",
        solver_available=True,
        env_get=lambda name: None,
    )

    assert response["contract_version"] == "v1"
    assert response["source_service"] == "lotus-manage"
    assert response["consumer_system"] == "lotus-gateway"
    assert response["tenant_id"] == "tenant-a"
    assert response["as_of_date"] == date.today()
    assert response["policy_version"] == "dpm.policy.v1"
    assert response["supported_input_modes"] == ["stateless"]
    features = {item["key"]: item["enabled"] for item in response["features"]}
    assert features["dpm.execution.stateful_portfolio_id"] is False
    assert features["dpm.execution.stateless"] is True
    assert features["dpm.execution.solver_target_generation"] is True
    assert features["manage.observability.action_register_supportability"] is True
    assert response["workflows"][0]["workflow_key"] == "dpm_rebalance_lifecycle"


def test_build_capabilities_response_uses_explicit_environment_overrides() -> None:
    override = {
        "DPM_CAP_SOURCE_SERVICE": "gateway",
        "DPM_POLICY_VERSION": "tenant-override-v2",
    }
    response = build_capabilities_response(
        consumer_system="lotus-gateway",
        tenant_id="tenant-b",
        solver_available=False,
        env_get=lambda name: override.get(name),
    )

    assert response["source_service"] == "gateway"
    assert response["policy_version"] == "tenant-override-v2"
    assert response["features"][2]["enabled"] is False
    assert response["workflows"][0]["enabled"] is False
