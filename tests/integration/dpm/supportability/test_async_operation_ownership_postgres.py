"""Native PostgreSQL and registered-HTTP ownership proof for #719."""

from __future__ import annotations

import multiprocessing
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Event, Lock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.services.rebalance_run_support_service import reset_dpm_run_support_service_for_tests
from src.core.rebalance_runs.models import DpmAsyncOperationRecord
from src.infrastructure import postgres_migrations
from src.infrastructure.rebalance_runs.postgres import PostgresDpmRunRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.shared.factories import valid_api_payload


TENANT_A = "tenant-async-owner-a"
TENANT_B = "tenant-async-owner-b"
_PROOF = "async operation execution ownership proof"


def _claim_in_process(
    dsn: str,
    operation_id: str,
    token: str,
    ready: object,
    start: object,
) -> tuple[str, int | None]:
    repository = PostgresDpmRunRepository(dsn=dsn)
    ready.set()
    start.wait(timeout=20)
    now = datetime.now(timezone.utc)
    claimed = repository.claim_operation_execution(
        tenant_id=TENANT_A,
        operation_id=operation_id,
        execution_token=token,
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )
    return token, claimed.execution_attempt if claimed else None


@pytest.fixture
def dsn() -> str:
    return postgres_dsn_or_skip(_PROOF)


@pytest.fixture(autouse=True)
def reset_operation_tables(dsn: str) -> None:
    repository = PostgresDpmRunRepository(dsn=dsn)
    with closing(repository._connect()) as connection:
        connection.execute(
            "TRUNCATE TABLE dpm_async_operations, dpm_lineage_edges, "
            "dpm_run_idempotency_history, dpm_run_idempotency, "
            "dpm_run_artifacts, dpm_runs CASCADE"
        )
        connection.commit()


def _pending(*, operation_id: str, correlation_id: str) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
        tenant_id=TENANT_A,
        operation_id=operation_id,
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=correlation_id,
        created_at=datetime.now(timezone.utc),
        request_json={"synthetic": "request"},
    )


def test_separate_processes_yield_one_execution_owner(dsn: str) -> None:
    operation_id = f"dop_process_{uuid.uuid4().hex}"
    PostgresDpmRunRepository(dsn=dsn).create_operation(
        _pending(operation_id=operation_id, correlation_id=f"corr-{uuid.uuid4().hex}")
    )
    tokens = [f"claim-{uuid.uuid4().hex}" for _ in range(4)]
    context = multiprocessing.get_context("spawn")
    with context.Manager() as manager:
        start = manager.Event()
        ready_events = [manager.Event() for _ in tokens]
        with ProcessPoolExecutor(max_workers=4, mp_context=context) as pool:
            futures = [
                pool.submit(
                    _claim_in_process,
                    dsn,
                    operation_id,
                    token,
                    ready,
                    start,
                )
                for token, ready in zip(tokens, ready_events, strict=True)
            ]
            assert all(ready.wait(timeout=20) for ready in ready_events)
            start.set()
            outcomes = [future.result(timeout=30) for future in futures]

    winners = [(token, attempt) for token, attempt in outcomes if attempt is not None]
    assert len(winners) == 1
    assert winners[0][1] == 1


def test_restart_reclaims_expired_lease_and_fences_stale_publication(dsn: str) -> None:
    operation_id = f"dop_recovery_{uuid.uuid4().hex}"
    correlation_id = f"corr-shared-{uuid.uuid4().hex}"
    repository = PostgresDpmRunRepository(dsn=dsn)
    repository.create_operation(_pending(operation_id=operation_id, correlation_id=correlation_id))
    now = datetime.now(timezone.utc)
    first = repository.claim_operation_execution(
        tenant_id=TENANT_A,
        operation_id=operation_id,
        execution_token="crashed-owner",
        claimed_at=now - timedelta(minutes=2),
        lease_expires_at=now - timedelta(minutes=1),
    )
    assert first is not None and first.execution_attempt == 1

    restarted = PostgresDpmRunRepository(dsn=dsn)
    second = restarted.claim_operation_execution(
        tenant_id=TENANT_A,
        operation_id=operation_id,
        execution_token="recovery-owner",
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )
    assert second is not None and second.execution_attempt == 2
    running, next_cursor = restarted.list_operations_for_tenant(
        tenant_id=TENANT_A,
        created_from=now - timedelta(minutes=5),
        created_to=now + timedelta(minutes=5),
        operation_type="ANALYZE_SCENARIOS",
        status="RUNNING",
        correlation_id=correlation_id,
        limit=10,
        cursor=None,
    )
    assert [operation.operation_id for operation in running] == [operation_id]
    assert next_cursor is None
    assert (
        restarted.publish_operation_success(
            tenant_id=TENANT_A,
            operation_id=operation_id,
            execution_token="crashed-owner",
            result_json={"authoritative": "stale"},
            finished_at=now,
        )
        is False
    )
    result = {"authoritative": "recovered", "gross_turnover_usd": "20000.00"}
    assert (
        restarted.publish_operation_success(
            tenant_id=TENANT_A,
            operation_id=operation_id,
            execution_token="recovery-owner",
            result_json=result,
            finished_at=now,
        )
        is True
    )
    assert (
        restarted.publish_operation_success(
            tenant_id=TENANT_A,
            operation_id=operation_id,
            execution_token="recovery-owner",
            result_json={"authoritative": "rewrite"},
            finished_at=now,
        )
        is False
    )
    stored = restarted.get_operation_for_tenant(
        tenant_id=TENANT_A,
        operation_id=operation_id,
    )
    assert stored is not None and stored.result_json == result
    assert (
        restarted.get_operation_for_tenant(
            tenant_id=TENANT_B,
            operation_id=operation_id,
        )
        is None
    )

    # Correlation identity is tenant scoped rather than globally reserved.
    restarted.create_operation(
        DpmAsyncOperationRecord(
            tenant_id=TENANT_B,
            operation_id=f"dop_tenant_b_{uuid.uuid4().hex}",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id=correlation_id,
            created_at=now,
            request_json={"tenant": "b"},
        )
    )
    tenant_a_operation = restarted.get_operation_by_correlation_for_tenant(
        tenant_id=TENANT_A,
        correlation_id=correlation_id,
    )
    assert tenant_a_operation is not None
    assert tenant_a_operation.operation_id == operation_id
    tenant_b_operation = restarted.get_operation_by_correlation_for_tenant(
        tenant_id=TENANT_B,
        correlation_id=correlation_id,
    )
    assert tenant_b_operation is not None
    assert tenant_b_operation.tenant_id == TENANT_B

    failed_operation_id = f"dop_failed_{uuid.uuid4().hex}"
    restarted.create_operation(
        _pending(operation_id=failed_operation_id, correlation_id=f"corr-{uuid.uuid4().hex}")
    )
    failed_claim = restarted.claim_operation_execution(
        tenant_id=TENANT_A,
        operation_id=failed_operation_id,
        execution_token="failure-owner",
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )
    assert failed_claim is not None
    assert restarted.publish_operation_failure(
        tenant_id=TENANT_A,
        operation_id=failed_operation_id,
        execution_token="failure-owner",
        error_json={"code": "UPSTREAM_TIMEOUT", "message": "timed out"},
        finished_at=now,
    )


def test_registered_http_competition_runs_one_financial_calculation(
    dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace
    from src.api.dependencies import get_rebalance_runtime

    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", dsn)
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    original_overrides = dict(app.dependency_overrides)

    async def override_db_session():
        yield None

    app.dependency_overrides[get_db_session] = override_db_session
    runtime = get_rebalance_runtime()
    real_run_simulation = runtime.run_simulation
    engine_started = Event()
    release_engine = Event()
    count_lock = Lock()
    engine_calls = 0

    def counted_run_simulation(*args, **kwargs):
        nonlocal engine_calls
        with count_lock:
            engine_calls += 1
        engine_started.set()
        assert release_engine.wait(timeout=10)
        return real_run_simulation(*args, **kwargs)

    app.dependency_overrides[get_rebalance_runtime] = lambda: replace(
        runtime, run_simulation=counted_run_simulation
    )
    payload = valid_api_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_SELL", "quantity": "100"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "0"}]
    payload["market_data_snapshot"]["prices"] = [
        {"instrument_id": "EQ_SELL", "price": "100", "currency": "USD"},
        {"instrument_id": "EQ_BUY", "price": "100", "currency": "USD"},
    ]
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_BUY", "weight": "1.0"}]
    payload["shelf_entries"] = [
        {"instrument_id": "EQ_SELL", "status": "APPROVED"},
        {"instrument_id": "EQ_BUY", "status": "APPROVED"},
    ]
    payload["scenarios"] = {"full_rotation": {"options": {}}}
    request_payload = {"input_mode": "stateless", "stateless_input": payload}
    headers = {
        "X-Tenant-Id": TENANT_A,
        "X-Correlation-Id": f"corr-http-{uuid.uuid4().hex}",
    }

    try:
        with TestClient(app) as client:
            accepted = client.post(
                "/api/v1/rebalance/analyze/async",
                json=request_payload,
                headers=headers,
            )
            assert accepted.status_code == 202, accepted.text
            operation_id = accepted.json()["operation_id"]
            execute_url = f"/api/v1/rebalance/operations/{operation_id}/execute"
            with ThreadPoolExecutor(max_workers=1) as pool:
                owner = pool.submit(client.post, execute_url, headers={"X-Tenant-Id": TENANT_A})
                assert engine_started.wait(timeout=10)
                competitor = client.post(execute_url, headers={"X-Tenant-Id": TENANT_A})
                assert competitor.status_code == 409
                assert competitor.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"
                release_engine.set()
                completed = owner.result(timeout=20)

            assert completed.status_code == 200
            assert engine_calls == 1
            status = client.get(
                execute_url.removesuffix("/execute"), headers={"X-Tenant-Id": TENANT_A}
            )
            assert status.status_code == 200
            body = status.json()
            assert body["status"] == "SUCCEEDED"
            assert body["execution_attempt"] == 1
            assert "execution_token" not in body
            result = body["result"]
            metric = result["comparison_metrics"]["full_rotation"]
            assert metric["gross_turnover_notional_base"]["currency"] == "USD"
            assert Decimal(metric["gross_turnover_notional_base"]["amount"]) == Decimal("20000")
            assert (
                client.get(
                    execute_url.removesuffix("/execute"), headers={"X-Tenant-Id": TENANT_B}
                ).status_code
                == 404
            )
    finally:
        release_engine.set()
        reset_dpm_run_support_service_for_tests()
        app.dependency_overrides = original_overrides


def test_migration_from_0032_quarantines_legacy_operations(
    dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import psycopg
    from psycopg.rows import dict_row

    schema = f"issue719_upgrade_{uuid.uuid4().hex[:12]}"
    admin = psycopg.connect(dsn, row_factory=dict_row)
    try:
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.commit()
        admin.execute(f'SET search_path TO "{schema}"')
        all_migrations = postgres_migrations._load_migrations(namespace="dpm")
        assert any(migration.version == "0033" for migration in all_migrations)
        pre_0033_migrations = [
            migration for migration in all_migrations if migration.version < "0033"
        ]
        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: pre_0033_migrations,
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")
        operation_ids = {
            status: f"dop_legacy_{status.lower()}_{uuid.uuid4().hex}"
            for status in ("PENDING", "RUNNING", "SUCCEEDED", "FAILED")
        }
        for status, operation_id in operation_ids.items():
            admin.execute(
                """
                INSERT INTO dpm_async_operations (
                    operation_id, operation_type, status, correlation_id, created_at, request_json
                ) VALUES (%s, 'ANALYZE_SCENARIOS', %s, %s, %s, %s)
                """,
                (
                    operation_id,
                    status,
                    f"corr-{uuid.uuid4().hex}",
                    datetime.now(timezone.utc).isoformat(),
                    '{"legacy":true}',
                ),
            )
        admin.commit()

        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: all_migrations,
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")
        preserved = admin.execute(
            """
            SELECT operation_id, status, tenant_id, execution_token, execution_attempt,
                   execution_claimed_at, execution_lease_expires_at
            FROM dpm_async_operations WHERE operation_id = ANY(%s)
            ORDER BY status
            """,
            (list(operation_ids.values()),),
        ).fetchall()
        assert {row["status"] for row in preserved} == set(operation_ids)
        assert all(row["tenant_id"] is None for row in preserved)
        assert all(row["execution_token"] is None for row in preserved)
        assert all(row["execution_attempt"] == 0 for row in preserved)
        assert all(row["execution_claimed_at"] is None for row in preserved)
        assert all(row["execution_lease_expires_at"] is None for row in preserved)
    finally:
        admin.rollback()
        admin.execute("SET search_path TO public")
        admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.commit()
        admin.close()
