import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


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
    _assert_property_has_docs(workflow_policy_schema, "workflow_requires_client_consent")
    _assert_property_has_docs(workflow_policy_schema, "client_consent_already_obtained")

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


def test_integration_capabilities_paths_have_route_and_query_docs():
    _guard_strict_validation()
    openapi = app.openapi()

    integration_get = openapi["paths"]["/integration/capabilities"]["get"]
    platform_get = openapi["paths"]["/platform/capabilities"]["get"]

    assert "backend-governed rebalance feature and workflow capability posture" in integration_get[
        "description"
    ]
    assert "platform namespace" in platform_get["description"]
    assert "canonical snake_case query parameters `consumer_system` and `tenant_id`" in (
        integration_get["description"]
    )
    assert "canonical snake_case query parameters `consumer_system` and `tenant_id`" in (
        platform_get["description"]
    )

    integration_params = {param["name"]: param for param in integration_get["parameters"]}
    assert integration_params["consumer_system"]["schema"]["default"] == "lotus-gateway"
    assert integration_params["tenant_id"]["schema"]["default"] == "default"
    assert "canonical snake_case query parameter `consumer_system`" in integration_params[
        "consumer_system"
    ]["description"]
    assert "canonical snake_case query parameter `tenant_id`" in integration_params["tenant_id"][
        "description"
    ]


def test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts():
    _guard_strict_validation()
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    analyze_async = openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]
    assert analyze_async["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchRebalanceRequest"
    )
    assert analyze_async["responses"]["202"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncAcceptedResponse")
    assert "X-Correlation-Id" in analyze_async["responses"]["202"]["headers"]
    header_names = {param["name"] for param in analyze_async["parameters"]}
    assert "x-correlation-id" in header_names
    assert "x-policy-pack-id" in header_names
    assert "x-tenant-id" in header_names

    simulate = openapi["paths"]["/api/v1/rebalance/simulate"]["post"]
    assert simulate["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RebalanceRequest"
    )
    assert simulate["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RebalanceResult"
    )

    analyze = openapi["paths"]["/api/v1/rebalance/analyze"]["post"]
    assert analyze["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchRebalanceRequest"
    )
    assert analyze["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchRebalanceResult"
    )

    effective_policy = openapi["paths"]["/api/v1/rebalance/policies/effective"]["get"]
    assert "requestBody" not in effective_policy
    assert effective_policy["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmEffectivePolicyPackResolution")
    assert "Supply resolution context via the documented headers" in effective_policy["description"]
    assert "422" in effective_policy["responses"]
    policy_params = {param["name"] for param in effective_policy["parameters"]}
    assert "x-policy-pack-id" in policy_params
    assert "x-tenant-policy-pack-id" in policy_params
    assert "x-tenant-id" in policy_params

    policy_catalog = openapi["paths"]["/api/v1/rebalance/policies/catalog"]["get"]
    assert "requestBody" not in policy_catalog
    assert policy_catalog["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackCatalogResponse")
    assert "Supply resolution context via the documented headers" in policy_catalog["description"]
    assert "422" in policy_catalog["responses"]
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

    policy_catalog_upsert = openapi["paths"]["/api/v1/rebalance/policies/catalog/{policy_pack_id}"][
        "put"
    ]
    assert policy_catalog_upsert["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackUpsertRequest")
    assert policy_catalog_upsert["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmPolicyPackMutationResponse")

    policy_catalog_delete = openapi["paths"]["/api/v1/rebalance/policies/catalog/{policy_pack_id}"][
        "delete"
    ]
    assert "requestBody" not in policy_catalog_delete
    assert "204" in policy_catalog_delete["responses"]

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
    assert "status_filter` for operation status filtering; unsupported aliases are rejected" in (
        list_operations["description"]
    )
    assert "422" in list_operations["responses"]

    execute_async = openapi["paths"]["/api/v1/rebalance/operations/{operation_id}/execute"]["post"]
    assert "requestBody" not in execute_async
    assert execute_async["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncOperationStatusResponse")

    run_artifact = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}/artifact"]["get"]
    assert run_artifact["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunArtifactResponse")
    assert "404" in run_artifact["responses"]
    assert run_artifact["responses"]["404"]["description"]

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
    assert "status_filter` for status filtering; unsupported aliases are rejected" in list_runs[
        "description"
    ]
    assert "422" in list_runs["responses"]

    run_by_request_hash = openapi["paths"]["/api/v1/rebalance/runs/by-request-hash/{request_hash}"][
        "get"
    ]
    assert run_by_request_hash["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunLookupResponse")

    supportability_summary = openapi["paths"]["/api/v1/rebalance/supportability/summary"]["get"]
    assert supportability_summary["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmSupportabilitySummaryResponse")
    assert "store-wide health and retention snapshot" in supportability_summary["description"]
    assert "does not accept ad hoc query filters" in supportability_summary["description"]
    assert "parameters" not in supportability_summary
    assert "422" in supportability_summary["responses"]

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

    workflow_decisions = openapi["paths"]["/api/v1/rebalance/workflow/decisions"]["get"]
    assert workflow_decisions["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmWorkflowDecisionListResponse")
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

    lineage = openapi["paths"]["/api/v1/rebalance/lineage/{entity_id}"]["get"]
    assert lineage["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmLineageResponse"
    )

    idempotency_history = openapi["paths"][
        "/api/v1/rebalance/idempotency/{idempotency_key}/history"
    ]["get"]
    assert idempotency_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunIdempotencyHistoryResponse")

    workflow = openapi["paths"]["/api/v1/rebalance/runs/{rebalance_run_id}/workflow"]["get"]
    assert workflow["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunWorkflowResponse"
    )

    workflow_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow"
    ]["get"]
    assert workflow_by_correlation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")

    workflow_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow"
    ]["get"]
    assert workflow_by_idempotency["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")

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

    workflow_actions_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_correlation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")

    workflow_actions_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_idempotency["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")

    workflow_history = openapi["paths"][
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow/history"
    ]["get"]
    assert workflow_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowHistoryResponse")

    workflow_history_by_correlation = openapi["paths"][
        "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/history"
    ]["get"]
    assert workflow_history_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")

    workflow_history_by_idempotency = openapi["paths"][
        "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/history"
    ]["get"]
    assert workflow_history_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")
