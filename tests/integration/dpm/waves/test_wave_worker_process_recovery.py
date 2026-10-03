"""Physical worker death across the durable financial/item publication boundary.

Synthetic, manually source-ready inputs prove recovery, not live source authority,
approval, instruction release, core booking, or a production capacity envelope.
"""

from __future__ import annotations

import multiprocessing
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from multiprocessing.connection import Connection

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.main import app
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves.models import DpmRebalanceWaveItem
from src.core.waves.simulation_operations import DpmWaveSimulationItemClaim
from src.infrastructure.construction import PostgresConstructionRepository
from src.infrastructure.rebalance_runs import PostgresDpmRunRepository
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.integration.dpm.waves.financial_fixture import admit_financial_operation


@contextmanager
def _postgres_client(dsn: str, repository: PostgresDpmWaveRepository):
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_wave_repository] = lambda: repository
    app.dependency_overrides[get_construction_repository] = lambda: PostgresConstructionRepository(
        dsn=dsn
    )
    app.dependency_overrides[get_dpm_run_support_service] = lambda: DpmRunSupportService(
        repository=PostgresDpmRunRepository(dsn=dsn)
    )
    app.dependency_overrides[get_risk_authority_client] = lambda: None
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides = original


def _worker(dsn: str, tenant_id: str, operation_id: str, pipe: Connection, interrupt: bool) -> None:
    """Each spawned worker builds independent, exclusively PostgreSQL adapters."""
    repository = PostgresDpmWaveRepository(dsn=dsn)
    if interrupt:
        # The application reaches this call only after real construction/run commits.
        # Block before the item checkpoint; only the parent can terminate this worker.
        def before_checkpoint(*, claim, result_item, completed_at):
            pipe.send((claim.model_dump(mode="json"), result_item.model_dump(mode="json")))
            pipe.recv()
            raise AssertionError("The interrupted worker must never resume publication")

        repository.publish_simulation_item_result = before_checkpoint
    try:
        with _postgres_client(dsn, repository) as client:
            response = client.post(
                f"/api/v1/rebalance/waves/simulation-operations/{operation_id}/work",
                headers={"X-Tenant-Id": tenant_id},
                json={
                    "worker_id": "interrupted" if interrupt else "replacement",
                    "max_items": 1,
                    "lease_seconds": 5 if interrupt else 30,
                },
            )
            assert response.status_code == 200, response.text
            result = response.json()
            pipe.send(
                (
                    result["operation"]["status"],
                    result["claimed_count"],
                    result["completed_count"],
                    result["failed_count"],
                )
            )
    finally:
        pipe.close()


def _receive(pipe: Connection, worker: multiprocessing.Process):
    assert pipe.poll(60), f"Worker {worker.pid} produced no receipt (exit={worker.exitcode})"
    return pipe.recv()


def _stop(worker: multiprocessing.Process) -> None:
    if worker.is_alive():
        worker.kill()
    worker.join(timeout=10)
    assert not worker.is_alive(), "Owned proof worker did not terminate"
    worker.close()


def test_killed_worker_recovers_durable_financial_artifact_in_fresh_process() -> None:
    dsn = postgres_dsn_or_skip("physical wave worker termination and durable financial recovery")
    suffix = uuid.uuid4().hex
    tenant_id, wave_id = f"tenant-process-{suffix}", f"wave-process-{suffix}"
    repository = PostgresDpmWaveRepository(dsn=dsn)
    operation = admit_financial_operation(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        item_count=1,
        max_concurrency=1,
    )
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    interrupted = context.Process(
        target=_worker, args=(dsn, tenant_id, operation.operation_id, child, True)
    )
    interrupted.start()
    child.close()
    try:
        claim_json, item_json = _receive(parent, interrupted)
        claim = DpmWaveSimulationItemClaim.model_validate(claim_json)
        committed_item = DpmRebalanceWaveItem.model_validate(item_json)
        assert interrupted.is_alive()
        pending = repository.list_simulation_items(
            tenant_id=tenant_id, operation_id=operation.operation_id, limit=10, offset=0
        ).items[0]
        assert pending.status == "RUNNING"
        assert pending.result_item is None
        construction = PostgresConstructionRepository(dsn=dsn)
        sets_before = construction.list_alternative_sets(
            tenant_id=tenant_id, portfolio_id=claim.portfolio_id, limit=10
        )
        assert len(sets_before) == 1
        alternative = sets_before[0].alternatives[0]
        assert alternative.rebalance_run_id is not None
        runs = DpmRunSupportService(repository=PostgresDpmRunRepository(dsn=dsn))
        artifact_before = runs.get_run_artifact_for_tenant(
            tenant_id=tenant_id, rebalance_run_id=alternative.rebalance_run_id
        )
        # Independent arithmetic: 100*100 + 5000 = 15000; 80% = 120 shares.
        assert alternative.diagnostics["proposed_changes"][0]["quantity"] == "20"
        assert artifact_before.result.after_simulated.positions[0].quantity == Decimal("120")
        assert artifact_before.result.after_simulated.cash_balances[0].amount == Decimal("3000")
        assert artifact_before.result.before.total_value.amount == Decimal("15000")
        assert artifact_before.result.after_simulated.total_value.amount == Decimal("15000")
        interrupted.kill()
        interrupted.join(timeout=10)
        assert not interrupted.is_alive()
        assert interrupted.exitcode not in (None, 0)
    finally:
        parent.close()
        _stop(interrupted)

    # Let the real persisted lease expire; do not manufacture timestamps in the DB.
    remaining = (claim.lease_expires_at - datetime.now(UTC)).total_seconds()
    if remaining > 0:
        time.sleep(remaining + 0.05)
    replacement_parent, replacement_child = context.Pipe()
    replacement = context.Process(
        target=_worker,
        args=(dsn, tenant_id, operation.operation_id, replacement_child, False),
    )
    replacement.start()
    replacement_child.close()
    try:
        assert _receive(replacement_parent, replacement) == ("SUCCEEDED", 1, 1, 0)
        replacement.join(timeout=10)
        assert replacement.exitcode == 0
    finally:
        replacement_parent.close()
        _stop(replacement)

    reopened = PostgresDpmWaveRepository(dsn=dsn)
    recovered = reopened.list_simulation_items(
        tenant_id=tenant_id, operation_id=operation.operation_id, limit=10, offset=0
    ).items[0]
    assert recovered.status == "SUCCEEDED"
    assert recovered.attempt_count == 2
    assert recovered.claim_generation == claim.claim_generation + 1
    assert recovered.result_item == committed_item
    assert (
        reopened.publish_simulation_item_result(
            claim=claim, result_item=committed_item, completed_at=datetime.now(UTC)
        )
        is False
    )
    assert (
        construction.list_alternative_sets(
            tenant_id=tenant_id, portfolio_id=claim.portfolio_id, limit=10
        )
        == sets_before
    )
    artifact_after = DpmRunSupportService(
        repository=PostgresDpmRunRepository(dsn=dsn)
    ).get_run_artifact_for_tenant(
        tenant_id=tenant_id, rebalance_run_id=alternative.rebalance_run_id
    )
    assert artifact_after == artifact_before
    persisted_runs = DpmRunSupportService(
        repository=PostgresDpmRunRepository(dsn=dsn)
    ).list_runs_for_tenant(
        tenant_id=tenant_id,
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=claim.portfolio_id,
        limit=10,
        cursor=None,
    )
    assert [run.rebalance_run_id for run in persisted_runs.items] == [alternative.rebalance_run_id]
    assert (
        PostgresDpmRunRepository(dsn=dsn).get_run_for_tenant(
            tenant_id=f"other-{tenant_id}", rebalance_run_id=alternative.rebalance_run_id
        )
        is None
    )
    assert (
        reopened.get_simulation_operation(
            tenant_id=f"other-{tenant_id}", operation_id=operation.operation_id
        )
        is None
    )
    wave = reopened.get_wave(tenant_id=tenant_id, wave_id=wave_id)
    assert wave is not None and wave.state == "SIMULATED"
    assert sum(event.reason_code == "WAVE_ASYNC_SIMULATION_COMPLETED" for event in wave.events) == 1
    with _postgres_client(dsn, reopened) as client:
        path = f"/api/v1/rebalance/waves/simulation-operations/{operation.operation_id}"
        headers = {"X-Tenant-Id": tenant_id}
        progress = client.get(path, headers=headers)
        assert progress.status_code == 200
        assert progress.json()["status"] == "SUCCEEDED"
        results = client.get(f"{path}/results", headers=headers)
        assert results.status_code == 200
        assert results.json()["total_count"] == 1
        item = results.json()["items"][0]
        assert item["status"] == "SUCCEEDED" and item["attempt_count"] == 2
        assert item["alternative_set_id"] == committed_item.alternative_set_id
        for endpoint in (path, f"{path}/results"):
            assert (
                client.get(endpoint, headers={"X-Tenant-Id": f"other-{tenant_id}"}).status_code
                == 404
            )
