"""HTTP recovery after API death and an aborted, lock-blocked publication session.

Synthetic source-ready input; not upstream authority or capacity proof. The default
runtime is source-installed; the image acceptance runner repeats this case by image ID.
All financial writes use the unmodified native API. Fault locks/backend termination
are confined to this case's disposable database, never a shared runtime.
"""

from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import psycopg
import pytest
from psycopg.rows import dict_row

from src.infrastructure.waves.postgres import PostgresDpmWaveRepository
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.integration.dpm.waves.financial_fixture import financial_request, source_ready_wave


def _wait_row(connection, query, params=()):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        row = connection.execute(query, params).fetchone()
        if row is not None:
            return row
        time.sleep(0.05)
    pytest.fail("Expected durable fault-boundary observation did not arrive")


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _interrupt_publication(dsn, client, process, path, headers):
    # Hold financial storage until the claim is durable, then fence publication.
    # This enforces ordering in PostgreSQL rather than relying on timing or mocks.
    with (
        psycopg.connect(dsn) as financial_lock,
        psycopg.connect(dsn) as publication_lock,
        psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as observer,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        financial_lock.execute("LOCK TABLE dpm_runs IN ACCESS EXCLUSIVE MODE")
        pending = executor.submit(
            client.post,
            path,
            headers=headers,
            json={"worker_id": "interrupted-http", "max_items": 1, "lease_seconds": 10},
        )
        try:
            claimed = _wait_row(
                observer, "SELECT * FROM dpm_wave_simulation_items WHERE status='RUNNING'"
            )
            publication_lock.execute(
                "SELECT operation_id FROM dpm_wave_simulation_operations WHERE operation_id=%s FOR UPDATE",
                (claimed["operation_id"],),
            )
            blocker_pid = publication_lock.info.backend_pid
            financial_lock.commit()
            durable = _wait_row(
                observer,
                "SELECT rebalance_run_id, artifact_json FROM dpm_run_artifacts",
            )
            publisher = _wait_row(
                observer,
                "SELECT pid FROM pg_stat_activity WHERE datname=current_database() "
                "AND wait_event_type='Lock' AND %s=ANY(pg_blocking_pids(pid)) "
                "AND query LIKE '%%SELECT * FROM dpm_wave_simulation_operations%%'",
                (blocker_pid,),
            )
            row = observer.execute(
                "SELECT status, result_item_json FROM dpm_wave_simulation_items"
            ).fetchone()
            assert row == {"status": "RUNNING", "result_item_json": None}
            assert not pending.done()
            process.kill()
            process.join(10)
            assert process.exitcode not in (None, 0)
            # A database query can outlive its disconnected API process. Abort
            # only the observed blocked publisher before releasing our row lock.
            observer.execute("SELECT pg_terminate_backend(%s)", (publisher["pid"],))
            with pytest.raises(httpx.TransportError):
                pending.result(timeout=10)
            return claimed, durable
        finally:
            financial_lock.rollback()
            publication_lock.rollback()


def test_http_wave_worker_recovers_committed_financial_artifact_after_process_death():
    tenant = f"tenant-wave-http-{uuid.uuid4().hex}"
    wave_id = f"wave-http-{uuid.uuid4().hex}"
    headers = {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": "http-pm",
        "X-Role": "PM",
        "X-Capabilities": "manage.write",
        "X-Correlation-Id": uuid.uuid4().hex,
        "X-Service-Identity": "local-network-proof",
        "Idempotency-Key": uuid.uuid4().hex,
    }
    foreign = {**headers, "X-Tenant-Id": "foreign-http-tenant"}
    with disposable_database() as dsn:
        wave = source_ready_wave(tenant_id=tenant, wave_id=wave_id, item_count=1)
        PostgresDpmWaveRepository(dsn=dsn).save_wave(
            wave=wave, tenant_id=tenant, idempotency_key=None, request_hash=None
        )
        body = {
            "actor_id": "http-pm",
            "max_concurrency": 1,
            "max_attempts": 3,
            "methods": ["HEURISTIC_EXPLAINABLE"],
            "item_inputs": [
                {
                    "wave_item_id": wave.items[0].wave_item_id,
                    "stateless_input": financial_request(wave.items[0].portfolio_id),
                }
            ],
        }
        admission_path = f"/api/v1/rebalance/waves/{wave_id}/simulation-operations"
        with native_api(dsn) as (client, original):
            admitted = _call(client, "POST", admission_path, headers, body, expected=202)
            operation_path = (
                f"/api/v1/rebalance/waves/simulation-operations/{admitted['operation_id']}"
            )
            work_path = f"{operation_path}/work"
            _call(client, "GET", operation_path, foreign, expected=404)
            denied = {key: value for key, value in headers.items() if key != "X-Capabilities"}
            _call(client, "POST", work_path, denied, {"worker_id": "denied"}, expected=403)
            old_pid = original.pid
            claimed, durable = _interrupt_publication(dsn, client, original, work_path, headers)
        remaining = (claimed["lease_expires_at"] - datetime.now(UTC)).total_seconds()
        if remaining > 0:
            time.sleep(remaining + 0.1)
        with native_api(dsn) as (client, replacement):
            assert replacement.pid != old_pid
            retained = _call(client, "GET", operation_path, headers)
            for field in ("request_hash", "source_identity_hash", "operation_id"):
                assert retained[field] == admitted[field]
            assert retained["counts"]["RUNNING"] == 1
            worked = _call(
                client,
                "POST",
                work_path,
                headers,
                {"worker_id": "replacement-http", "max_items": 1, "lease_seconds": 30},
            )
            assert (worked["claimed_count"], worked["completed_count"], worked["failed_count"]) == (
                1,
                1,
                0,
            )
            assert worked["operation"]["status"] == "SUCCEEDED"
            results = _call(client, "GET", f"{operation_path}/results?limit=1", headers)
            assert results["total_count"] == results["returned_count"] == 1
            assert results["next_offset"] is None
            item = results["items"][0]
            assert item["status"] == "SUCCEEDED" and item["attempt_count"] == 2
            rid = durable["rebalance_run_id"]
            artifact_path = f"/api/v1/rebalance/runs/{rid}/artifact"
            artifact = _call(client, "GET", artifact_path, headers)
            assert artifact == json.loads(durable["artifact_json"])
            result = artifact["result"]
            assert Decimal(result["before"]["total_value"]["amount"]) == 15000
            assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == 120
            assert Decimal(result["after_simulated"]["cash_balances"][0]["amount"]) == 3000
            alternative_set = _call(
                client,
                "GET",
                f"/api/v1/construction/alternative-sets/{item['alternative_set_id']}",
                headers,
            )
            alternative = alternative_set["alternatives"][0]
            assert alternative["rebalance_run_id"] == rid
            changes = alternative["diagnostics"]["proposed_changes"]
            assert len(changes) == 1 and changes[0]["action"] == "BUY"
            assert Decimal(changes[0]["quantity"]) == 20
            _call(client, "GET", artifact_path, foreign, expected=404)
            _call(client, "GET", f"{operation_path}/results", foreign, expected=404)
            replay = _call(client, "POST", admission_path, headers, body, expected=202)
            assert (
                replay["idempotent_replay"] and replay["operation_id"] == admitted["operation_id"]
            )
            repeat = _call(client, "POST", work_path, headers, {"worker_id": "repeat-http"})
            assert (
                repeat["claimed_count"] == repeat["completed_count"] == repeat["failed_count"] == 0
            )
            assert _call(client, "GET", f"{operation_path}/results?limit=1", headers) == results
        with psycopg.connect(dsn) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            for table in ("dpm_runs", "dpm_run_artifacts", "dpm_construction_alternative_sets"):
                assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (1,)
            assert connection.execute(
                "SELECT status, attempt_count FROM dpm_wave_simulation_items"
            ).fetchone() == ("SUCCEEDED", 2)
