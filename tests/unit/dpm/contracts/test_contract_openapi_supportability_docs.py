import os

import pytest
from fastapi.testclient import TestClient

from src.api.simulation_examples import (
    ANALYZE_ASYNC_ACCEPTED_EXAMPLE,
    ANALYZE_RESPONSE_EXAMPLE,
    SIMULATE_BLOCKED_EXAMPLE,
    SIMULATE_PENDING_EXAMPLE,
    SIMULATE_READY_EXAMPLE,
)
from src.api.main import app
from src.core.models import BatchRebalanceResult, RebalanceResult
from src.core.rebalance_runs import DpmAsyncAcceptedResponse


def _strict_openapi_validation_enabled() -> bool:
    value = os.getenv("DPM_STRICT_OPENAPI_VALIDATION")
    if value is None:
        return True
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _guard_strict_validation() -> None:
    if not _strict_openapi_validation_enabled():
        pytest.skip("DPM_STRICT_OPENAPI_VALIDATION=false")


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop) or ("$ref" in prop)


def _schema_any(schemas: dict, names: list[str]) -> dict:
    for name in names:
        if name in schemas:
            return schemas[name]
    raise KeyError(f"None of schema names present: {names}")


def _has_example(content: dict) -> bool:
    return bool(content.get("example") or content.get("examples"))


def _is_error_status(status_code: object) -> bool:
    normalized = str(status_code)
    return normalized.startswith(("4", "5")) or normalized == "default"


def test_dpm_supportability_and_async_schemas_have_descriptions_and_examples():
    _guard_strict_validation()
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    run_lookup_schema = schemas["DpmRunLookupResponse"]
    _assert_property_has_docs(run_lookup_schema, "rebalance_run_id")
    _assert_property_has_docs(run_lookup_schema, "correlation_id")
    _assert_property_has_docs(run_lookup_schema, "request_hash")
    _assert_property_has_docs(run_lookup_schema, "portfolio_id")
    _assert_property_has_docs(run_lookup_schema, "created_at")
    _assert_property_has_docs(run_lookup_schema, "result")

    run_list_schema = schemas["DpmRunListResponse"]
    _assert_property_has_docs(run_list_schema, "items")
    _assert_property_has_docs(run_list_schema, "next_cursor")

    run_list_item_schema = schemas["DpmRunListItemResponse"]
    _assert_property_has_docs(run_list_item_schema, "rebalance_run_id")
    _assert_property_has_docs(run_list_item_schema, "correlation_id")
    _assert_property_has_docs(run_list_item_schema, "request_hash")
    _assert_property_has_docs(run_list_item_schema, "idempotency_key")
    _assert_property_has_docs(run_list_item_schema, "portfolio_id")
    _assert_property_has_docs(run_list_item_schema, "status")
    _assert_property_has_docs(run_list_item_schema, "created_at")

    idempotency_schema = schemas["DpmRunIdempotencyLookupResponse"]
    _assert_property_has_docs(idempotency_schema, "idempotency_key")
    _assert_property_has_docs(idempotency_schema, "request_hash")
    _assert_property_has_docs(idempotency_schema, "rebalance_run_id")
    _assert_property_has_docs(idempotency_schema, "created_at")

    idempotency_history_schema = schemas["DpmRunIdempotencyHistoryResponse"]
    _assert_property_has_docs(idempotency_history_schema, "idempotency_key")
    _assert_property_has_docs(idempotency_history_schema, "history")

    idempotency_history_item_schema = schemas["DpmRunIdempotencyHistoryItem"]
    _assert_property_has_docs(idempotency_history_item_schema, "rebalance_run_id")
    _assert_property_has_docs(idempotency_history_item_schema, "correlation_id")
    _assert_property_has_docs(idempotency_history_item_schema, "request_hash")
    _assert_property_has_docs(idempotency_history_item_schema, "created_at")

    async_accepted_schema = schemas["DpmAsyncAcceptedResponse"]
    _assert_property_has_docs(async_accepted_schema, "operation_id")
    _assert_property_has_docs(async_accepted_schema, "operation_type")
    _assert_property_has_docs(async_accepted_schema, "status")
    _assert_property_has_docs(async_accepted_schema, "correlation_id")
    _assert_property_has_docs(async_accepted_schema, "created_at")
    _assert_property_has_docs(async_accepted_schema, "status_url")
    _assert_property_has_docs(async_accepted_schema, "execute_url")

    async_status_schema = schemas["DpmAsyncOperationStatusResponse"]
    _assert_property_has_docs(async_status_schema, "operation_id")
    _assert_property_has_docs(async_status_schema, "operation_type")
    _assert_property_has_docs(async_status_schema, "status")
    _assert_property_has_docs(async_status_schema, "is_executable")
    _assert_property_has_docs(async_status_schema, "correlation_id")
    _assert_property_has_docs(async_status_schema, "created_at")
    _assert_property_has_docs(async_status_schema, "result")
    _assert_property_has_docs(async_status_schema, "error")

    async_list_schema = schemas["DpmAsyncOperationListResponse"]
    _assert_property_has_docs(async_list_schema, "items")
    _assert_property_has_docs(async_list_schema, "next_cursor")

    async_list_item_schema = schemas["DpmAsyncOperationListItemResponse"]
    _assert_property_has_docs(async_list_item_schema, "operation_id")
    _assert_property_has_docs(async_list_item_schema, "operation_type")
    _assert_property_has_docs(async_list_item_schema, "status")
    _assert_property_has_docs(async_list_item_schema, "correlation_id")
    _assert_property_has_docs(async_list_item_schema, "is_executable")
    _assert_property_has_docs(async_list_item_schema, "created_at")
    _assert_property_has_docs(async_list_item_schema, "started_at")
    _assert_property_has_docs(async_list_item_schema, "finished_at")

    supportability_summary_schema = schemas["DpmSupportabilitySummaryResponse"]
    _assert_property_has_docs(supportability_summary_schema, "store_backend")
    _assert_property_has_docs(supportability_summary_schema, "retention_days")
    _assert_property_has_docs(supportability_summary_schema, "run_count")
    _assert_property_has_docs(supportability_summary_schema, "operation_count")
    _assert_property_has_docs(supportability_summary_schema, "operation_status_counts")
    _assert_property_has_docs(supportability_summary_schema, "run_status_counts")
    _assert_property_has_docs(supportability_summary_schema, "workflow_decision_count")
    _assert_property_has_docs(supportability_summary_schema, "workflow_action_counts")
    _assert_property_has_docs(supportability_summary_schema, "workflow_reason_code_counts")
    _assert_property_has_docs(supportability_summary_schema, "lineage_edge_count")
    _assert_property_has_docs(supportability_summary_schema, "oldest_run_created_at")

    integration_capabilities_schema = schemas["IntegrationCapabilitiesResponse"]
    _assert_property_has_docs(integration_capabilities_schema, "contract_version")
    _assert_property_has_docs(integration_capabilities_schema, "source_service")
    _assert_property_has_docs(integration_capabilities_schema, "consumer_system")
    _assert_property_has_docs(integration_capabilities_schema, "tenant_id")
    _assert_property_has_docs(integration_capabilities_schema, "generated_at")
    _assert_property_has_docs(integration_capabilities_schema, "as_of_date")
    _assert_property_has_docs(integration_capabilities_schema, "policy_version")
    _assert_property_has_docs(integration_capabilities_schema, "supported_input_modes")
    _assert_property_has_docs(integration_capabilities_schema, "features")
    _assert_property_has_docs(integration_capabilities_schema, "workflows")

    feature_capability_schema = schemas["FeatureCapability"]
    _assert_property_has_docs(feature_capability_schema, "key")
    _assert_property_has_docs(feature_capability_schema, "enabled")
    _assert_property_has_docs(feature_capability_schema, "owner_service")
    _assert_property_has_docs(feature_capability_schema, "description")

    workflow_capability_schema = schemas["WorkflowCapability"]
    _assert_property_has_docs(workflow_capability_schema, "workflow_key")
    _assert_property_has_docs(workflow_capability_schema, "enabled")
    _assert_property_has_docs(workflow_capability_schema, "required_features")
    _assert_property_has_docs(supportability_summary_schema, "newest_run_created_at")
    _assert_property_has_docs(supportability_summary_schema, "oldest_operation_created_at")
    _assert_property_has_docs(supportability_summary_schema, "newest_operation_created_at")

    support_bundle_schema = schemas["DpmRunSupportBundleResponse"]
    _assert_property_has_docs(support_bundle_schema, "run")
    _assert_property_has_docs(support_bundle_schema, "artifact")
    _assert_property_has_docs(support_bundle_schema, "async_operation")
    _assert_property_has_docs(support_bundle_schema, "workflow_history")
    _assert_property_has_docs(support_bundle_schema, "lineage")
    _assert_property_has_docs(support_bundle_schema, "idempotency_history")

    artifact_schema = schemas["DpmRunArtifactResponse"]
    _assert_property_has_docs(artifact_schema, "artifact_id")
    _assert_property_has_docs(artifact_schema, "artifact_version")
    _assert_property_has_docs(artifact_schema, "rebalance_run_id")
    _assert_property_has_docs(artifact_schema, "correlation_id")
    _assert_property_has_docs(artifact_schema, "portfolio_id")
    _assert_property_has_docs(artifact_schema, "status")
    _assert_property_has_docs(artifact_schema, "request_snapshot")
    _assert_property_has_docs(artifact_schema, "before_summary")
    _assert_property_has_docs(artifact_schema, "after_summary")
    _assert_property_has_docs(artifact_schema, "order_intents")
    _assert_property_has_docs(artifact_schema, "rule_outcomes")
    _assert_property_has_docs(artifact_schema, "diagnostics")
    _assert_property_has_docs(artifact_schema, "result")
    _assert_property_has_docs(artifact_schema, "evidence")

    workflow_action_schema = schemas["DpmRunWorkflowActionRequest"]
    _assert_property_has_docs(workflow_action_schema, "action")
    _assert_property_has_docs(workflow_action_schema, "reason_code")
    _assert_property_has_docs(workflow_action_schema, "comment")
    _assert_property_has_docs(workflow_action_schema, "actor_id")

    workflow_schema = schemas["DpmRunWorkflowResponse"]
    _assert_property_has_docs(workflow_schema, "run_id")
    _assert_property_has_docs(workflow_schema, "run_status")
    _assert_property_has_docs(workflow_schema, "workflow_status")
    _assert_property_has_docs(workflow_schema, "requires_review")
    _assert_property_has_docs(workflow_schema, "latest_decision")

    workflow_history_schema = schemas["DpmRunWorkflowHistoryResponse"]
    _assert_property_has_docs(workflow_history_schema, "run_id")
    _assert_property_has_docs(workflow_history_schema, "decisions")

    workflow_list_schema = schemas["DpmWorkflowDecisionListResponse"]
    _assert_property_has_docs(workflow_list_schema, "items")
    _assert_property_has_docs(workflow_list_schema, "next_cursor")

    lineage_schema = schemas["DpmLineageResponse"]
    _assert_property_has_docs(lineage_schema, "entity_id")
    _assert_property_has_docs(lineage_schema, "edges")

    policy_catalog_schema = schemas["DpmPolicyPackCatalogResponse"]
    _assert_property_has_docs(policy_catalog_schema, "enabled")
    _assert_property_has_docs(policy_catalog_schema, "total")
    _assert_property_has_docs(policy_catalog_schema, "selected_policy_pack_id")
    _assert_property_has_docs(policy_catalog_schema, "selected_policy_pack_present")
    _assert_property_has_docs(policy_catalog_schema, "selected_policy_pack_source")
    _assert_property_has_docs(policy_catalog_schema, "items")

    policy_resolution_schema = schemas["DpmEffectivePolicyPackResolution"]
    _assert_property_has_docs(policy_resolution_schema, "enabled")
    _assert_property_has_docs(policy_resolution_schema, "selected_policy_pack_id")
    _assert_property_has_docs(policy_resolution_schema, "source")

    policy_definition_schema = schemas["DpmPolicyPackDefinition"]
    _assert_property_has_docs(policy_definition_schema, "policy_pack_id")
    _assert_property_has_docs(policy_definition_schema, "version")
    _assert_property_has_docs(policy_definition_schema, "turnover_policy")
    _assert_property_has_docs(policy_definition_schema, "tax_policy")
    _assert_property_has_docs(policy_definition_schema, "settlement_policy")
    _assert_property_has_docs(policy_definition_schema, "constraint_policy")
    _assert_property_has_docs(policy_definition_schema, "workflow_policy")
    _assert_property_has_docs(policy_definition_schema, "idempotency_policy")

    turnover_policy_schema = _schema_any(
        schemas,
        ["DpmPolicyPackTurnoverPolicy", "DpmPolicyPackTurnoverPolicy-Output"],
    )
    _assert_property_has_docs(turnover_policy_schema, "max_turnover_pct")

    tax_policy_schema = _schema_any(
        schemas,
        ["DpmPolicyPackTaxPolicy", "DpmPolicyPackTaxPolicy-Output"],
    )
    _assert_property_has_docs(tax_policy_schema, "enable_tax_awareness")
    _assert_property_has_docs(tax_policy_schema, "max_realized_capital_gains")

    settlement_policy_schema = schemas["DpmPolicyPackSettlementPolicy"]
    _assert_property_has_docs(settlement_policy_schema, "enable_settlement_awareness")
    _assert_property_has_docs(settlement_policy_schema, "settlement_horizon_days")

    constraint_policy_schema = _schema_any(
        schemas,
        ["DpmPolicyPackConstraintPolicy", "DpmPolicyPackConstraintPolicy-Output"],
    )
    _assert_property_has_docs(constraint_policy_schema, "single_position_max_weight")
    _assert_property_has_docs(constraint_policy_schema, "group_constraints")

    workflow_policy_schema = schemas["DpmPolicyPackWorkflowPolicy"]
    _assert_property_has_docs(workflow_policy_schema, "enable_workflow_gates")
    _assert_property_has_docs(workflow_policy_schema, "workflow_requires_mandate_approval")
    _assert_property_has_docs(workflow_policy_schema, "mandate_approval_already_obtained")

    idempotency_policy_schema = schemas["DpmPolicyPackIdempotencyPolicy"]
    _assert_property_has_docs(idempotency_policy_schema, "replay_enabled")

    upsert_request_schema = schemas["DpmPolicyPackUpsertRequest"]
    _assert_property_has_docs(upsert_request_schema, "version")
    _assert_property_has_docs(upsert_request_schema, "turnover_policy")
    _assert_property_has_docs(upsert_request_schema, "tax_policy")
    _assert_property_has_docs(upsert_request_schema, "settlement_policy")
    _assert_property_has_docs(upsert_request_schema, "constraint_policy")
    _assert_property_has_docs(upsert_request_schema, "workflow_policy")
    _assert_property_has_docs(upsert_request_schema, "idempotency_policy")

    mutation_response_schema = schemas["DpmPolicyPackMutationResponse"]
    _assert_property_has_docs(mutation_response_schema, "item")

    health_status_schema = schemas["HealthStatusResponse"]
    _assert_property_has_docs(health_status_schema, "status")
    status_schema = health_status_schema["properties"]["status"]
    assert set(status_schema["enum"]) == {"ok", "live", "ready"}


def test_openapi_error_responses_have_json_examples():
    _guard_strict_validation()
    openapi = app.openapi()
    missing: list[str] = []

    for path, operations in sorted(openapi["paths"].items()):
        for method, operation in sorted(operations.items()):
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for status_code, response in sorted(operation.get("responses", {}).items()):
                if not _is_error_status(status_code):
                    continue
                json_content = response.get("content", {}).get("application/json")
                if not isinstance(json_content, dict) or not _has_example(json_content):
                    missing.append(f"{method.upper()} {path} {status_code}")

    assert missing == []


def test_integration_capabilities_paths_have_route_and_query_docs():
    _guard_strict_validation()
    openapi = app.openapi()

    integration_get = openapi["paths"]["/api/v1/integration/capabilities"]["get"]

    assert (
        "backend-governed rebalance feature and workflow capability posture"
        in integration_get["description"]
    )
    assert (
        "canonical snake_case query parameters `consumer_system` and `tenant_id`"
        in (integration_get["description"])
    )

    integration_params = {param["name"]: param for param in integration_get["parameters"]}
    assert integration_params["consumer_system"]["schema"]["default"] == "lotus-gateway"
    assert integration_params["tenant_id"]["schema"]["default"] == "default"
    assert "consumerSystem" not in integration_params
    assert "tenantId" not in integration_params
    assert "422" in integration_get["responses"]
    assert "Unsupported query parameters" in integration_get["responses"]["422"]["description"]
    assert (
        "canonical snake_case query parameter `consumer_system`"
        in integration_params["consumer_system"]["description"]
    )
    assert (
        "canonical snake_case query parameter `tenant_id`"
        in integration_params["tenant_id"]["description"]
    )

    integration_examples = integration_get["responses"]["200"]["content"]["application/json"][
        "examples"
    ]
    default_example = integration_examples["default"]["value"]
    assert default_example["supported_input_modes"] == ["stateless"]
    example_features = {item["key"]: item for item in default_example["features"]}
    assert example_features["dpm.execution.stateful_portfolio_id"]["enabled"] is False
    assert example_features["dpm.execution.stateless"]["enabled"] is True
    assert example_features["dpm.workflow.review_gate"]["enabled"] is False
    assert (
        example_features["manage.observability.action_register_supportability"]["enabled"] is True
    )
    assert default_example["workflows"] == [
        {
            "workflow_key": "dpm_rebalance_lifecycle",
            "enabled": False,
            "required_features": ["dpm.workflow.review_gate"],
        }
    ]


def test_openapi_json_requests_and_responses_have_examples():
    _guard_strict_validation()
    openapi = app.openapi()
    missing: list[str] = []

    for path, operations in sorted(openapi["paths"].items()):
        for method, operation in sorted(operations.items()):
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            request_content = (
                operation.get("requestBody", {}).get("content", {}).get("application/json")
            )
            if isinstance(request_content, dict) and not _has_example(request_content):
                missing.append(f"{method.upper()} {path} request")

            for status_code, response in sorted(operation.get("responses", {}).items()):
                response_content = response.get("content", {}).get("application/json")
                if isinstance(response_content, dict) and not _has_example(response_content):
                    missing.append(f"{method.upper()} {path} {status_code} response")

    assert missing == []


def test_metrics_openapi_documents_prometheus_text_response():
    _guard_strict_validation()
    openapi = app.openapi()

    metrics_response = openapi["paths"]["/metrics"]["get"]["responses"]["200"]
    content = metrics_response["content"]

    assert "application/json" not in content
    prometheus_content = content["text/plain; version=0.0.4"]
    assert prometheus_content["schema"]["type"] == "string"
    assert prometheus_content["examples"]["prometheus"]["value"].startswith(
        "# HELP http_requests_total"
    )


@pytest.mark.parametrize(
    "example",
    [SIMULATE_READY_EXAMPLE, SIMULATE_PENDING_EXAMPLE, SIMULATE_BLOCKED_EXAMPLE],
)
def test_simulate_response_examples_are_complete_rebalance_results(example):
    _guard_strict_validation()

    result = RebalanceResult.model_validate(example["value"])

    assert result.before.total_value.currency
    assert result.after_simulated.total_value.currency
    assert result.universe.coverage.price_coverage_pct is not None
    assert result.target.targets
    assert result.reconciliation is not None
    assert result.diagnostics.data_quality
    assert result.gate_decision is not None
    assert result.lineage.request_hash.startswith("sha256:")


def test_analyze_response_example_is_complete_batch_result():
    _guard_strict_validation()

    result = BatchRebalanceResult.model_validate(ANALYZE_RESPONSE_EXAMPLE["value"])

    assert result.batch_run_id.startswith("batch_")
    assert set(result.results.keys()) == {"baseline"}
    assert set(result.comparison_metrics.keys()) == {"baseline"}
    assert set(result.failed_scenarios.keys()) == {"invalid_case"}
    assert "PARTIAL_BATCH_FAILURE" in result.warnings
    baseline = result.results["baseline"]
    metric = result.comparison_metrics["baseline"]
    expected_turnover = sum(
        intent.notional_base.amount
        for intent in baseline.intents
        if intent.intent_type == "SECURITY_TRADE" and intent.notional_base is not None
    )
    assert metric.security_intent_count == 1
    assert metric.gross_turnover_notional_base.amount == expected_turnover


def test_analyze_async_accepted_example_is_complete_response():
    _guard_strict_validation()

    accepted = DpmAsyncAcceptedResponse.model_validate(ANALYZE_ASYNC_ACCEPTED_EXAMPLE["value"])

    assert accepted.operation_id.startswith("dop_")
    assert accepted.operation_type == "ANALYZE_SCENARIOS"
    assert accepted.status == "PENDING"
    assert accepted.status_url == f"/api/v1/rebalance/operations/{accepted.operation_id}"
    assert accepted.execute_url == f"/api/v1/rebalance/operations/{accepted.operation_id}/execute"


def test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts():
    _guard_strict_validation()
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    analyze_async = openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]
    assert analyze_async["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchExecutionRequestEnvelope"
    )
    assert analyze_async["responses"]["202"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncAcceptedResponse")
    assert "X-Correlation-Id" in analyze_async["responses"]["202"]["headers"]
    assert (
        analyze_async["responses"]["409"]["content"]["application/json"]["examples"][
            "correlation_conflict"
        ]["value"]["detail"]
        == "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"
    )
    assert (
        "Use this route when the caller needs polling-based orchestration"
        in analyze_async["description"]
    )
    header_names = {param["name"] for param in analyze_async["parameters"]}
    assert "x-correlation-id" in header_names
    assert "x-policy-pack-id" in header_names
    assert "x-tenant-policy-pack-id" in header_names
    assert "x-tenant-id" in header_names

    simulate = openapi["paths"]["/api/v1/rebalance/simulate"]["post"]
    assert simulate["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RebalanceExecutionRequestEnvelope"
    )
    assert simulate["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RebalanceResult"
    )
    assert "Do not use it for advisor-led proposal workflows" in simulate["description"]
    assert (
        "Reusing an idempotency key with a different canonical request hash returns `409`"
        in (simulate["description"])
    )
    simulate_params = {param["name"] for param in simulate["parameters"]}
    assert {
        "idempotency-key",
        "x-correlation-id",
        "x-policy-pack-id",
        "x-tenant-policy-pack-id",
        "x-tenant-id",
    }.issubset(simulate_params)

    analyze = openapi["paths"]["/api/v1/rebalance/analyze"]["post"]
    assert analyze["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchExecutionRequestEnvelope"
    )
    assert analyze["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchRebalanceResult"
    )
    assert (
        "Use this synchronous route when the caller needs immediate results"
        in analyze["description"]
    )
    analyze_params = {param["name"] for param in analyze["parameters"]}
    assert {
        "x-correlation-id",
        "x-policy-pack-id",
        "x-tenant-policy-pack-id",
        "x-tenant-id",
    }.issubset(analyze_params)
    analyze_examples = analyze["responses"]["200"]["content"]["application/json"]["examples"]
    assert "batch_result" in analyze_examples
    analyze_value = analyze_examples["batch_result"]["value"]
    assert "baseline" in analyze_value["results"]
    assert "baseline" in analyze_value["comparison_metrics"]
    assert "invalid_case" in analyze_value["failed_scenarios"]
    assert "PARTIAL_BATCH_FAILURE" in analyze_value["warnings"]

    health_paths = {
        "/health": "minimal service health",
        "/health/live": "process liveness without touching persistence dependencies",
        "/health/ready": "production profile",
    }
    for path, description_fragment in health_paths.items():
        operation = openapi["paths"][path]["get"]
        assert operation["tags"] == ["Health"]
        assert description_fragment in operation["description"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/HealthStatusResponse")
        assert operation["responses"]["200"]["description"] in {
            "Health probe succeeded.",
            "Readiness probe succeeded.",
        }
        assert "requestBody" not in operation

    assert openapi["paths"]["/health/ready"]["get"]["responses"]["500"]["description"] == (
        "Readiness guardrails failed, including production persistence profile or migration "
        "cutover checks."
    )

    effective_policy = openapi["paths"]["/api/v1/rebalance/policies/effective"]["get"]
    assert "requestBody" not in effective_policy
    assert effective_policy["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmEffectivePolicyPackResolution")
    assert "precedence" in effective_policy["description"]
    assert "X-Policy-Pack-Id" in effective_policy["description"]
    assert "X-Tenant-Policy-Pack-Id" in effective_policy["description"]
    assert "X-Tenant-Id" in effective_policy["description"]
    assert "before invoking rebalance execution" in effective_policy["description"]
    assert "unsupported query parameters are rejected" in effective_policy["description"]
    assert effective_policy["responses"]["200"]["description"] == (
        "Effective policy-pack selection and resolution source."
    )
    assert effective_policy["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    policy_params = {param["name"] for param in effective_policy["parameters"]}
    assert "x-policy-pack-id" in policy_params
    assert "x-tenant-policy-pack-id" in policy_params
    assert "x-tenant-id" in policy_params

    policy_catalog = openapi["paths"]["/api/v1/rebalance/policies/catalog"]["get"]
    assert "requestBody" not in policy_catalog
    assert policy_catalog["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackCatalogResponse")
    assert "PostgreSQL policy-pack repository" in policy_catalog["description"]
    assert "selected policy pack is present" in policy_catalog["description"]
    assert "unsupported query parameters are rejected" in policy_catalog["description"]
    assert policy_catalog["responses"]["200"]["description"] == (
        "Policy-pack catalog with effective selection context."
    )
    assert policy_catalog["responses"]["503"]["description"] == (
        "Policy-pack repository is unavailable or not configured."
    )
    assert policy_catalog["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    policy_catalog_params = {param["name"] for param in policy_catalog["parameters"]}
    assert "x-policy-pack-id" in policy_catalog_params
    assert "x-tenant-policy-pack-id" in policy_catalog_params
    assert "x-tenant-id" in policy_catalog_params

    policy_catalog_get_one = openapi["paths"][
        "/api/v1/rebalance/policies/catalog/{policy_pack_id}"
    ]["get"]
    assert "requestBody" not in policy_catalog_get_one
    assert policy_catalog_get_one["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackDefinition")
    assert (
        "turnover, tax, settlement, constraint, workflow, and idempotency controls"
        in (policy_catalog_get_one["description"])
    )
    assert "unsupported query parameters are rejected" in policy_catalog_get_one["description"]
    assert policy_catalog_get_one["responses"]["404"]["description"] == (
        "Policy-pack identifier was not found."
    )
    assert policy_catalog_get_one["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    assert policy_catalog_get_one["responses"]["503"]["description"] == (
        "Policy-pack repository is unavailable or not configured."
    )

    policy_catalog_upsert = openapi["paths"]["/api/v1/rebalance/policies/catalog/{policy_pack_id}"][
        "put"
    ]
    assert policy_catalog_upsert["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackUpsertRequest")
    assert policy_catalog_upsert["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackMutationResponse")
    assert "operator/admin control-plane endpoint" in policy_catalog_upsert["description"]
    assert "DPM_POLICY_PACK_ADMIN_APIS_ENABLED=true" in policy_catalog_upsert["description"]
    assert "path identifier is authoritative" in policy_catalog_upsert["description"]
    assert policy_catalog_upsert["responses"]["404"]["description"] == (
        "Policy-pack admin APIs are disabled for this runtime."
    )
    assert policy_catalog_upsert["responses"]["422"]["description"] == (
        "Request body validation failed or unsupported query parameters were supplied."
    )
    assert policy_catalog_upsert["responses"]["503"]["description"] == (
        "Policy-pack repository is unavailable or not configured."
    )

    policy_catalog_delete = openapi["paths"]["/api/v1/rebalance/policies/catalog/{policy_pack_id}"][
        "delete"
    ]
    assert "requestBody" not in policy_catalog_delete
    assert "204" in policy_catalog_delete["responses"]
    assert "operator/admin control-plane endpoint" in policy_catalog_delete["description"]
    assert "obsolete mandate policy packs" in policy_catalog_delete["description"]
    assert "advisory proposal lifecycle workflows" in policy_catalog_delete["description"]
    assert policy_catalog_delete["responses"]["404"]["description"] == (
        "Policy-pack admin APIs are disabled or the policy pack was not found."
    )
    assert policy_catalog_delete["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    assert policy_catalog_delete["responses"]["503"]["description"] == (
        "Policy-pack repository is unavailable or not configured."
    )

    list_operations = openapi["paths"]["/api/v1/rebalance/operations"]["get"]
    assert list_operations["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncOperationListResponse")
    expected_params = {
        "created_from",
        "created_to",
        "operation_type",
        "status_filter",
        "correlation_id",
        "limit",
        "cursor",
    }
    actual_params = {param["name"] for param in list_operations["parameters"]}
    assert expected_params.issubset(actual_params)
    assert (
        "status_filter` for operation status filtering; unsupported aliases are rejected"
        in (list_operations["description"])
    )
    assert "bounded page of operations" in list_operations["description"]
    for parameter in list_operations["parameters"]:
        if parameter["name"] in expected_params:
            assert parameter["description"]
            assert parameter["schema"].get("examples") or parameter["schema"].get("type")
    assert (
        "ordered by newest creation timestamp" in list_operations["responses"]["200"]["description"]
    )
    assert "422" in list_operations["responses"]

    get_operation = openapi["paths"]["/api/v1/rebalance/operations/{operation_id}"]["get"]
    assert "requestBody" not in get_operation
    assert get_operation["tags"] == ["lotus-manage Run Supportability"]
    assert get_operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncOperationStatusResponse")
    assert (
        "Terminal `SUCCEEDED` operations include the batch analysis result payload"
        in get_operation["description"]
    )
    assert "404" in get_operation["responses"]
    operation_id_param = next(
        parameter
        for parameter in get_operation["parameters"]
        if parameter["name"] == "operation_id"
    )
    assert operation_id_param["in"] == "path"
    assert operation_id_param["required"] is True
    assert operation_id_param["description"]

    get_operation_by_correlation = openapi["paths"][
        "/api/v1/rebalance/operations/by-correlation/{correlation_id}"
    ]["get"]
    assert "requestBody" not in get_operation_by_correlation
    assert get_operation_by_correlation["tags"] == ["lotus-manage Run Supportability"]
    assert get_operation_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmAsyncOperationStatusResponse")
    assert (
        "submitted `X-Correlation-Id` to `POST /api/v1/rebalance/analyze/async`"
        in get_operation_by_correlation["description"]
    )
    assert "404" in get_operation_by_correlation["responses"]
    correlation_id_param = next(
        parameter
        for parameter in get_operation_by_correlation["parameters"]
        if parameter["name"] == "correlation_id"
    )
    assert correlation_id_param["in"] == "path"
    assert correlation_id_param["required"] is True
    assert correlation_id_param["description"]

    execute_async = openapi["paths"]["/api/v1/rebalance/operations/{operation_id}/execute"]["post"]
    assert "requestBody" not in execute_async
    assert execute_async["tags"] == ["lotus-manage Run Supportability"]
    assert execute_async["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncOperationStatusResponse")
    assert "DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY" in execute_async["description"]
    assert "already terminal operations" in execute_async["description"]
    assert "SUCCEEDED" in execute_async["responses"]["200"]["description"]
    assert "FAILED" in execute_async["responses"]["200"]["description"]
    assert "404" in execute_async["responses"]
    assert "409" in execute_async["responses"]
    execute_operation_id_param = next(
        parameter
        for parameter in execute_async["parameters"]
        if parameter["name"] == "operation_id"
    )
    assert execute_operation_id_param["in"] == "path"
    assert execute_operation_id_param["required"] is True
    assert execute_operation_id_param["description"]

    run_artifact = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}/artifact"]["get"]
    assert run_artifact["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunArtifactResponse")
    assert "artifact payload only" in run_artifact["description"]
    assert "support-bundle endpoint" in run_artifact["description"]
    assert "unsupported query parameters are rejected" in run_artifact["description"]
    assert run_artifact["responses"]["200"]["description"] == (
        "Deterministic run artifact for audit and replay support."
    )
    assert "404" in run_artifact["responses"]
    assert run_artifact["responses"]["404"]["description"]
    assert run_artifact["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    list_runs = openapi["paths"]["/api/v1/rebalance/runs"]["get"]
    assert list_runs["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunListResponse"
    )
    expected_params = {
        "created_from",
        "created_to",
        "status_filter",
        "request_hash",
        "portfolio_id",
        "limit",
        "cursor",
    }
    actual_params = {param["name"] for param in list_runs["parameters"]}
    assert expected_params.issubset(actual_params)
    assert (
        "status_filter` for status filtering; unsupported aliases are rejected"
        in list_runs["description"]
    )
    assert "ordered by `created_at` descending" in list_runs["description"]
    assert "Pass the returned `next_cursor`" in list_runs["description"]
    assert list_runs["responses"]["200"]["description"] == (
        "Bounded page of run supportability records for investigation."
    )
    assert "422" in list_runs["responses"]

    run_by_request_hash = openapi["paths"]["/api/v1/rebalance/runs/by-request-hash/{request_hash}"][
        "get"
    ]
    assert run_by_request_hash["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunLookupResponse")
    assert "canonical request hash" in run_by_request_hash["description"]
    assert "URL-encode the request hash" in run_by_request_hash["description"]
    assert "does not accept query parameters" in run_by_request_hash["description"]
    assert run_by_request_hash["responses"]["200"]["description"] == (
        "Latest run supportability record mapped to the request hash."
    )
    assert "404" in run_by_request_hash["responses"]
    assert run_by_request_hash["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    run_by_id = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}"]["get"]
    assert run_by_id["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunLookupResponse"
    )
    assert "deterministic audit artifact" in run_by_id["description"]
    assert "support-bundle" in run_by_id["description"]
    assert "does not accept query parameters" in run_by_id["description"]
    assert run_by_id["responses"]["200"]["description"] == (
        "Persisted run supportability record and result payload."
    )
    assert "404" in run_by_id["responses"]
    assert run_by_id["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    run_by_correlation = openapi["paths"]["/api/v1/rebalance/runs/by-correlation/{correlation_id}"][
        "get"
    ]
    assert run_by_correlation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunLookupResponse")
    assert "X-Correlation-Id" in run_by_correlation["description"]
    assert "support-bundle routes" in run_by_correlation["description"]
    assert "does not accept query parameters" in run_by_correlation["description"]
    assert run_by_correlation["responses"]["200"]["description"] == (
        "Latest run supportability record mapped to the correlation id."
    )
    assert "404" in run_by_correlation["responses"]
    assert run_by_correlation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    idempotency_lookup = openapi["paths"]["/api/v1/rebalance/runs/idempotency/{idempotency_key}"][
        "get"
    ]
    assert idempotency_lookup["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunIdempotencyLookupResponse")
    assert "current idempotency-key mapping" in idempotency_lookup["description"]
    assert "append-only retry history" in idempotency_lookup["description"]
    assert "does not accept query parameters" in idempotency_lookup["description"]
    assert idempotency_lookup["responses"]["200"]["description"] == (
        "Current idempotency-key to run mapping."
    )
    assert "404" in idempotency_lookup["responses"]
    assert idempotency_lookup["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    supportability_summary = openapi["paths"]["/api/v1/rebalance/supportability/summary"]["get"]
    assert supportability_summary["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmSupportabilitySummaryResponse")
    assert "store-wide health and retention snapshot" in supportability_summary["description"]
    assert "does not accept ad hoc query filters" in supportability_summary["description"]
    assert "bounded action-register supportability state" in supportability_summary["description"]
    assert supportability_summary["responses"]["200"]["description"] == (
        "Store-wide supportability summary with counts, freshness, and bounded "
        "action-register posture."
    )
    assert supportability_summary["responses"]["404"]["description"] == (
        "Support APIs or supportability summary APIs are disabled."
    )
    assert "parameters" not in supportability_summary
    assert "422" in supportability_summary["responses"]
    assert supportability_summary["responses"]["503"]["description"] == (
        "Supportability store backend is unavailable or not configured."
    )

    support_bundle = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}/support-bundle"][
        "get"
    ]
    assert support_bundle["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunSupportBundleResponse")
    expected_params = {
        "rebalance_run_id",
        "include_artifact",
        "include_async_operation",
        "include_idempotency_history",
    }
    actual_params = {param["name"] for param in support_bundle["parameters"]}
    assert expected_params.issubset(actual_params)
    assert "unsupported query parameters are rejected" in support_bundle["description"]
    assert support_bundle["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    assert "404" in support_bundle["responses"]

    support_bundle_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/support-bundle"
    ]["get"]
    correlation_schema_ref = support_bundle_by_correlation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert correlation_schema_ref.endswith("/DpmRunSupportBundleResponse")
    expected_params = {
        "correlation_id",
        "include_artifact",
        "include_async_operation",
        "include_idempotency_history",
    }
    actual_params = {param["name"] for param in support_bundle_by_correlation["parameters"]}
    assert expected_params.issubset(actual_params)
    assert (
        "unsupported query parameters are rejected" in support_bundle_by_correlation["description"]
    )
    assert support_bundle_by_correlation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_decisions = openapi["paths"]["/api/v1/rebalance/workflow/decisions"]["get"]
    assert workflow_decisions["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmWorkflowDecisionListResponse")
    assert workflow_decisions["responses"]["200"]["description"] == (
        "Bounded page of workflow decisions ordered by newest decision timestamp."
    )
    assert "404" in workflow_decisions["responses"]
    assert workflow_decisions["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    assert (
        "Supported filters are `rebalance_run_id`, `action`, `actor_id`, `reason_code`, "
        "`decided_from`, `decided_to`, `limit`, and `cursor`" in workflow_decisions["description"]
    )
    expected_params = {
        "rebalance_run_id",
        "action",
        "actor_id",
        "reason_code",
        "decided_from",
        "decided_to",
        "limit",
        "cursor",
    }
    actual_params = {param["name"] for param in workflow_decisions["parameters"]}
    assert expected_params.issubset(actual_params)

    workflow_decisions_by_correlation = openapi["paths"][
        "/api/v1/rebalance/workflow/decisions/by-correlation/{correlation_id}"
    ]["get"]
    assert workflow_decisions_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")
    assert "run resolved by correlation id" in workflow_decisions_by_correlation["description"]
    assert "does not accept query parameters" in workflow_decisions_by_correlation["description"]
    assert workflow_decisions_by_correlation["responses"]["200"]["description"] == (
        "Append-only workflow decision history for the resolved run."
    )
    assert "404" in workflow_decisions_by_correlation["responses"]
    assert workflow_decisions_by_correlation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    support_bundle_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/support-bundle"
    ]["get"]
    assert support_bundle_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunSupportBundleResponse")
    expected_params = {
        "idempotency_key",
        "include_artifact",
        "include_async_operation",
        "include_idempotency_history",
    }
    actual_params = {param["name"] for param in support_bundle_by_idempotency["parameters"]}
    assert expected_params.issubset(actual_params)
    assert (
        "unsupported query parameters are rejected" in support_bundle_by_idempotency["description"]
    )
    assert support_bundle_by_idempotency["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    support_bundle_by_operation = openapi["paths"][
        "/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle"
    ]["get"]
    operation_schema_ref = support_bundle_by_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert operation_schema_ref.endswith("/DpmRunSupportBundleResponse")
    expected_params = {
        "operation_id",
        "include_artifact",
        "include_async_operation",
        "include_idempotency_history",
    }
    actual_params = {param["name"] for param in support_bundle_by_operation["parameters"]}
    assert expected_params.issubset(actual_params)
    assert "unsupported query parameters are rejected" in support_bundle_by_operation["description"]
    assert support_bundle_by_operation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    lineage = openapi["paths"]["/api/v1/rebalance/lineage/{entity_id}"]["get"]
    assert lineage["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmLineageResponse"
    )
    assert (
        "Supported filters are `edge_type`, `created_from`, `created_to`, `limit`, and `cursor`"
        in lineage["description"]
    )
    assert "Unknown entity ids return an empty page" in lineage["description"]
    assert "source or target" in lineage["description"]
    assert lineage["responses"]["422"]["description"] == (
        "Unsupported query parameters or invalid filter values were supplied."
    )
    expected_params = {"entity_id", "edge_type", "created_from", "created_to", "limit", "cursor"}
    actual_params = {param["name"] for param in lineage["parameters"]}
    assert expected_params.issubset(actual_params)
    edge_type_param = next(param for param in lineage["parameters"] if param["name"] == "edge_type")
    assert edge_type_param["description"]
    edge_type_schema = next(
        schema for schema in edge_type_param["schema"]["anyOf"] if "enum" in schema
    )
    assert set(edge_type_schema["enum"]) == {
        "CORRELATION_TO_RUN",
        "IDEMPOTENCY_TO_RUN",
        "OPERATION_TO_CORRELATION",
    }

    idempotency_history = openapi["paths"][
        "/api/v1/rebalance/idempotency/{idempotency_key}/history"
    ]["get"]
    assert idempotency_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunIdempotencyHistoryResponse")
    assert "DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true" in idempotency_history["description"]
    assert "does not accept query parameters" in idempotency_history["description"]
    assert "404" in idempotency_history["responses"]
    assert idempotency_history["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
    idempotency_key_param = next(
        parameter
        for parameter in idempotency_history["parameters"]
        if parameter["name"] == "idempotency_key"
    )
    assert idempotency_key_param["in"] == "path"
    assert idempotency_key_param["required"] is True
    assert idempotency_key_param["description"]

    workflow = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}/workflow"]["get"]
    assert workflow["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunWorkflowResponse"
    )
    assert "current review posture" in workflow["description"]
    assert "does not accept query parameters" in workflow["description"]
    assert workflow["responses"]["200"]["description"] == (
        "Current workflow state and latest reviewer decision for the run."
    )
    assert "404" in workflow["responses"]
    assert workflow["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow"
    ]["get"]
    assert workflow_by_correlation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")
    assert "submitted correlation id" in workflow_by_correlation["description"]
    assert "does not accept query parameters" in workflow_by_correlation["description"]
    assert workflow_by_correlation["responses"]["200"]["description"] == (
        "Current workflow state and latest reviewer decision for the run."
    )
    assert "404" in workflow_by_correlation["responses"]
    assert workflow_by_correlation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow"
    ]["get"]
    assert workflow_by_idempotency["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")
    assert "idempotency-key mapping" in workflow_by_idempotency["description"]
    assert "does not accept query parameters" in workflow_by_idempotency["description"]
    assert workflow_by_idempotency["responses"]["200"]["description"] == (
        "Current workflow state and latest reviewer decision for the run."
    )
    assert "404" in workflow_by_idempotency["responses"]
    assert workflow_by_idempotency["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_actions = openapi["paths"][
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow/actions"
    ]["post"]
    workflow_action_request_ref = workflow_actions["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert workflow_action_request_ref.endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")
    assert "Supply the reviewer action in the request body" in workflow_actions["description"]
    assert "does not accept query parameters" in workflow_actions["description"]
    assert workflow_actions["responses"]["200"]["description"] == (
        "Updated workflow state after applying the reviewer action."
    )
    assert "404" in workflow_actions["responses"]
    assert "409" in workflow_actions["responses"]
    assert workflow_actions["responses"]["422"]["description"] == (
        "Invalid action payload or unsupported query parameters were supplied."
    )

    workflow_actions_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_correlation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")
    assert "submitted correlation id" in workflow_actions_by_correlation["description"]
    assert "does not accept query parameters" in workflow_actions_by_correlation["description"]
    assert workflow_actions_by_correlation["responses"]["200"]["description"] == (
        "Updated workflow state after applying the reviewer action."
    )
    assert "404" in workflow_actions_by_correlation["responses"]
    assert "409" in workflow_actions_by_correlation["responses"]
    assert workflow_actions_by_correlation["responses"]["422"]["description"] == (
        "Invalid action payload or unsupported query parameters were supplied."
    )

    workflow_actions_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_idempotency["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")
    assert "idempotency-key mapping" in workflow_actions_by_idempotency["description"]
    assert "does not accept query parameters" in workflow_actions_by_idempotency["description"]
    assert workflow_actions_by_idempotency["responses"]["200"]["description"] == (
        "Updated workflow state after applying the reviewer action."
    )
    assert "404" in workflow_actions_by_idempotency["responses"]
    assert "409" in workflow_actions_by_idempotency["responses"]
    assert workflow_actions_by_idempotency["responses"]["422"]["description"] == (
        "Invalid action payload or unsupported query parameters were supplied."
    )

    workflow_history = openapi["paths"][
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow/history"
    ]["get"]
    assert workflow_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowHistoryResponse")
    assert "review reconstruction" in workflow_history["description"]
    assert "does not accept query parameters" in workflow_history["description"]
    assert workflow_history["responses"]["200"]["description"] == (
        "Append-only workflow decision history for the resolved run."
    )
    assert "404" in workflow_history["responses"]
    assert workflow_history["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_history_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/history"
    ]["get"]
    assert workflow_history_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")
    assert "submitted correlation id" in workflow_history_by_correlation["description"]
    assert "does not accept query parameters" in workflow_history_by_correlation["description"]
    assert workflow_history_by_correlation["responses"]["200"]["description"] == (
        "Append-only workflow decision history for the resolved run."
    )
    assert "404" in workflow_history_by_correlation["responses"]
    assert workflow_history_by_correlation["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )

    workflow_history_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/history"
    ]["get"]
    assert workflow_history_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")
    assert "idempotency-key mapping" in workflow_history_by_idempotency["description"]
    assert "does not accept query parameters" in workflow_history_by_idempotency["description"]
    assert workflow_history_by_idempotency["responses"]["200"]["description"] == (
        "Append-only workflow decision history for the resolved run."
    )
    assert "404" in workflow_history_by_idempotency["responses"]
    assert workflow_history_by_idempotency["responses"]["422"]["description"] == (
        "Unsupported query parameters were supplied."
    )
