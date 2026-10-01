"""Registered HTTP and native PostgreSQL proof of async scenario-run membership."""

from __future__ import annotations

import multiprocessing
import os
import time
from contextlib import closing
from datetime import datetime, timezone

import pytest
from psycopg.errors import NotNullViolation
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.services import rebalance_run_support_repository
from src.api.services.rebalance_run_support_service import reset_dpm_run_support_service_for_tests
from src.core.rebalance_runs.models import DpmLineageEdgeRecord, DpmRunRecord
from src.core.rebalance_runs.repository import DpmRunRepositoryConflictError
from src.infrastructure.rebalance_runs.postgres import PostgresDpmRunRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.shared.factories import valid_api_payload


TENANT = "tenant-async-bundle"


async def _no_db_session():
    yield None


def _headers(correlation: str | None = None) -> dict[str, str]:
    headers = {"X-Tenant-Id": TENANT}
    if correlation is not None:
        headers["X-Correlation-Id"] = correlation
    return headers


def _batch(scenarios: dict[str, dict[str, object]]) -> dict[str, object]:
    payload = valid_api_payload()
    payload.pop("options")
    payload["scenarios"] = scenarios
    return {"input_mode": "stateless", "stateless_input": payload}


def _kill_after_first_persisted_scenario(dsn: str, operation_id: str) -> None:
    """Die after the real support-record call, before terminal operation publication."""
    import src.api.main as api_main

    os.environ["DPM_SUPPORTABILITY_POSTGRES_DSN"] = dsn
    reset_dpm_run_support_service_for_tests()
    original = api_main.record_dpm_run_for_support

    def persist_then_die(**kwargs):
        original(**kwargs)
        os._exit(0)

    api_main.record_dpm_run_for_support = persist_then_die
    app.dependency_overrides[get_db_session] = _no_db_session
    with TestClient(app) as client:
        client.post(
            f"/api/v1/rebalance/operations/{operation_id}/execute",
            headers=_headers(),
        )
    os._exit(2)


@pytest.fixture
def postgres_http(monkeypatch: pytest.MonkeyPatch):
    dsn = postgres_dsn_or_skip("async operation support-bundle PostgreSQL HTTP proof")
    repository = PostgresDpmRunRepository(dsn=dsn)
    with closing(repository._connect()) as connection:
        connection.execute(
            "TRUNCATE TABLE dpm_async_operations, dpm_lineage_edges, "
            "dpm_run_idempotency_history, dpm_run_idempotency, "
            "dpm_run_artifacts, dpm_runs CASCADE"
        )
        connection.commit()
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", dsn)
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_LEASE_SECONDS", "1")
    monkeypatch.setattr(
        rebalance_run_support_repository,
        "PostgresDpmRunRepository",
        PostgresDpmRunRepository,
    )
    reset_dpm_run_support_service_for_tests()
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = _no_db_session
    try:
        with TestClient(app) as client:
            yield client, dsn
    finally:
        reset_dpm_run_support_service_for_tests()
        app.dependency_overrides = original_overrides


def test_operation_bundle_reload_partial_failure_and_tenant_scope(postgres_http) -> None:
    client, _ = postgres_http
    correlation = "bundle-postgres-one"
    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=_batch(
            {
                "baseline": {"options": {}},
                "invalid": {"options": {"max_turnover_pct": "-1"}},
            }
        ),
        headers=_headers(correlation),
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    pending = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
        headers=_headers(),
    )
    assert pending.status_code == 200
    assert {key: value["status"] for key, value in pending.json()["scenarios"].items()} == {
        "baseline": "missing",
        "invalid": "missing",
    }
    executed = client.post(
        f"/api/v1/rebalance/operations/{operation_id}/execute", headers=_headers()
    )
    assert executed.status_code == 200
    assert executed.json()["status"] == "SUCCEEDED"
    reset_dpm_run_support_service_for_tests()
    response = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenarios"]["baseline"]["status"] == "succeeded"
    assert body["scenarios"]["invalid"]["status"] == "failed"
    assert body["scenarios"]["invalid"]["bundle"] is None
    run_id = body["scenarios"]["baseline"]["bundle"]["run"]["rebalance_run_id"]
    direct = client.get(f"/api/v1/rebalance/runs/{run_id}/support-bundle", headers=_headers())
    assert direct.status_code == 200
    assert direct.json()["async_operation"]["operation_id"] == operation_id
    foreign = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
        headers={"X-Tenant-Id": "foreign-tenant"},
    )
    assert foreign.status_code == 404
    assert (
        client.get(
            "/api/v1/rebalance/runs/by-operation/dop_unknown/support-bundle",
            headers=_headers(),
        ).status_code
        == 404
    )


def test_killed_attempt_remains_identified_but_not_authoritative(postgres_http) -> None:
    client, dsn = postgres_http
    correlation = "bundle-postgres-retry"
    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=_batch({"first": {"options": {}}, "second": {"options": {}}}),
        headers=_headers(correlation),
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    child = multiprocessing.get_context("spawn").Process(
        target=_kill_after_first_persisted_scenario, args=(dsn, operation_id)
    )
    child.start()
    child.join(timeout=30)
    if child.is_alive():
        child.terminate()
        child.join(timeout=5)
    assert child.exitcode == 0
    repository = PostgresDpmRunRepository(dsn=dsn)
    first_edges = [
        edge
        for edge in repository.list_lineage_edges(entity_id=operation_id)
        if edge.edge_type == "OPERATION_TO_RUN"
    ]
    assert len(first_edges) == 1
    assert first_edges[0].metadata_json == {"scenario_key": "first", "execution_attempt": 1}

    time.sleep(1.2)
    reset_dpm_run_support_service_for_tests()
    completed = client.post(
        f"/api/v1/rebalance/operations/{operation_id}/execute", headers=_headers()
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "SUCCEEDED"
    assert completed.json()["execution_attempt"] == 2
    reset_dpm_run_support_service_for_tests()
    response = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert {key: value["status"] for key, value in body["scenarios"].items()} == {
        "first": "succeeded",
        "second": "succeeded",
    }
    authoritative_ids = {
        value["bundle"]["run"]["rebalance_run_id"] for value in body["scenarios"].values()
    }
    assert len(authoritative_ids) == 2
    assert len(body["historical_runs"]) == 1
    abandoned = body["historical_runs"][0]
    assert abandoned["scenario_key"] == "first"
    assert abandoned["execution_attempt"] == 1
    assert abandoned["bundle"]["run"]["rebalance_run_id"] not in authoritative_ids
    assert abandoned["bundle"]["run"]["correlation_id"] == (f"{correlation}:attempt-1:first")
    assert body["scenarios"]["first"]["bundle"]["run"]["correlation_id"] == (
        f"{correlation}:attempt-2:first"
    )


def test_run_and_membership_are_one_postgres_transaction(postgres_http) -> None:
    _, dsn = postgres_http
    repository = PostgresDpmRunRepository(dsn=dsn)
    now = datetime.now(timezone.utc)
    run = DpmRunRecord(
        tenant_id=TENANT,
        rebalance_run_id="rr_membership_rollback",
        correlation_id="bundle-rollback:attempt-1:baseline",
        request_hash="batch-rollback:baseline",
        portfolio_id="pf-rollback",
        created_at=now,
        result_json={"rebalance_run_id": "rr_membership_rollback"},
    )
    invalid_edge = DpmLineageEdgeRecord.model_construct(
        tenant_id=TENANT,
        source_entity_id=None,
        edge_type="OPERATION_TO_RUN",
        target_entity_id=run.rebalance_run_id,
        created_at=now,
        metadata_json={"scenario_key": "baseline", "execution_attempt": 1},
    )
    with pytest.raises(ValueError, match="DPM_RUN_LINEAGE_SCOPE_MISMATCH"):
        repository.save_run_with_lineage(
            run=run,
            lineage_edges=[invalid_edge.model_copy(update={"tenant_id": "foreign-tenant"})],
        )
    assert repository.get_run(rebalance_run_id=run.rebalance_run_id) is None
    with pytest.raises(NotNullViolation):
        repository.save_run_with_lineage(run=run, lineage_edges=[invalid_edge])
    assert repository.get_run(rebalance_run_id=run.rebalance_run_id) is None

    valid_edge = invalid_edge.model_copy(update={"source_entity_id": "dop_membership_rollback"})
    repository.save_run_with_lineage(run=run, lineage_edges=[valid_edge])
    with pytest.raises(DpmRunRepositoryConflictError, match="DPM_RUN_ALREADY_EXISTS"):
        repository.save_run_with_lineage(
            run=run.model_copy(update={"result_json": {"tampered": True}}),
            lineage_edges=[valid_edge],
        )
    assert repository.get_run(rebalance_run_id=run.rebalance_run_id).result_json == (
        run.result_json
    )
    assert len(repository.list_lineage_edges(entity_id=run.rebalance_run_id)) == 1
