"""
FILE: tests/api/test_api_rebalance.py
"""

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import src.api.routers.dpm_runs as dpm_runs_router
from src.api.main import DPM_IDEMPOTENCY_CACHE, app, get_db_session
from src.api.routers.dpm_runs import (
    get_dpm_run_support_service,
    reset_dpm_run_support_service_for_tests,
)
from src.core.dpm_runs import (
    DpmRunNotFoundError,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.models import RebalanceResult
from tests.shared.factories import valid_api_payload


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    yield
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def get_valid_payload():
    return valid_api_payload()


def test_simulate_endpoint_success(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["rebalance_run_id"].startswith("rr_")
    assert data["correlation_id"] == "corr-1"
    assert "before" in data
    assert "after_simulated" in data
    assert "rule_results" in data
    assert "diagnostics" in data
    assert data["gate_decision"]["gate"] in {
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "CLIENT_CONSENT_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    }


def test_simulate_missing_idempotency_key_422(client):
    """Verifies that Idempotency-Key is mandatory."""
    payload = get_valid_payload()
    response = client.post("/api/v1/rebalance/simulate", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["type"] == "missing" and "idempotency-key" in e["loc"] for e in errors)


def test_simulate_payload_validation_error_422(client):
    """Verifies that invalid payloads still return 422."""
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]
    headers = {"Idempotency-Key": "test-key-val"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_idempotency_replay_returns_same_payload(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-replay", "X-Correlation-Id": "corr-idem-replay"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_simulate_idempotency_conflict_returns_409(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-conflict"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert first.status_code == 200

    changed = get_valid_payload()
    changed["options"]["max_turnover_pct"] = "0.05"
    conflict = client.post("/api/v1/rebalance/simulate", json=changed, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"


def test_simulate_idempotency_replay_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-disabled"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["rebalance_run_id"] != second.json()["rebalance_run_id"]


def test_dpm_support_apis_lookup_by_run_correlation_and_idempotency(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-support-1", "X-Correlation-Id": "corr-support-1"}
    simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert simulate.status_code == 200
    body = simulate.json()

    by_run = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}")
    assert by_run.status_code == 200
    run_body = by_run.json()
    assert run_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert run_body["correlation_id"] == "corr-support-1"
    assert run_body["idempotency_key"] == "test-key-support-1"
    assert run_body["request_hash"].startswith("sha256:")
    assert run_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]

    by_correlation = client.get("/api/v1/rebalance/runs/by-correlation/corr-support-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["rebalance_run_id"] == body["rebalance_run_id"]

    by_request_hash = client.get(
        f"/api/v1/rebalance/runs/by-request-hash/{run_body['request_hash']}"
    )
    assert by_request_hash.status_code == 200
    assert by_request_hash.json()["rebalance_run_id"] == body["rebalance_run_id"]

    by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/test-key-support-1")
    assert by_idempotency.status_code == 200
    idem_body = by_idempotency.json()
    assert idem_body["idempotency_key"] == "test-key-support-1"
    assert idem_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert idem_body["request_hash"].startswith("sha256:")

    artifact = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact.status_code == 200
    artifact_body = artifact.json()
    assert artifact_body["artifact_id"].startswith("dra_")
    assert artifact_body["artifact_version"] == "1.0"
    assert artifact_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert artifact_body["correlation_id"] == "corr-support-1"
    assert artifact_body["idempotency_key"] == "test-key-support-1"
    assert artifact_body["portfolio_id"] == payload["portfolio_snapshot"]["portfolio_id"]
    assert artifact_body["status"] == body["status"]
    assert artifact_body["request_snapshot"]["request_hash"].startswith("sha256:")
    assert (
        artifact_body["request_snapshot"]["portfolio_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert artifact_body["evidence"]["hashes"]["request_hash"].startswith("sha256:")
    assert artifact_body["evidence"]["hashes"]["artifact_hash"].startswith("sha256:")
    assert artifact_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]

    artifact_again = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact_again.status_code == 200
    assert (
        artifact_again.json()["evidence"]["hashes"]["artifact_hash"]
        == artifact_body["evidence"]["hashes"]["artifact_hash"]
    )


@pytest.mark.parametrize(
    ("backend_value", "path_env_var"),
    [("SQLITE", "DPM_SUPPORTABILITY_SQLITE_PATH"), ("SQL", "DPM_SUPPORTABILITY_SQL_PATH")],
)
def test_dpm_supportability_sql_backend_selection(client, monkeypatch, backend_value, path_env_var):
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "dpm_supportability.sqlite")
        monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", backend_value)
        monkeypatch.setenv(path_env_var, sqlite_path)
        reset_dpm_run_support_service_for_tests()

        payload = get_valid_payload()
        headers = {
            "Idempotency-Key": "test-key-support-sqlite",
            "X-Correlation-Id": "corr-sqlite-1",
        }
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 503
        assert simulate.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"


def test_dpm_support_runs_list_filters_and_cursor(client):
    payload = get_valid_payload()
    first = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-list-1", "X-Correlation-Id": "corr-runs-list-1"},
    )
    assert first.status_code == 200
    first_body = first.json()

    payload["options"]["single_position_max_weight"] = "0.50"
    second = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-list-2", "X-Correlation-Id": "corr-runs-list-2"},
    )
    assert second.status_code == 200
    second_body = second.json()

    all_rows = client.get("/api/v1/rebalance/runs?limit=10")
    assert all_rows.status_code == 200
    all_body = all_rows.json()
    ids = [item["rebalance_run_id"] for item in all_body["items"]]
    assert second_body["rebalance_run_id"] in ids
    assert first_body["rebalance_run_id"] in ids

    ready_rows = client.get("/api/v1/rebalance/runs?status_filter=READY&limit=10")
    assert ready_rows.status_code == 200
    ready_body = ready_rows.json()
    assert len(ready_body["items"]) >= 1
    assert all(item["status"] == "READY" for item in ready_body["items"])

    portfolio_rows = client.get(
        f"/api/v1/rebalance/runs?portfolio_id={payload['portfolio_snapshot']['portfolio_id']}&limit=10"
    )
    assert portfolio_rows.status_code == 200
    assert len(portfolio_rows.json()["items"]) >= 2

    first_lookup = client.get(f"/api/v1/rebalance/runs/{first_body['rebalance_run_id']}")
    assert first_lookup.status_code == 200
    first_request_hash = first_lookup.json()["request_hash"]

    request_hash_rows = client.get(
        f"/api/v1/rebalance/runs?request_hash={first_request_hash}&limit=10"
    )
    assert request_hash_rows.status_code == 200
    request_hash_body = request_hash_rows.json()
    assert len(request_hash_body["items"]) == 1
    assert request_hash_body["items"][0]["rebalance_run_id"] == first_body["rebalance_run_id"]

    page_one = client.get("/api/v1/rebalance/runs?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None

    page_two = client.get(f"/api/v1/rebalance/runs?limit=1&cursor={page_one_body['next_cursor']}")
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert (
        page_two_body["items"][0]["rebalance_run_id"]
        != page_one_body["items"][0]["rebalance_run_id"]
    )


def test_dpm_support_runs_list_respects_retention_policy(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_RETENTION_DAYS", "1")
    reset_dpm_run_support_service_for_tests()

    payload = get_valid_payload()
    recent = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-retention-recent"},
    )
    assert recent.status_code == 200
    recent_body = recent.json()
    recent_result = RebalanceResult.model_validate(recent_body)

    old_result = recent_result.model_copy(
        update={
            "rebalance_run_id": "rr_runs_retention_old",
            "correlation_id": "corr-runs-retention-old",
        }
    )
    service = get_dpm_run_support_service()
    service.record_run(
        result=old_result,
        request_hash="sha256:runs-retention-old",
        portfolio_id=payload["portfolio_snapshot"]["portfolio_id"],
        idempotency_key="idem-runs-retention-old",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )

    listed = client.get(
        f"/api/v1/rebalance/runs?portfolio_id={payload['portfolio_snapshot']['portfolio_id']}&limit=20"
    )
    assert listed.status_code == 200
    rows = listed.json()["items"]
    assert any(row["rebalance_run_id"] == recent_body["rebalance_run_id"] for row in rows)
    assert all(row["rebalance_run_id"] != "rr_runs_retention_old" for row in rows)


def test_dpm_lineage_api_disabled_and_enabled(client, monkeypatch):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-lineage-1", "X-Correlation-Id": "corr-lineage-api-1"},
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    disabled = client.get("/api/v1/rebalance/lineage/corr-lineage-api-1")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_LINEAGE_APIS_DISABLED"

    monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    simulate_enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-lineage-2",
            "X-Correlation-Id": "corr-lineage-api-2",
        },
    )
    assert simulate_enabled.status_code == 200
    run_id_enabled = simulate_enabled.json()["rebalance_run_id"]

    by_correlation = client.get("/api/v1/rebalance/lineage/corr-lineage-api-2")
    assert by_correlation.status_code == 200
    correlation_edges = by_correlation.json()["edges"]
    assert len(correlation_edges) == 1
    assert correlation_edges[0]["edge_type"] == "CORRELATION_TO_RUN"
    assert correlation_edges[0]["target_entity_id"] == run_id_enabled

    by_idempotency = client.get("/api/v1/rebalance/lineage/test-key-lineage-2")
    assert by_idempotency.status_code == 200
    idempotency_edges = by_idempotency.json()["edges"]
    assert len(idempotency_edges) == 1
    assert idempotency_edges[0]["edge_type"] == "IDEMPOTENCY_TO_RUN"
    assert idempotency_edges[0]["target_entity_id"] == run_id_enabled

    by_run = client.get(f"/api/v1/rebalance/lineage/{run_id_enabled}")
    assert by_run.status_code == 200
    run_edges = by_run.json()["edges"]
    assert len(run_edges) == 2
    assert {edge["edge_type"] for edge in run_edges} == {"CORRELATION_TO_RUN", "IDEMPOTENCY_TO_RUN"}

    assert run_id != run_id_enabled


def test_dpm_idempotency_history_api_disabled_enabled_and_history_payload(client, monkeypatch):
    payload = get_valid_payload()
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    simulate_one = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-history-1", "X-Correlation-Id": "corr-history-1"},
    )
    assert simulate_one.status_code == 200
    run_one = simulate_one.json()["rebalance_run_id"]

    payload["options"]["single_position_max_weight"] = "0.50"
    simulate_two = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-history-1", "X-Correlation-Id": "corr-history-2"},
    )
    assert simulate_two.status_code == 200
    run_two = simulate_two.json()["rebalance_run_id"]
    assert run_one != run_two

    disabled = client.get("/api/v1/rebalance/idempotency/test-key-history-1/history")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED"

    monkeypatch.setenv("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", "true")
    history = client.get("/api/v1/rebalance/idempotency/test-key-history-1/history")
    assert history.status_code == 200
    body = history.json()
    assert body["idempotency_key"] == "test-key-history-1"
    assert len(body["history"]) == 2
    assert body["history"][0]["rebalance_run_id"] == run_one
    assert body["history"][0]["correlation_id"] == "corr-history-1"
    assert body["history"][0]["request_hash"].startswith("sha256:")
    assert body["history"][1]["rebalance_run_id"] == run_two
    assert body["history"][1]["correlation_id"] == "corr-history-2"
    assert body["history"][1]["request_hash"].startswith("sha256:")

    missing = client.get("/api/v1/rebalance/idempotency/test-key-history-missing/history")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"


def test_dpm_support_apis_not_found_and_disabled(client, monkeypatch):
    missing_run = client.get("/api/v1/rebalance/runs/rr_missing")
    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_correlation = client.get("/api/v1/rebalance/runs/by-correlation/corr-missing")
    assert missing_correlation.status_code == 404
    assert missing_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_request_hash = client.get("/api/v1/rebalance/runs/by-request-hash/sha256:missing")
    assert missing_request_hash.status_code == 404
    assert missing_request_hash.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_idem = client.get("/api/v1/rebalance/runs/idempotency/idem-missing")
    assert missing_idem.status_code == 404
    assert missing_idem.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    missing_artifact = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "false")
    disabled = client.get("/api/v1/rebalance/runs/rr_missing")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_SUPPORT_APIS_DISABLED"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "true")
    monkeypatch.setenv("DPM_ARTIFACTS_ENABLED", "false")
    artifact_disabled = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_disabled.status_code == 404
    assert artifact_disabled.json()["detail"] == "DPM_ARTIFACTS_DISABLED"

    monkeypatch.setenv("DPM_ARTIFACTS_ENABLED", "true")
    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "PERSISTED")
    artifact_mode_enabled = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_mode_enabled.status_code == 404
    assert artifact_mode_enabled.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "UNKNOWN_MODE")
    artifact_mode_fallback = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_mode_fallback.status_code == 404
    assert artifact_mode_fallback.json()["detail"] == "DPM_RUN_NOT_FOUND"


def test_dpm_support_repository_backend_init_errors_return_503(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    reset_dpm_run_support_service_for_tests()

    missing_dsn = client.get("/api/v1/rebalance/runs?limit=1")
    assert missing_dsn.status_code == 503
    assert missing_dsn.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"

    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/dpm",
    )
    monkeypatch.setattr(
        "src.api.routers.dpm_runs_config.PostgresDpmRunRepository",
        lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("boom")),
    )
    reset_dpm_run_support_service_for_tests()
    missing_driver = client.get("/api/v1/rebalance/runs?limit=1")
    assert missing_driver.status_code == 503
    assert missing_driver.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"


def test_dpm_async_operation_lookup_not_found_and_disabled(client, monkeypatch):
    missing = client.get("/api/v1/rebalance/operations/dop_missing")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    missing_by_corr = client.get("/api/v1/rebalance/operations/by-correlation/corr-missing")
    assert missing_by_corr.status_code == 404
    assert missing_by_corr.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")
    disabled = client.get("/api/v1/rebalance/operations/dop_missing")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_dpm_async_operation_lookup_by_id_and_correlation(client):
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-dpm-async-support-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    by_operation = client.get(f"/api/v1/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["operation_id"] == accepted.operation_id
    assert by_operation_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert by_operation_body["status"] == "PENDING"
    assert by_operation_body["is_executable"] is True
    assert by_operation_body["correlation_id"] == "corr-dpm-async-support-1"
    assert by_operation_body["result"] is None
    assert by_operation_body["error"] is None

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-dpm-async-support-1"
    )
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == accepted.operation_id


def test_dpm_async_operation_list_filters_and_cursor(client):
    service = get_dpm_run_support_service()
    one = service.submit_analyze_async(
        correlation_id="corr-dpm-ops-list-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    two = service.submit_analyze_async(
        correlation_id="corr-dpm-ops-list-2",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    pending = client.get("/api/v1/rebalance/operations?status_filter=PENDING&limit=10")
    assert pending.status_code == 200
    pending_body = pending.json()
    assert any(item["operation_id"] == one.operation_id for item in pending_body["items"])
    assert any(item["operation_id"] == two.operation_id for item in pending_body["items"])
    assert all(item["status"] == "PENDING" for item in pending_body["items"])

    by_correlation = client.get(
        "/api/v1/rebalance/operations?correlation_id=corr-dpm-ops-list-1&limit=10"
    )
    assert by_correlation.status_code == 200
    correlation_body = by_correlation.json()
    assert len(correlation_body["items"]) == 1
    assert correlation_body["items"][0]["operation_id"] == one.operation_id
    assert correlation_body["items"][0]["is_executable"] is True

    page_one = client.get("/api/v1/rebalance/operations?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None
    page_two = client.get(
        f"/api/v1/rebalance/operations?limit=1&cursor={page_one_body['next_cursor']}"
    )
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert page_one_body["items"][0]["operation_id"] != page_two_body["items"][0]["operation_id"]


def test_dpm_async_operation_ttl_expiry_by_id_and_correlation(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_TTL_SECONDS", "1")
    reset_dpm_run_support_service_for_tests()
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-dpm-async-ttl-expired",
        request_json={"scenarios": {"baseline": {"options": {}}}},
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )

    by_operation = client.get(f"/api/v1/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 404
    assert by_operation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-dpm-async-ttl-expired"
    )
    assert by_correlation.status_code == 404
    assert by_correlation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"


def test_dpm_supportability_summary_endpoint(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-summary-1",
            "X-Correlation-Id": "corr-support-summary-run-1",
        },
    )
    assert simulate.status_code == 200

    service = get_dpm_run_support_service()
    service.submit_analyze_async(
        correlation_id="corr-support-summary-op-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["store_backend"] == "POSTGRES"
    assert body["retention_days"] == 0
    assert body["run_count"] == 1
    assert body["operation_count"] == 1
    assert body["run_status_counts"] == {"READY": 1}
    assert body["operation_status_counts"] == {"PENDING": 1}
    assert body["workflow_decision_count"] == 0
    assert body["workflow_action_counts"] == {}
    assert body["workflow_reason_code_counts"] == {}
    assert body["lineage_edge_count"] == 3
    assert body["oldest_run_created_at"] is not None
    assert body["newest_run_created_at"] is not None
    assert body["oldest_operation_created_at"] is not None
    assert body["newest_operation_created_at"] is not None


def test_dpm_supportability_summary_endpoint_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED", "false")
    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED"


def test_dpm_supportability_summary_includes_workflow_aggregates(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-summary-workflow-1",
            "X-Correlation-Id": "corr-support-summary-workflow-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    action = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "actor_id": "reviewer_summary",
        },
        headers={"X-Correlation-Id": "corr-support-summary-workflow-action-1"},
    )
    assert action.status_code == 200

    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_decision_count"] == 1
    assert body["workflow_action_counts"] == {"APPROVE": 1}
    assert body["workflow_reason_code_counts"] == {"REVIEW_APPROVED": 1}


def test_dpm_run_support_bundle_endpoint(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-bundle-1",
            "X-Correlation-Id": "corr-support-bundle-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-support-bundle-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    response = client.get(f"/api/v1/rebalance/runs/{run_id}/support-bundle")
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["rebalance_run_id"] == run_id
    assert body["run"]["correlation_id"] == "corr-support-bundle-1"
    assert body["artifact"] is not None
    assert body["artifact"]["rebalance_run_id"] == run_id
    assert body["async_operation"] is not None
    assert body["async_operation"]["operation_id"] == accepted.operation_id
    assert body["workflow_history"]["run_id"] == run_id
    assert body["workflow_history"]["decisions"] == []
    assert body["lineage"]["entity_id"] == run_id
    assert len(body["lineage"]["edges"]) == 2
    assert body["idempotency_history"] is not None
    assert body["idempotency_history"]["idempotency_key"] == "test-key-support-bundle-1"
    assert len(body["idempotency_history"]["history"]) == 1

    compact = client.get(
        f"/api/v1/rebalance/runs/{run_id}/support-bundle"
        "?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
    )
    assert compact.status_code == 200
    compact_body = compact.json()
    assert compact_body["artifact"] is None
    assert compact_body["async_operation"] is None
    assert compact_body["idempotency_history"] is None


def test_dpm_run_support_bundle_endpoint_by_correlation_and_idempotency(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-bundle-2",
            "X-Correlation-Id": "corr-support-bundle-2",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-support-bundle-2/support-bundle"
    )
    assert by_correlation.status_code == 200
    by_correlation_body = by_correlation.json()
    assert by_correlation_body["run"]["rebalance_run_id"] == run_id
    assert by_correlation_body["run"]["correlation_id"] == "corr-support-bundle-2"

    by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-support-bundle-2/support-bundle"
    )
    assert by_idempotency.status_code == 200
    by_idempotency_body = by_idempotency.json()
    assert by_idempotency_body["run"]["rebalance_run_id"] == run_id
    assert by_idempotency_body["idempotency_history"] is not None
    assert (
        by_idempotency_body["idempotency_history"]["idempotency_key"] == "test-key-support-bundle-2"
    )

    missing_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr_missing/support-bundle"
    )
    assert missing_by_correlation.status_code == 404
    assert missing_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/idem_missing/support-bundle"
    )
    assert missing_by_idempotency.status_code == 404
    assert missing_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"


def test_dpm_run_support_bundle_endpoint_by_operation(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-bundle-3",
            "X-Correlation-Id": "corr-support-bundle-3",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-support-bundle-3",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    by_operation = client.get(
        f"/api/v1/rebalance/runs/by-operation/{accepted.operation_id}/support-bundle"
    )
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["run"]["rebalance_run_id"] == run_id
    assert by_operation_body["async_operation"] is not None
    assert by_operation_body["async_operation"]["operation_id"] == accepted.operation_id

    missing = client.get("/api/v1/rebalance/runs/by-operation/dop_missing/support-bundle")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"


def test_dpm_run_support_bundle_endpoint_disabled_and_not_found(client, monkeypatch):
    missing = client.get("/api/v1/rebalance/runs/rr_missing/support-bundle")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_SUPPORT_BUNDLE_APIS_ENABLED", "false")
    disabled = client.get("/api/v1/rebalance/runs/rr_missing/support-bundle")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_SUPPORT_BUNDLE_APIS_DISABLED"


def test_dpm_run_support_service_env_parsing_defaults(monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_TTL_SECONDS", "not-an-int")
    monkeypatch.setenv("DPM_SUPPORTABILITY_RETENTION_DAYS", "not-an-int")
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    monkeypatch.setenv("DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES", " , ")
    dpm_runs_router._REPOSITORY = None
    dpm_runs_router._SERVICE = None

    service = get_dpm_run_support_service()
    assert service._async_operation_ttl_seconds == 86400
    assert service._supportability_retention_days == 0
    assert service._workflow_enabled is True
    assert service._workflow_requires_review_for_statuses == {"PENDING_REVIEW"}


def test_dpm_workflow_router_not_found_mappings(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")

    by_run = client.get("/api/v1/rebalance/runs/rr_missing/workflow")
    assert by_run.status_code == 404
    assert by_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_run = client.get("/api/v1/rebalance/runs/rr_missing/workflow/history")
    assert history_by_run.status_code == 404
    assert history_by_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/history"
    )
    assert history_by_correlation.status_code == 404
    assert history_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    decisions_by_correlation = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr_missing"
    )
    assert decisions_by_correlation.status_code == 404
    assert decisions_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/history"
    )
    assert history_by_idempotency.status_code == 404
    assert history_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"


def test_dpm_workflow_action_router_exception_mappings(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = {
        "action": "APPROVE",
        "reason_code": "REVIEW_APPROVED",
        "actor_id": "reviewer_001",
    }

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action",
        side_effect=DpmRunNotFoundError("DPM_RUN_NOT_FOUND"),
    ):
        not_found = client.post("/api/v1/rebalance/runs/rr_missing/workflow/actions", json=payload)
    assert not_found.status_code == 404
    assert not_found.json()["detail"] == "DPM_RUN_NOT_FOUND"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled = client.post("/api/v1/rebalance/runs/rr_missing/workflow/actions", json=payload)
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_correlation",
        side_effect=DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION"),
    ):
        transition = client.post(
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
            json=payload,
        )
    assert transition.status_code == 409
    assert transition.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_correlation",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled_by_correlation = client.post(
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
            json=payload,
        )
    assert disabled_by_correlation.status_code == 404
    assert disabled_by_correlation.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    missing_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/actions",
        json=payload,
    )
    assert missing_idempotency.status_code == 404
    assert missing_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_idempotency",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled_idem = client.post(
            "/api/v1/rebalance/runs/idempotency/idem_any/workflow/actions",
            json=payload,
        )
    assert disabled_idem.status_code == 404
    assert disabled_idem.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_idempotency",
        side_effect=DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION"),
    ):
        transition_idem = client.post(
            "/api/v1/rebalance/runs/idempotency/idem_any/workflow/actions",
            json=payload,
        )
    assert transition_idem.status_code == 409
    assert transition_idem.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"


def test_simulate_generates_correlation_id_when_header_missing(client):
    payload = get_valid_payload()
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-corr-none"},
    )
    assert response.status_code == 200
    assert response.json()["correlation_id"].startswith("corr_")


def test_simulate_returns_503_when_idempotency_store_write_fails(client):
    payload = get_valid_payload()
    with patch("src.api.main.record_dpm_run_for_support", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-supportability-error"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"


def test_simulate_returns_503_when_idempotency_lookup_points_to_missing_run(client):
    payload = get_valid_payload()

    class _InconsistentIdempotencyService:
        def get_idempotency_lookup(self, *, idempotency_key):
            return SimpleNamespace(
                idempotency_key=idempotency_key,
                request_hash="sha256:matches",
                rebalance_run_id="rr_missing_for_idem",
            )

        def get_run(self, *, rebalance_run_id):
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")

    with (
        patch(
            "src.api.services.dpm_simulation_service.hash_canonical_payload",
            return_value="sha256:matches",
        ),
        patch(
            "src.api.services.dpm_simulation_service.get_dpm_run_support_service",
            return_value=_InconsistentIdempotencyService(),
        ),
    ):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-idem-store-inconsistent"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_IDEMPOTENCY_STORE_INCONSISTENT"


def test_simulate_ignores_supportability_persistence_errors_when_replay_disabled(
    client, monkeypatch
):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    payload = get_valid_payload()
    with patch("src.api.main.record_dpm_run_for_support", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-supportability-error-disabled"},
        )
    assert response.status_code == 200
    assert response.json()["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}


def test_simulate_rfc7807_domain_error_mapping(client):
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"

    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_REVIEW"


def test_get_db_session_dependency():
    """Verify DB dependency yields expected stub session value."""
    gen = get_db_session()
    assert inspect.isasyncgen(gen)

    async def consume():
        first = await gen.__anext__()
        assert first is None
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    asyncio.run(consume())


def test_simulate_blocked_logs_warning(client):
    """
    Force a 'BLOCKED' status (e.g. missing price) to verify the API logging branch.
    """
    payload = get_valid_payload()
    payload["market_data_snapshot"]["prices"] = []

    headers = {"Idempotency-Key": "test-key-block"}
    with patch("src.api.main.logger") as mock_logger:
        response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "BLOCKED"

        mock_logger.warning.assert_called()
        args, _ = mock_logger.warning.call_args
        assert "Run blocked" in args[0]


def test_simulate_missing_price_can_continue_when_non_blocking(client):
    payload = get_valid_payload()
    payload["market_data_snapshot"]["prices"] = []
    payload["options"]["block_on_missing_prices"] = False

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-missing-price-nonblock"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"READY", "PENDING_REVIEW"}
    assert "EQ_1" in body["diagnostics"]["data_quality"]["price_missing"]


def test_simulate_rejects_invalid_group_constraint_key(client):
    payload = get_valid_payload()
    payload["options"]["group_constraints"] = {"sectorTECH": {"max_weight": "0.2"}}

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-invalid-group-key"},
    )

    assert response.status_code == 422


def test_analyze_endpoint_success(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["snapshot_id"] = "ps_13"
    payload["market_data_snapshot"]["snapshot_id"] = "md_13"
    payload["scenarios"] = {
        "baseline": {"options": {}},
        "position_cap": {"options": {"single_position_max_weight": "0.5"}},
    }

    response = client.post(
        "/api/v1/rebalance/analyze",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["batch_run_id"].startswith("batch_")
    assert "run_at_utc" in body
    assert body["base_snapshot_ids"]["portfolio_snapshot_id"] == "ps_13"
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md_13"
    assert set(body["results"].keys()) == {"baseline", "position_cap"}
    assert set(body["comparison_metrics"].keys()) == {"baseline", "position_cap"}
    assert body["failed_scenarios"] == {}
    assert body["warnings"] == []

    for scenario_result in body["results"].values():
        assert scenario_result["lineage"]["request_hash"].startswith(body["batch_run_id"])
    assert body["results"]["baseline"]["correlation_id"] == "corr-batch-1:baseline"
    assert body["results"]["position_cap"]["correlation_id"] == "corr-batch-1:position_cap"
    for metrics in body["comparison_metrics"].values():
        assert metrics["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}
        assert isinstance(metrics["security_intent_count"], int)
        assert (
            metrics["gross_turnover_notional_base"]["currency"]
            == payload["portfolio_snapshot"]["base_currency"]
        )


def test_analyze_async_accept_and_lookup_succeeded(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-1"},
    )
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert accepted_body["status"] == "PENDING"
    assert accepted_body["correlation_id"] == "corr-batch-async-1"
    assert (
        accepted_body["execute_url"]
        == f"/api/v1/rebalance/operations/{accepted_body['operation_id']}/execute"
    )
    assert accepted.headers["X-Correlation-Id"] == "corr-batch-async-1"
    operation_id = accepted_body["operation_id"]

    by_operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["status"] == "SUCCEEDED"
    assert by_operation_body["is_executable"] is False
    assert by_operation_body["correlation_id"] == "corr-batch-async-1"
    assert by_operation_body["result"]["batch_run_id"].startswith("batch_")
    assert set(by_operation_body["result"]["results"].keys()) == {"baseline"}
    assert by_operation_body["error"] is None

    by_correlation = client.get("/api/v1/rebalance/operations/by-correlation/corr-batch-async-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "SUCCEEDED"


def test_analyze_async_generates_and_echoes_correlation_header_when_missing(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["correlation_id"].startswith("corr_")
    assert accepted.headers["X-Correlation-Id"] == accepted_body["correlation_id"]


def test_analyze_async_failure_is_captured_in_operation_status(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    with patch("src.api.main._execute_batch_analysis", side_effect=RuntimeError("boom")):
        accepted = client.post(
            "/api/v1/rebalance/analyze/async",
            json=payload,
            headers={"X-Correlation-Id": "corr-batch-async-failure"},
        )

    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "FAILED"
    assert operation_body["result"] is None
    assert operation_body["error"]["code"] == "RuntimeError"
    assert operation_body["error"]["message"] == "boom"


def test_analyze_async_disabled_returns_404(client, monkeypatch):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")

    response = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_dpm_policy_pack_header_is_accepted_without_behavior_change(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    payload = get_valid_payload()

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-policy-pack-header",
            "X-Policy-Pack-Id": "dpm_request_pack",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}


def test_dpm_policy_pack_catalog_overrides_turnover_option(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"dpm_request_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.01"},'
            '"tax_policy":{"enable_tax_awareness":true,"max_realized_capital_gains":"55"},'
            '"settlement_policy":{"enable_settlement_awareness":true,"settlement_horizon_days":3},'
            '"constraint_policy":{"single_position_max_weight":"0.25",'
            '"group_constraints":{"sector:TECH":{"max_weight":"0.20"}}},'
            '"workflow_policy":{"enable_workflow_gates":false,'
            '"workflow_requires_client_consent":true,'
            '"client_consent_already_obtained":true}}}'
        ),
    )

    payload = get_valid_payload()
    from src.core.dpm.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        simulate = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": "test-key-policy-pack-override-simulate",
                "X-Policy-Pack-Id": "dpm_request_pack",
            },
        )
        assert simulate.status_code == 200
        simulate_options = mock_run.call_args_list[0].kwargs["options"]
        assert simulate_options.max_turnover_pct == Decimal("0.01")
        assert simulate_options.enable_tax_awareness is True
        assert simulate_options.max_realized_capital_gains == Decimal("55")
        assert simulate_options.enable_settlement_awareness is True
        assert simulate_options.settlement_horizon_days == 3
        assert simulate_options.single_position_max_weight == Decimal("0.25")
        assert "sector:TECH" in simulate_options.group_constraints
        assert simulate_options.group_constraints["sector:TECH"].max_weight == Decimal("0.20")
        assert simulate_options.enable_workflow_gates is False
        assert simulate_options.workflow_requires_client_consent is True
        assert simulate_options.client_consent_already_obtained is True

        batch_payload = get_valid_payload()
        batch_payload.pop("options")
        batch_payload["scenarios"] = {"baseline": {"options": {}}}
        analyze = client.post(
            "/api/v1/rebalance/analyze",
            json=batch_payload,
            headers={"X-Policy-Pack-Id": "dpm_request_pack"},
        )
        assert analyze.status_code == 200
        analyze_options = mock_run.call_args_list[1].kwargs["options"]
        assert analyze_options.max_turnover_pct == Decimal("0.01")
        assert analyze_options.enable_tax_awareness is True
        assert analyze_options.max_realized_capital_gains == Decimal("55")
        assert analyze_options.enable_settlement_awareness is True
        assert analyze_options.settlement_horizon_days == 3
        assert analyze_options.single_position_max_weight == Decimal("0.25")
        assert "sector:TECH" in analyze_options.group_constraints
        assert analyze_options.group_constraints["sector:TECH"].max_weight == Decimal("0.20")
        assert analyze_options.enable_workflow_gates is False
        assert analyze_options.workflow_requires_client_consent is True
        assert analyze_options.client_consent_already_obtained is True


def test_effective_policy_pack_endpoint_resolution_precedence(client, monkeypatch):
    disabled = client.get(
        "/api/v1/rebalance/policies/effective", headers={"X-Policy-Pack-Id": "req_pack"}
    )
    assert disabled.status_code == 200
    assert disabled.json() == {
        "enabled": False,
        "selected_policy_pack_id": None,
        "source": "DISABLED",
    }

    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")

    request_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={
            "X-Policy-Pack-Id": "req_pack",
            "X-Tenant-Policy-Pack-Id": "tenant_pack",
        },
    )
    assert request_level.status_code == 200
    assert request_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "req_pack",
        "source": "REQUEST",
    }

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={"X-Tenant-Policy-Pack-Id": "tenant_pack"},
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_pack",
        "source": "TENANT_DEFAULT",
    }

    global_level = client.get("/api/v1/rebalance/policies/effective")
    assert global_level.status_code == 200
    assert global_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "global_pack",
        "source": "GLOBAL_DEFAULT",
    }


def test_effective_policy_pack_endpoint_uses_tenant_resolver_when_enabled(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={"X-Tenant-Id": "tenant_001"},
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_pack",
        "source": "TENANT_DEFAULT",
    }


def test_effective_policy_pack_explicit_tenant_header_precedence_over_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={
            "X-Tenant-Id": "tenant_001",
            "X-Tenant-Policy-Pack-Id": "tenant_header_pack",
        },
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_header_pack",
        "source": "TENANT_DEFAULT",
    }


def test_policy_pack_catalog_endpoint_returns_resolution_and_items(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"dpm_request_pack":{"version":"2","turnover_policy":{"max_turnover_pct":"0.03"}},'
            '"global_pack":{"version":"1"}}'
        ),
    )

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={
            "X-Policy-Pack-Id": "dpm_request_pack",
            "X-Tenant-Policy-Pack-Id": "tenant_pack",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["total"] == 2
    assert body["selected_policy_pack_id"] == "dpm_request_pack"
    assert body["selected_policy_pack_present"] is True
    assert body["selected_policy_pack_source"] == "REQUEST"
    assert [item["policy_pack_id"] for item in body["items"]] == ["dpm_request_pack", "global_pack"]
    assert body["items"][0]["version"] == "2"
    assert body["items"][0]["turnover_policy"]["max_turnover_pct"] == "0.03"


def test_policy_pack_catalog_endpoint_uses_tenant_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"tenant_pack":{"version":"1"}}',
    )

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={"X-Tenant-Id": "tenant_001"},
    )
    assert response.status_code == 200
    assert response.json()["selected_policy_pack_id"] == "tenant_pack"
    assert response.json()["selected_policy_pack_present"] is True
    assert response.json()["selected_policy_pack_source"] == "TENANT_DEFAULT"


def test_policy_pack_catalog_endpoint_selected_not_present(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_JSON", '{"global_pack":{"version":"1"}}')

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={"X-Policy-Pack-Id": "unknown_pack"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_policy_pack_id"] == "unknown_pack"
    assert body["selected_policy_pack_present"] is False
    assert body["selected_policy_pack_source"] == "REQUEST"


def test_dpm_policy_pack_catalog_overrides_options_using_tenant_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"tenant_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}}}',
    )
    payload = get_valid_payload()
    from src.core.dpm.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack-tenant",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        simulate = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": "test-key-policy-pack-tenant-override-simulate",
                "X-Tenant-Id": "tenant_001",
            },
        )
        assert simulate.status_code == 200
        simulate_options = mock_run.call_args.kwargs["options"]
        assert simulate_options.max_turnover_pct == Decimal("0.02")


def test_dpm_policy_pack_idempotency_override_disables_replay(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"dpm_request_pack":{"idempotency_policy":{"replay_enabled":false}}}',
    )
    payload = get_valid_payload()
    headers = {
        "Idempotency-Key": "test-key-policy-idem-disable",
        "X-Policy-Pack-Id": "dpm_request_pack",
    }

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["rebalance_run_id"] != second.json()["rebalance_run_id"]


def test_dpm_policy_pack_idempotency_override_enables_replay(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"dpm_request_pack":{"idempotency_policy":{"replay_enabled":true}}}',
    )
    payload = get_valid_payload()
    headers = {
        "Idempotency-Key": "test-key-policy-idem-enable",
        "X-Policy-Pack-Id": "dpm_request_pack",
    }

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_analyze_async_accept_only_mode_keeps_operation_pending(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-accept-only"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "PENDING"
    assert operation_body["is_executable"] is True
    assert operation_body["started_at"] is None
    assert operation_body["finished_at"] is None
    assert operation_body["result"] is None
    assert operation_body["error"] is None

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-batch-async-accept-only"
    )
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "PENDING"


def test_analyze_async_accept_only_mode_can_be_executed_manually(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-manual"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    executed = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert executed.status_code == 200
    executed_body = executed.json()
    assert executed_body["operation_id"] == operation_id
    assert executed_body["status"] == "SUCCEEDED"
    assert executed_body["is_executable"] is False
    assert executed_body["result"]["batch_run_id"].startswith("batch_")


def test_analyze_async_manual_execute_not_found_not_executable_and_disabled(client, monkeypatch):
    missing = client.post("/api/v1/rebalance/operations/dop_missing/execute")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    accepted = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    non_executable = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert non_executable.status_code == 409
    assert non_executable.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"

    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "false")
    disabled = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_ASYNC_MANUAL_EXECUTION_DISABLED"


def test_analyze_async_invalid_execution_mode_falls_back_to_inline(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "INVALID_MODE")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-inline-fallback"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    assert operation.json()["status"] == "SUCCEEDED"


def test_dpm_artifact_openapi_schema_has_descriptions_and_examples(client):
    openapi = client.get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["DpmRunArtifactResponse"]
    for property_name in [
        "artifact_id",
        "artifact_version",
        "rebalance_run_id",
        "correlation_id",
        "portfolio_id",
        "status",
        "request_snapshot",
        "before_summary",
        "after_summary",
        "order_intents",
        "rule_outcomes",
        "diagnostics",
        "result",
        "evidence",
    ]:
        prop = schema["properties"][property_name]
        assert prop.get("description")
        assert prop.get("examples") or prop.get("$ref")


def test_openapi_title_and_tag_grouping(client):
    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["title"] == "Private Banking Rebalance API"

    tags = {tag["name"] for tag in openapi.get("tags", [])}
    assert "lotus-manage Simulation" in tags
    assert "lotus-manage What-If Analysis" in tags
    assert "lotus-manage Run Supportability" in tags
    assert "Advisory Simulation" in tags
    assert "Advisory Proposal Lifecycle" in tags

    assert openapi["paths"]["/api/v1/rebalance/simulate"]["post"]["tags"] == [
        "lotus-manage Simulation"
    ]
    assert openapi["paths"]["/api/v1/rebalance/analyze"]["post"]["tags"] == [
        "lotus-manage What-If Analysis"
    ]
    assert openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]["tags"] == [
        "lotus-manage What-If Analysis"
    ]
    assert openapi["paths"]["/api/v1/rebalance/policies/effective"]["get"]["tags"] == [
        "lotus-manage Run Supportability"
    ]
    assert openapi["paths"]["/api/v1/rebalance/policies/catalog"]["get"]["tags"] == [
        "lotus-manage Run Supportability"
    ]
    assert openapi["paths"]["/api/v1/rebalance/proposals/simulate"]["post"]["tags"] == [
        "Advisory Simulation"
    ]


def test_openapi_async_analyze_documents_correlation_header(client):
    openapi = client.get("/openapi.json").json()
    simulate = openapi["paths"]["/api/v1/rebalance/simulate"]["post"]
    analyze = openapi["paths"]["/api/v1/rebalance/analyze"]["post"]
    analyze_async = openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]

    simulate_header_names = {parameter["name"] for parameter in simulate["parameters"]}
    analyze_header_names = {parameter["name"] for parameter in analyze["parameters"]}
    assert "x-policy-pack-id" in simulate_header_names
    assert "x-policy-pack-id" in analyze_header_names
    assert "x-tenant-id" in simulate_header_names
    assert "x-tenant-id" in analyze_header_names

    request_header = next(
        parameter
        for parameter in analyze_async["parameters"]
        if parameter["name"] == "x-correlation-id"
    )
    assert request_header["in"] == "header"
    assert request_header["description"]
    schema = request_header["schema"]
    if "type" in schema:
        assert schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in schema.get("anyOf", []))

    response_headers = analyze_async["responses"]["202"]["headers"]
    assert "X-Correlation-Id" in response_headers
    assert response_headers["X-Correlation-Id"]["description"]
    assert response_headers["X-Correlation-Id"]["schema"]["type"] == "string"

    policy_pack_header = next(
        parameter
        for parameter in analyze_async["parameters"]
        if parameter["name"] == "x-policy-pack-id"
    )
    assert policy_pack_header["in"] == "header"
    assert policy_pack_header["description"]
    policy_schema = policy_pack_header["schema"]
    if "type" in policy_schema:
        assert policy_schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in policy_schema.get("anyOf", []))

    tenant_header = next(
        parameter for parameter in analyze_async["parameters"] if parameter["name"] == "x-tenant-id"
    )
    assert tenant_header["in"] == "header"
    assert tenant_header["description"]
    tenant_schema = tenant_header["schema"]
    if "type" in tenant_schema:
        assert tenant_schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in tenant_schema.get("anyOf", []))

    accepted_schema = openapi["components"]["schemas"]["DpmAsyncAcceptedResponse"]
    assert "execute_url" in accepted_schema["properties"]
    assert accepted_schema["properties"]["execute_url"]["description"]
    assert accepted_schema["properties"]["execute_url"]["examples"]
    async_status_schema = openapi["components"]["schemas"]["DpmAsyncOperationStatusResponse"]
    assert "is_executable" in async_status_schema["properties"]
    assert async_status_schema["properties"]["is_executable"]["description"]
    assert async_status_schema["properties"]["is_executable"]["examples"]
    assert "/api/v1/rebalance/operations/{operation_id}/execute" in openapi["paths"]


def test_analyze_rejects_invalid_scenario_name(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"Invalid-Name": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_partial_failure_invalid_scenario_options(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "valid_case": {"options": {}},
        "invalid_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "valid_case" in body["results"]
    assert "invalid_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["invalid_case"].startswith("INVALID_OPTIONS:")
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_rejects_too_many_scenarios(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i}": {"options": {}} for i in range(21)}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_fallback_snapshot_ids_when_not_provided(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert (
        body["base_snapshot_ids"]["portfolio_snapshot_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md"


def test_analyze_scenarios_are_processed_in_sorted_name_order(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"z_case": {"options": {}}, "a_case": {"options": {}}}

    from src.core.dpm.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        response = client.post("/api/v1/rebalance/analyze", json=payload)
        assert response.status_code == 200
        call_hashes = [c.kwargs["request_hash"] for c in mock_run.call_args_list]
        assert call_hashes[0].endswith(":a_case")
        assert call_hashes[1].endswith(":z_case")


def test_analyze_runtime_error_is_isolated_to_failing_scenario(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"ok_case": {"options": {}}, "boom_case": {"options": {}}}

    from src.api.main import run_simulation as real_run

    def _side_effect(*args, **kwargs):
        if kwargs.get("request_hash", "").endswith(":boom_case"):
            raise RuntimeError("boom")
        return real_run(*args, **kwargs)

    with patch("src.api.main.run_simulation", side_effect=_side_effect):
        response = client.post("/api/v1/rebalance/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "ok_case" in body["results"]
    assert "boom_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["boom_case"] == "SCENARIO_EXECUTION_ERROR: RuntimeError"
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_comparison_metrics_turnover_matches_intents(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_1", "quantity": "100"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "0"}]
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "0.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]
    payload["scenarios"] = {"de_risk": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    metric = body["comparison_metrics"]["de_risk"]
    result = body["results"]["de_risk"]
    expected_turnover = sum(
        Decimal(intent["notional_base"]["amount"])
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    )
    assert Decimal(metric["gross_turnover_notional_base"]["amount"]) == expected_turnover


def test_analyze_accepts_max_scenarios_boundary(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i:02d}": {"options": {}} for i in range(20)}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 20
    assert len(body["comparison_metrics"]) == 20
    assert body["failed_scenarios"] == {}


def test_analyze_run_at_utc_is_timezone_aware_iso8601(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    run_at = datetime.fromisoformat(response.json()["run_at_utc"])
    assert run_at.tzinfo is not None


def test_analyze_results_and_metrics_keys_match_successful_scenarios_only(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "ok_case": {"options": {}},
        "bad_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body["results"].keys()) == {"ok_case"}
    assert set(body["comparison_metrics"].keys()) == {"ok_case"}
    assert set(body["failed_scenarios"].keys()) == {"bad_case"}


def test_analyze_mixed_outcomes_ready_pending_review_blocked(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["shelf_entries"] = [
        {
            "instrument_id": "EQ_1",
            "status": "APPROVED",
            "attributes": {"sector": "TECH"},
        }
    ]
    payload["scenarios"] = {
        "ready_case": {"options": {}},
        "pending_case": {"options": {"single_position_max_weight": "0.5"}},
        "blocked_case": {"options": {"group_constraints": {"sector:TECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    metrics = response.json()["comparison_metrics"]
    assert metrics["ready_case"]["status"] == "READY"
    assert metrics["pending_case"]["status"] == "PENDING_REVIEW"
    assert metrics["blocked_case"]["status"] == "BLOCKED"


def test_simulate_turnover_cap_emits_partial_rebalance_warning(client):
    payload = get_valid_payload()
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "100000"}]
    payload["market_data_snapshot"]["prices"] = [
        {"instrument_id": "A", "price": "100", "currency": "USD"},
        {"instrument_id": "B", "price": "100", "currency": "USD"},
        {"instrument_id": "C", "price": "100", "currency": "USD"},
    ]
    payload["model_portfolio"]["targets"] = [
        {"instrument_id": "A", "weight": "0.10"},
        {"instrument_id": "B", "weight": "0.10"},
        {"instrument_id": "C", "weight": "0.02"},
    ]
    payload["shelf_entries"] = [
        {"instrument_id": "A", "status": "APPROVED"},
        {"instrument_id": "B", "status": "APPROVED"},
        {"instrument_id": "C", "status": "APPROVED"},
    ]
    payload["options"]["max_turnover_pct"] = "0.15"

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-turnover-cap"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "PARTIAL_REBALANCE_TURNOVER_LIMIT" in body["diagnostics"]["warnings"]
    assert len(body["diagnostics"]["dropped_intents"]) == 1


def test_simulate_settlement_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_settlement_api",
            "base_currency": "USD",
            "positions": [{"instrument_id": "SLOW_FUND", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "SLOW_FUND", "price": "100", "currency": "USD"},
                {"instrument_id": "FAST_STOCK", "price": "100", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        "model_portfolio": {
            "targets": [
                {"instrument_id": "SLOW_FUND", "weight": "0.0"},
                {"instrument_id": "FAST_STOCK", "weight": "1.0"},
            ]
        },
        "shelf_entries": [
            {"instrument_id": "SLOW_FUND", "status": "APPROVED", "settlement_days": 3},
            {"instrument_id": "FAST_STOCK", "status": "APPROVED", "settlement_days": 1},
        ],
        "options": {"enable_settlement_awareness": False},
    }

    disabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-off"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "READY"

    payload["options"]["enable_settlement_awareness"] = True
    payload["options"]["settlement_horizon_days"] = 3

    enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert body["status"] == "BLOCKED"
    assert "OVERDRAFT_ON_T_PLUS_1" in body["diagnostics"]["warnings"]


def test_simulate_tax_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_tax_api",
            "base_currency": "USD",
            "positions": [
                {
                    "instrument_id": "ABC",
                    "quantity": "100",
                    "lots": [
                        {
                            "lot_id": "L_LOW",
                            "quantity": "50",
                            "unit_cost": {"amount": "10", "currency": "USD"},
                            "purchase_date": "2024-01-01",
                        },
                        {
                            "lot_id": "L_HIGH",
                            "quantity": "50",
                            "unit_cost": {"amount": "100", "currency": "USD"},
                            "purchase_date": "2024-02-01",
                        },
                    ],
                }
            ],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "ABC", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "ABC", "weight": "0.0"}]},
        "shelf_entries": [{"instrument_id": "ABC", "status": "APPROVED"}],
        "options": {
            "enable_tax_awareness": False,
            "max_realized_capital_gains": "100",
        },
    }

    disabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-off"},
    )
    assert disabled.status_code == 200
    assert Decimal(disabled.json()["intents"][0]["quantity"]) == Decimal("100")
    assert disabled.json()["tax_impact"] is None

    payload["options"]["enable_tax_awareness"] = True
    enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert Decimal(body["intents"][0]["quantity"]) < Decimal("100")
    assert "TAX_BUDGET_LIMIT_REACHED" in body["diagnostics"]["warnings"]
    assert body["tax_impact"]["budget_used"]["amount"] == "100"


def test_dpm_run_workflow_endpoints_happy_path_and_invalid_transition(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-1", "X-Correlation-Id": "corr-workflow-1"},
    )
    assert simulate.status_code == 200
    run = simulate.json()
    assert run["status"] == "PENDING_REVIEW"
    run_id = run["rebalance_run_id"]

    workflow = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow")
    assert workflow.status_code == 200
    workflow_body = workflow.json()
    assert workflow_body["run_id"] == run_id
    assert workflow_body["run_status"] == "PENDING_REVIEW"
    assert workflow_body["workflow_status"] == "PENDING_REVIEW"
    assert workflow_body["requires_review"] is True
    assert workflow_body["latest_decision"] is None

    workflow_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow"
    )
    assert workflow_by_correlation.status_code == 200
    assert workflow_by_correlation.json()["run_id"] == run_id
    workflow_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow"
    )
    assert workflow_by_idempotency.status_code == 200
    assert workflow_by_idempotency.json()["run_id"] == run_id

    request_changes = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "REQUIRES_ADVISOR_NOTE",
            "comment": "Please add rationale.",
            "actor_id": "reviewer_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-2"},
    )
    assert request_changes.status_code == 200
    request_changes_body = request_changes.json()
    assert request_changes_body["workflow_status"] == "PENDING_REVIEW"
    assert request_changes_body["latest_decision"]["action"] == "REQUEST_CHANGES"
    assert request_changes_body["latest_decision"]["correlation_id"] == "corr-workflow-2"

    request_changes_by_correlation = client.post(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "NEEDS_ONE_MORE_FIX",
            "comment": "Resolve minor note",
            "actor_id": "reviewer_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-2b"},
    )
    assert request_changes_by_correlation.status_code == 200
    assert (
        request_changes_by_correlation.json()["latest_decision"]["correlation_id"]
        == "corr-workflow-2b"
    )

    approved = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_2",
        },
        headers={"X-Correlation-Id": "corr-workflow-3"},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["workflow_status"] == "APPROVED"
    assert approved_body["latest_decision"]["action"] == "APPROVE"
    assert approved_body["latest_decision"]["actor_id"] == "reviewer_2"

    rejected_by_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow/actions",
        json={
            "action": "REJECT",
            "reason_code": "POLICY_BREACH_REJECTED",
            "comment": "Rejected for control reasons",
            "actor_id": "reviewer_3",
        },
        headers={"X-Correlation-Id": "corr-workflow-4"},
    )
    assert rejected_by_idempotency.status_code == 200
    rejected_body = rejected_by_idempotency.json()
    assert rejected_body["workflow_status"] == "REJECTED"
    assert rejected_body["latest_decision"]["action"] == "REJECT"
    assert rejected_body["latest_decision"]["correlation_id"] == "corr-workflow-4"

    history = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow/history")
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["run_id"] == run_id
    assert len(history_body["decisions"]) == 4
    assert history_body["decisions"][0]["action"] == "REQUEST_CHANGES"
    assert history_body["decisions"][1]["action"] == "REQUEST_CHANGES"
    assert history_body["decisions"][2]["action"] == "APPROVE"
    assert history_body["decisions"][3]["action"] == "REJECT"

    history_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow/history"
    )
    assert history_by_correlation.status_code == 200
    history_by_correlation_body = history_by_correlation.json()
    assert history_by_correlation_body["run_id"] == run_id
    assert len(history_by_correlation_body["decisions"]) == 4
    history_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow/history"
    )
    assert history_by_idempotency.status_code == 200
    history_by_idempotency_body = history_by_idempotency.json()
    assert history_by_idempotency_body["run_id"] == run_id
    assert len(history_by_idempotency_body["decisions"]) == 4

    workflow_decisions_by_correlation = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr-workflow-1"
    )
    assert workflow_decisions_by_correlation.status_code == 200
    workflow_decisions_by_correlation_body = workflow_decisions_by_correlation.json()
    assert workflow_decisions_by_correlation_body["run_id"] == run_id
    assert len(workflow_decisions_by_correlation_body["decisions"]) == 4

    invalid = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REJECT",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_2",
        },
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"


def test_dpm_workflow_decision_list_endpoint_filters_and_cursor(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-workflow-list-1",
            "X-Correlation-Id": "corr-workflow-list-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    action_one = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "REQUIRES_ADVISOR_NOTE",
            "comment": "Need additional detail",
            "actor_id": "reviewer_list_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-list-2"},
    )
    assert action_one.status_code == 200
    action_two = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_list_2",
        },
        headers={"X-Correlation-Id": "corr-workflow-list-3"},
    )
    assert action_two.status_code == 200

    all_rows = client.get("/api/v1/rebalance/workflow/decisions?limit=10")
    assert all_rows.status_code == 200
    all_body = all_rows.json()
    assert len(all_body["items"]) >= 2
    assert (
        all_body["items"][0]["decision_id"] == action_two.json()["latest_decision"]["decision_id"]
    )
    assert (
        all_body["items"][1]["decision_id"] == action_one.json()["latest_decision"]["decision_id"]
    )

    by_actor = client.get("/api/v1/rebalance/workflow/decisions?actor_id=reviewer_list_2&limit=10")
    assert by_actor.status_code == 200
    by_actor_body = by_actor.json()
    assert [item["actor_id"] for item in by_actor_body["items"]] == ["reviewer_list_2"]

    by_run = client.get(f"/api/v1/rebalance/workflow/decisions?rebalance_run_id={run_id}&limit=10")
    assert by_run.status_code == 200
    assert len(by_run.json()["items"]) == 2

    page_one = client.get("/api/v1/rebalance/workflow/decisions?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None

    page_two = client.get(
        f"/api/v1/rebalance/workflow/decisions?limit=1&cursor={page_one_body['next_cursor']}"
    )
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert page_two_body["items"][0]["decision_id"] != page_one_body["items"][0]["decision_id"]


def test_dpm_run_workflow_endpoints_disabled_and_not_required_behavior(client, monkeypatch):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-2"},
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    disabled = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"
    decision_lookup_disabled = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr-missing"
    )
    assert decision_lookup_disabled.status_code == 404
    assert decision_lookup_disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    simulate_ready = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-3"},
    )
    assert simulate_ready.status_code == 200
    ready_run_id = simulate_ready.json()["rebalance_run_id"]
    not_required = client.post(
        f"/api/v1/rebalance/runs/{ready_run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert not_required.status_code == 409
    assert not_required.json()["detail"] == "DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS"

    missing_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-missing/workflow"
    )
    assert missing_by_correlation.status_code == 404
    assert missing_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    missing_by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/idem-missing/workflow")
    assert missing_by_idempotency.status_code == 404
    assert missing_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"
    missing_action_by_correlation = client.post(
        "/api/v1/rebalance/runs/by-correlation/corr-missing/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert missing_action_by_correlation.status_code == 404
    assert missing_action_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    missing_action_by_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/idem-missing/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert missing_action_by_idempotency.status_code == 404
    assert missing_action_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "false")
    reset_dpm_run_support_service_for_tests()
    workflow_decision_list_disabled = client.get("/api/v1/rebalance/workflow/decisions?limit=10")
    assert workflow_decision_list_disabled.status_code == 404
    assert workflow_decision_list_disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"
