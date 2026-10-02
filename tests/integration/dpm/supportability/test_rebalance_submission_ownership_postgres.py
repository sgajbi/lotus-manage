"""PostgreSQL proof for tenant-scoped synchronous rebalance admission (#716)."""

from __future__ import annotations

import multiprocessing
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.services.rebalance_run_support_service import (
    reset_dpm_run_support_service_for_tests,
)
from src.core.common.capabilities import has_psycopg
from src.core.rebalance_runs.models import (
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunRecord,
)
from src.core.rebalance_runs.repository import DpmRunRepositoryConflictError
from src.infrastructure.rebalance_runs.postgres import PostgresDpmRunRepository
from src.infrastructure import postgres_migrations
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

TENANT_A = "tenant-rebalance-a"
TENANT_B = "tenant-rebalance-b"
_PROOF = "atomic rebalance submission ownership proof"


def _claim_in_process(
    dsn: str,
    tenant_id: str,
    idempotency_key: str,
    request_hash: str,
    token: str,
    ready: object,
    start: object,
) -> tuple[str, str, str]:
    repository = PostgresDpmRunRepository(dsn=dsn)
    ready.set()
    start.wait(timeout=20)
    now = datetime.now(timezone.utc)
    claim = repository.claim_simulation_submission(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        claim_token=token,
        claimed_at=now,
        claim_expires_at=now + timedelta(seconds=60),
    )
    return token, claim.claim_token, claim.status


@pytest.fixture
def dsn() -> str:
    return postgres_dsn_or_skip(_PROOF)


@pytest.fixture(autouse=True)
def reset_submission_tables(dsn: str) -> None:
    repository = PostgresDpmRunRepository(dsn=dsn)
    with closing(repository._connect()) as connection:
        connection.execute(
            "TRUNCATE TABLE dpm_run_submission_claims, dpm_lineage_edges, "
            "dpm_run_idempotency_history, dpm_run_idempotency, dpm_run_artifacts, dpm_runs CASCADE"
        )
        connection.commit()


def test_separate_processes_claim_one_tenant_key_and_restart_replays_one_run(dsn: str) -> None:
    key = f"idem-concurrent-{uuid.uuid4().hex}"
    request_hash = f"sha256:{uuid.uuid4().hex}"
    tokens = [uuid.uuid4().hex for _ in range(4)]
    context = multiprocessing.get_context("spawn")
    with context.Manager() as manager:
        start = manager.Event()
        ready_events = [manager.Event() for _ in tokens]
        with ProcessPoolExecutor(max_workers=4, mp_context=context) as pool:
            futures = [
                pool.submit(
                    _claim_in_process,
                    dsn,
                    TENANT_A,
                    key,
                    request_hash,
                    token,
                    ready,
                    start,
                )
                for token, ready in zip(tokens, ready_events, strict=True)
            ]
            assert all(ready.wait(timeout=20) for ready in ready_events)
            start.set()
            outcomes = [future.result(timeout=30) for future in futures]

    winning_tokens = {stored_token for _, stored_token, _ in outcomes}
    assert len(winning_tokens) == 1
    winner = winning_tokens.pop()
    assert sum(own == stored for own, stored, _ in outcomes) == 1
    assert {status for _, _, status in outcomes} == {"IN_PROGRESS"}

    repository = PostgresDpmRunRepository(dsn=dsn)
    run = _run(tenant_id=TENANT_A, key=key, request_hash=request_hash)
    repository.complete_simulation_submission(
        tenant_id=TENANT_A,
        idempotency_key=key,
        request_hash=request_hash,
        claim_token=winner,
        run=run,
        artifact_json={"rebalance_run_id": run.rebalance_run_id},
        idempotency_history=_history(run=run, tenant_id=TENANT_A),
        lineage_edges=_lineage(run),
        completed_at=run.created_at,
    )

    restarted = PostgresDpmRunRepository(dsn=dsn)
    completed = restarted.get_simulation_submission_claim(tenant_id=TENANT_A, idempotency_key=key)
    assert completed is not None and completed.status == "COMPLETED"
    assert completed.rebalance_run_id == run.rebalance_run_id
    assert (
        restarted.get_run_for_tenant(tenant_id=TENANT_A, rebalance_run_id=run.rebalance_run_id)
        == run
    )
    mapping = restarted.get_idempotency_mapping_for_tenant(tenant_id=TENANT_A, idempotency_key=key)
    assert mapping is not None and mapping.rebalance_run_id == run.rebalance_run_id
    assert (
        restarted.get_run_by_correlation_for_tenant(
            tenant_id=TENANT_A,
            correlation_id=run.correlation_id,
        )
        == run
    )
    assert (
        restarted.get_run_by_request_hash_for_tenant(
            tenant_id=TENANT_A,
            request_hash=request_hash,
        )
        == run
    )
    page, next_cursor = restarted.list_runs_for_tenant(
        tenant_id=TENANT_A,
        created_from=None,
        created_to=None,
        status="READY",
        request_hash=request_hash,
        portfolio_id=run.portfolio_id,
        limit=10,
        cursor=None,
    )
    assert page == [run]
    assert next_cursor is None
    assert restarted.list_idempotency_history_for_tenant(
        tenant_id=TENANT_A,
        idempotency_key=key,
    ) == [_history(run=run, tenant_id=TENANT_A)]


def test_supported_http_concurrency_returns_one_postgres_run(
    dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", dsn)
    reset_dpm_run_support_service_for_tests()
    original_overrides = dict(app.dependency_overrides)

    async def override_db_session():
        yield None

    app.dependency_overrides[get_db_session] = override_db_session
    payload = {
        "input_mode": "stateless",
        "stateless_input": {
            "portfolio_snapshot": {
                "portfolio_id": "portfolio-concurrency-financial-oracle",
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "5000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                "fx_rates": [],
            },
            "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.8"}]},
            "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
            "options": {
                "target_method": "HEURISTIC",
                "enable_settlement_awareness": False,
                "enable_tax_awareness": False,
            },
        },
    }
    key = f"idem-http-concurrent-{uuid.uuid4().hex}"
    barrier = Barrier(2)
    try:
        with TestClient(app) as client:

            def submit(correlation_id: str):
                barrier.wait(timeout=5)
                return client.post(
                    "/api/v1/rebalance/simulate",
                    json=payload,
                    headers={
                        "Idempotency-Key": key,
                        "X-Correlation-Id": correlation_id,
                        "X-Tenant-Id": TENANT_A,
                    },
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(submit, ["corr-http-worker-a", "corr-http-worker-b"]))
            assert [response.status_code for response in responses] == [200, 200]
            run_ids = {response.json()["rebalance_run_id"] for response in responses}
            assert len(run_ids) == 1
            run_id = run_ids.pop()
            for response in responses:
                result = response.json()
                assert len(result["intents"]) == 1
                assert result["intents"][0]["side"] == "BUY"
                assert Decimal(result["intents"][0]["quantity"]) == Decimal("20")
                assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == Decimal(
                    "120"
                )
                assert result["after_simulated"]["cash_balances"][0]["currency"] == "USD"
                assert Decimal(result["after_simulated"]["cash_balances"][0]["amount"]) == Decimal(
                    "3000"
                )
                assert result["before"]["total_value"]["currency"] == "USD"
                assert Decimal(result["before"]["total_value"]["amount"]) == Decimal("15000")
                assert result["after_simulated"]["total_value"] == result["before"]["total_value"]
            assert (
                client.get(
                    f"/api/v1/rebalance/runs/{run_id}",
                    headers={"X-Tenant-Id": TENANT_A},
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/rebalance/runs/{run_id}",
                    headers={"X-Tenant-Id": TENANT_B},
                ).status_code
                == 404
            )
    finally:
        reset_dpm_run_support_service_for_tests()
        app.dependency_overrides = original_overrides


def test_expired_crash_claim_is_fenced_and_same_key_is_independent_across_tenants(
    dsn: str,
) -> None:
    repository = PostgresDpmRunRepository(dsn=dsn)
    key = f"idem-recovery-{uuid.uuid4().hex}"
    request_hash = f"sha256:{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    abandoned = repository.claim_simulation_submission(
        tenant_id=TENANT_A,
        idempotency_key=key,
        request_hash=request_hash,
        claim_token="crashed-worker",
        claimed_at=now - timedelta(minutes=2),
        claim_expires_at=now - timedelta(minutes=1),
    )
    assert abandoned.claim_token == "crashed-worker"

    recovered = PostgresDpmRunRepository(dsn=dsn).claim_simulation_submission(
        tenant_id=TENANT_A,
        idempotency_key=key,
        request_hash=request_hash,
        claim_token="recovery-worker",
        claimed_at=now,
        claim_expires_at=now + timedelta(minutes=1),
    )
    assert recovered.claim_token == "recovery-worker"

    other_tenant = repository.claim_simulation_submission(
        tenant_id=TENANT_B,
        idempotency_key=key,
        request_hash="sha256:tenant-b-independent",
        claim_token="tenant-b-worker",
        claimed_at=now,
        claim_expires_at=now + timedelta(minutes=1),
    )
    assert other_tenant.claim_token == "tenant-b-worker"
    repository.abandon_simulation_submission_claim(
        tenant_id=TENANT_B,
        idempotency_key=key,
        claim_token="tenant-b-worker",
        abandoned_at=now,
    )
    abandoned_other = repository.get_simulation_submission_claim(
        tenant_id=TENANT_B,
        idempotency_key=key,
    )
    assert abandoned_other is not None and abandoned_other.claim_expires_at == now

    lost_run = _run(tenant_id=TENANT_A, key=key, request_hash=request_hash)
    with pytest.raises(
        DpmRunRepositoryConflictError,
        match="DPM_SIMULATION_SUBMISSION_CLAIM_LOST",
    ):
        repository.complete_simulation_submission(
            tenant_id=TENANT_A,
            idempotency_key=key,
            request_hash=request_hash,
            claim_token="stale-worker",
            run=lost_run,
            artifact_json=None,
            idempotency_history=_history(run=lost_run, tenant_id=TENANT_A),
            lineage_edges=[],
            completed_at=now,
        )
    assert (
        repository.get_idempotency_mapping_for_tenant(tenant_id=TENANT_B, idempotency_key=key)
        is None
    )


def test_legacy_unattributed_rows_remain_preserved_but_unreachable(dsn: str) -> None:
    repository = PostgresDpmRunRepository(dsn=dsn)
    legacy_run_id = f"rr_legacy_{uuid.uuid4().hex}"
    key = f"idem-legacy-{uuid.uuid4().hex}"
    with closing(repository._connect()) as connection:
        connection.execute(
            """
            INSERT INTO dpm_runs (
                rebalance_run_id, correlation_id, request_hash, idempotency_key,
                portfolio_id, created_at, result_json, tenant_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
            """,
            (
                legacy_run_id,
                f"corr-{uuid.uuid4().hex}",
                "sha256:legacy",
                key,
                "portfolio-legacy",
                datetime.now(timezone.utc).isoformat(),
                '{"rebalance_run_id":"legacy","status":"READY"}',
            ),
        )
        connection.execute(
            """
            INSERT INTO dpm_run_idempotency_legacy_unattributed (
                idempotency_key, request_hash, rebalance_run_id, created_at
            ) VALUES (%s, %s, %s, %s)
            """,
            (key, "sha256:legacy", legacy_run_id, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()

    assert repository.get_run_for_tenant(tenant_id=TENANT_A, rebalance_run_id=legacy_run_id) is None
    assert (
        repository.get_idempotency_mapping_for_tenant(tenant_id=TENANT_A, idempotency_key=key)
        is None
    )
    with closing(repository._connect()) as connection:
        preserved = connection.execute(
            "SELECT COUNT(*) AS count FROM dpm_run_idempotency_legacy_unattributed "
            "WHERE idempotency_key = %s",
            (key,),
        ).fetchone()
    assert preserved["count"] == 1


def test_migration_from_0031_preserves_legacy_rows_and_builds_empty_owned_mapping(
    dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert has_psycopg()
    import psycopg
    from psycopg.rows import dict_row

    schema = f"issue716_upgrade_{uuid.uuid4().hex[:12]}"
    admin = psycopg.connect(dsn, row_factory=dict_row)
    try:
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.commit()
        admin.execute(f'SET search_path TO "{schema}"')
        all_migrations = postgres_migrations._load_migrations(namespace="dpm")
        assert {"0032", "0033"}.issubset({migration.version for migration in all_migrations})
        pre_0032_migrations = [
            migration for migration in all_migrations if migration.version < "0032"
        ]
        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: pre_0032_migrations,
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")
        legacy_run_id = f"rr_upgrade_{uuid.uuid4().hex}"
        key = f"idem-upgrade-{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        admin.execute(
            """
            INSERT INTO dpm_runs (
                rebalance_run_id, correlation_id, request_hash, idempotency_key,
                portfolio_id, created_at, result_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                legacy_run_id,
                f"corr-{uuid.uuid4().hex}",
                "sha256:upgrade",
                key,
                "portfolio-upgrade",
                now,
                '{"rebalance_run_id":"upgrade","status":"READY"}',
            ),
        )
        admin.execute(
            """
            INSERT INTO dpm_run_idempotency (
                idempotency_key, request_hash, rebalance_run_id, created_at
            ) VALUES (%s, %s, %s, %s)
            """,
            (key, "sha256:upgrade", legacy_run_id, now),
        )
        admin.commit()

        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: all_migrations,
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")

        preserved_mapping = admin.execute(
            "SELECT rebalance_run_id FROM dpm_run_idempotency_legacy_unattributed "
            "WHERE idempotency_key = %s",
            (key,),
        ).fetchone()
        quarantined_run = admin.execute(
            "SELECT tenant_id FROM dpm_runs WHERE rebalance_run_id = %s",
            (legacy_run_id,),
        ).fetchone()
        owned_mapping_count = admin.execute(
            "SELECT COUNT(*) AS count FROM dpm_run_idempotency"
        ).fetchone()
        assert preserved_mapping["rebalance_run_id"] == legacy_run_id
        assert quarantined_run["tenant_id"] is None
        assert owned_mapping_count["count"] == 0
    finally:
        admin.rollback()
        admin.execute("SET search_path TO public")
        admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.commit()
        admin.close()


def _run(*, tenant_id: str, key: str, request_hash: str) -> DpmRunRecord:
    run_id = f"rr_{uuid.uuid4().hex}"
    return DpmRunRecord(
        tenant_id=tenant_id,
        rebalance_run_id=run_id,
        correlation_id=f"corr_{uuid.uuid4().hex}",
        request_hash=request_hash,
        idempotency_key=key,
        portfolio_id="portfolio-concurrency-proof",
        created_at=datetime.now(timezone.utc),
        result_json={"rebalance_run_id": run_id, "status": "READY"},
    )


def _history(*, run: DpmRunRecord, tenant_id: str) -> DpmRunIdempotencyHistoryRecord:
    return DpmRunIdempotencyHistoryRecord(
        tenant_id=tenant_id,
        idempotency_key=run.idempotency_key or "",
        rebalance_run_id=run.rebalance_run_id,
        correlation_id=run.correlation_id,
        request_hash=run.request_hash,
        created_at=run.created_at,
    )


def _lineage(run: DpmRunRecord) -> list[DpmLineageEdgeRecord]:
    return [
        DpmLineageEdgeRecord(
            source_entity_id=run.correlation_id,
            edge_type="CORRELATION_TO_RUN",
            target_entity_id=run.rebalance_run_id,
            created_at=run.created_at,
            metadata_json={"request_hash": run.request_hash},
        )
    ]
