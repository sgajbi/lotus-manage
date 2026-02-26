import pytest
from fastapi.testclient import TestClient

from src.api.main import DPM_IDEMPOTENCY_CACHE, app, get_db_session
from src.api.routers.dpm_runs import reset_dpm_run_support_service_for_tests
from tests.shared.factories import valid_api_payload


async def _override_get_db_session():
    yield None


_ORIGINAL_OVERRIDES: dict = {}


def setup_function() -> None:
    global _ORIGINAL_OVERRIDES
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = _override_get_db_session
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    _ORIGINAL_OVERRIDES = original_overrides


def teardown_function() -> None:
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = _ORIGINAL_OVERRIDES


def test_simulate_then_supportability_endpoints_roundtrip() -> None:
    payload = valid_api_payload()
    headers = {"Idempotency-Key": "integration-dpm-1", "X-Correlation-Id": "corr-integration-dpm-1"}

    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200
        run = simulate.json()

        by_run = client.get(f"/api/v1/rebalance/runs/{run['rebalance_run_id']}")
        by_correlation = client.get("/api/v1/rebalance/runs/by-correlation/corr-integration-dpm-1")
        by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/integration-dpm-1")
        artifact = client.get(f"/api/v1/rebalance/runs/{run['rebalance_run_id']}/artifact")
        summary = client.get("/api/v1/rebalance/supportability/summary")

    assert by_run.status_code == 200
    assert by_correlation.status_code == 200
    assert by_idempotency.status_code == 200
    assert artifact.status_code == 200
    assert summary.status_code == 200

    assert by_run.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert by_correlation.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert by_idempotency.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert artifact.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert summary.json()["run_count"] >= 1


def test_run_list_and_operation_lookup_integration_flow() -> None:
    payload = valid_api_payload()
    payload.pop("options", None)
    payload["scenarios"] = {"baseline": {"options": {}}}
    headers = {
        "Idempotency-Key": "integration-dpm-async-1",
        "X-Correlation-Id": "corr-integration-dpm-async-1",
    }

    with TestClient(app) as client:
        accepted = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
        by_correlation = client.get(
            "/api/v1/rebalance/operations/by-correlation/corr-integration-dpm-async-1"
        )
        listed = client.get("/api/v1/rebalance/operations?limit=10")

    assert operation.status_code == 200
    assert by_correlation.status_code == 200
    assert listed.status_code == 200
    assert operation.json()["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id
    assert len(listed.json()["items"]) >= 1


def test_supportability_summary_respects_status_filter() -> None:
    payload = valid_api_payload()
    headers = {
        "Idempotency-Key": "integration-dpm-summary-filter-1",
        "X-Correlation-Id": "corr-integration-dpm-summary-filter-1",
    }

    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200

        summary = client.get("/api/v1/rebalance/supportability/summary?status=SUCCESS")

    assert summary.status_code == 200
    body = summary.json()
    assert body["run_count"] >= 1


def test_supportability_summary_rejects_unknown_status_filter() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/rebalance/supportability/summary?status=NOT_A_REAL_STATUS")

    assert response.status_code == 200


def test_support_bundle_lookup_variants_roundtrip() -> None:
    payload = valid_api_payload()
    payload.pop("options", None)
    payload["scenarios"] = {"baseline": {"options": {}}}
    headers = {
        "Idempotency-Key": "integration-dpm-bundle-1",
        "X-Correlation-Id": "corr-integration-dpm-bundle-1",
    }

    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=valid_api_payload(), headers=headers)
        assert simulate.status_code == 200
        run_id = simulate.json()["rebalance_run_id"]

        accepted = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        by_run = client.get(f"/api/v1/rebalance/runs/{run_id}/support-bundle")
        by_correlation = client.get(
            "/api/v1/rebalance/runs/by-correlation/corr-integration-dpm-bundle-1/support-bundle"
        )
        by_idempotency = client.get(
            "/api/v1/rebalance/runs/idempotency/integration-dpm-bundle-1/support-bundle"
        )
        by_operation = client.get(f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle")

    assert by_run.status_code == 200
    assert by_correlation.status_code == 200
    assert by_idempotency.status_code == 200
    assert by_operation.status_code == 200
    assert by_run.json()["run"]["rebalance_run_id"] == run_id
    assert by_correlation.json()["run"]["rebalance_run_id"] == run_id
    assert by_idempotency.json()["run"]["rebalance_run_id"] == run_id


def test_idempotency_history_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = valid_api_payload()
    headers = {
        "Idempotency-Key": "integration-dpm-idem-history-1",
        "X-Correlation-Id": "corr-integration-dpm-idem-history-1",
    }

    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200

        monkeypatch.setenv("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", "false")
        history = client.get("/api/v1/rebalance/idempotency/integration-dpm-idem-history-1/history")

    assert history.status_code == 404
    assert history.json()["detail"] == "DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED"


def test_supportability_summary_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get("/api/v1/rebalance/supportability/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED"


def test_async_operations_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get("/api/v1/rebalance/operations")

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_support_bundle_optional_sections_can_be_disabled() -> None:
    payload = valid_api_payload()
    headers = {
        "Idempotency-Key": "integration-dpm-bundle-optional-1",
        "X-Correlation-Id": "corr-integration-dpm-bundle-optional-1",
    }
    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200
        run_id = simulate.json()["rebalance_run_id"]

        response = client.get(
            f"/api/v1/rebalance/runs/{run_id}/support-bundle"
            "?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["rebalance_run_id"] == run_id
    assert body["artifact"] is None
    assert body["async_operation"] is None
    assert body["idempotency_history"] is None


def test_health_endpoints_integration_contract() -> None:
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert live.json()["status"] == "live"
    assert ready.json()["status"] == "ready"


def test_integration_capabilities_contract_default_consumer() -> None:
    with TestClient(app) as client:
        response = client.get("/integration/capabilities?consumerSystem=BFF&tenantId=default")

    assert response.status_code == 200
    body = response.json()
    assert body["contractVersion"] == "v1"
    assert body["sourceService"] == "lotus-advise"
    assert "pas_ref" in body["supportedInputModes"]


def test_lineage_edge_filtering_roundtrip_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")
    payload = valid_api_payload()
    headers = {
        "Idempotency-Key": "integration-dpm-lineage-filter-1",
        "X-Correlation-Id": "corr-integration-dpm-lineage-filter-1",
    }
    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200
        run_id = simulate.json()["rebalance_run_id"]

        filtered = client.get(
            "/api/v1/rebalance/lineage/corr-integration-dpm-lineage-filter-1?edge_type=CORRELATION_TO_RUN"
        )

    assert filtered.status_code == 200
    edges = filtered.json()["edges"]
    assert len(edges) == 1
    assert edges[0]["edge_type"] == "CORRELATION_TO_RUN"
    assert edges[0]["target_entity_id"] == run_id


def test_workflow_actions_and_decision_list_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = valid_api_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    headers = {
        "Idempotency-Key": "integration-dpm-workflow-1",
        "X-Correlation-Id": "corr-integration-dpm-workflow-1",
    }
    with TestClient(app) as client:
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200
        run_id = simulate.json()["rebalance_run_id"]

        approve = client.post(
            f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
            json={
                "action": "APPROVE",
                "reason_code": "REVIEW_APPROVED",
                "comment": None,
                "actor_id": "integration_reviewer",
            },
            headers={"X-Correlation-Id": "corr-integration-dpm-workflow-approve"},
        )
        decisions = client.get("/api/v1/rebalance/workflow/decisions?action=APPROVE&limit=10")

    assert approve.status_code == 200
    assert decisions.status_code == 200
    assert approve.json()["workflow_status"] == "APPROVED"
    items = decisions.json()["items"]
    assert len(items) >= 1
    assert any(
        item["run_id"] == run_id and item["reason_code"] == "REVIEW_APPROVED" for item in items
    )


@pytest.mark.parametrize(
    ("env_name", "env_value", "path", "expected_detail"),
    [
        ("DPM_SUPPORT_APIS_ENABLED", "false", "/api/v1/rebalance/runs", "DPM_SUPPORT_APIS_DISABLED"),
        (
            "DPM_ASYNC_OPERATIONS_ENABLED",
            "false",
            "/api/v1/rebalance/operations",
            "DPM_ASYNC_OPERATIONS_DISABLED",
        ),
        (
            "DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED",
            "false",
            "/api/v1/rebalance/idempotency/idem_missing/history",
            "DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED",
        ),
        (
            "DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED",
            "false",
            "/api/v1/rebalance/supportability/summary",
            "DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED",
        ),
        (
            "DPM_SUPPORT_BUNDLE_APIS_ENABLED",
            "false",
            "/api/v1/rebalance/runs/rr_missing/support-bundle",
            "DPM_SUPPORT_BUNDLE_APIS_DISABLED",
        ),
        (
            "DPM_ARTIFACTS_ENABLED",
            "false",
            "/api/v1/rebalance/runs/rr_missing/artifact",
            "DPM_ARTIFACTS_DISABLED",
        ),
        (
            "DPM_LINEAGE_APIS_ENABLED",
            "false",
            "/api/v1/rebalance/lineage/corr_missing",
            "DPM_LINEAGE_APIS_DISABLED",
        ),
        ("DPM_WORKFLOW_ENABLED", "false", "/api/v1/rebalance/workflow/decisions", "DPM_WORKFLOW_DISABLED"),
    ],
)
def test_supportability_feature_flag_guards(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
    path: str,
    expected_detail: str,
) -> None:
    monkeypatch.setenv(env_name, env_value)
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/v1/rebalance/runs/rr_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/by-correlation/corr_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/by-request-hash/hash_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/idempotency/idem_missing", "DPM_IDEMPOTENCY_KEY_NOT_FOUND"),
        ("/api/v1/rebalance/runs/rr_missing/artifact", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/operations/op_missing", "DPM_ASYNC_OPERATION_NOT_FOUND"),
        (
            "/api/v1/rebalance/operations/by-correlation/corr_missing",
            "DPM_ASYNC_OPERATION_NOT_FOUND",
        ),
        ("/api/v1/rebalance/runs/rr_missing/support-bundle", "DPM_RUN_NOT_FOUND"),
        (
            "/api/v1/rebalance/runs/idempotency/idem_missing/support-bundle",
            "DPM_IDEMPOTENCY_KEY_NOT_FOUND",
        ),
        (
            "/api/v1/rebalance/runs/by-operation/op_missing/support-bundle",
            "DPM_ASYNC_OPERATION_NOT_FOUND",
        ),
    ],
)
def test_supportability_not_found_matrix(path: str, expected_detail: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/v1/rebalance/workflow/decisions/by-correlation/corr_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/rr_missing/workflow", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/by-correlation/corr_missing/workflow", "DPM_RUN_NOT_FOUND"),
        (
            "/api/v1/rebalance/runs/idempotency/idem_missing/workflow",
            "DPM_IDEMPOTENCY_KEY_NOT_FOUND",
        ),
        ("/api/v1/rebalance/runs/rr_missing/workflow/history", "DPM_RUN_NOT_FOUND"),
        (
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/history",
            "DPM_RUN_NOT_FOUND",
        ),
        (
            "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/history",
            "DPM_IDEMPOTENCY_KEY_NOT_FOUND",
        ),
    ],
)
def test_workflow_lookup_not_found_matrix(
    monkeypatch: pytest.MonkeyPatch, path: str, expected_detail: str
) -> None:
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/v1/rebalance/workflow/decisions", "DPM_WORKFLOW_DISABLED"),
        ("/api/v1/rebalance/workflow/decisions/by-correlation/corr_missing", "DPM_WORKFLOW_DISABLED"),
        ("/api/v1/rebalance/runs/rr_missing/workflow", "DPM_WORKFLOW_DISABLED"),
        ("/api/v1/rebalance/runs/by-correlation/corr_missing/workflow", "DPM_WORKFLOW_DISABLED"),
        ("/api/v1/rebalance/runs/idempotency/idem_missing/workflow", "DPM_WORKFLOW_DISABLED"),
        ("/api/v1/rebalance/runs/rr_missing/workflow/history", "DPM_WORKFLOW_DISABLED"),
        (
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/history",
            "DPM_WORKFLOW_DISABLED",
        ),
        (
            "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/history",
            "DPM_WORKFLOW_DISABLED",
        ),
    ],
)
def test_workflow_feature_flag_guard_matrix(
    monkeypatch: pytest.MonkeyPatch, path: str, expected_detail: str
) -> None:
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/v1/rebalance/runs/rr_missing/workflow/actions", "DPM_RUN_NOT_FOUND"),
        (
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
            "DPM_RUN_NOT_FOUND",
        ),
        (
            "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/actions",
            "DPM_IDEMPOTENCY_KEY_NOT_FOUND",
        ),
    ],
)
def test_workflow_action_not_found_matrix(
    monkeypatch: pytest.MonkeyPatch, path: str, expected_detail: str
) -> None:
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = {
        "action": "APPROVE",
        "reason_code": "REVIEW_APPROVED",
        "comment": None,
        "actor_id": "integration_reviewer",
    }
    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/rebalance/runs/rr_missing/workflow/actions",
        "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
        "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/actions",
    ],
)
def test_workflow_action_feature_flag_guard_matrix(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "false")
    payload = {
        "action": "APPROVE",
        "reason_code": "REVIEW_APPROVED",
        "comment": None,
        "actor_id": "integration_reviewer",
    }
    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_WORKFLOW_DISABLED"


