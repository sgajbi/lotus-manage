from datetime import datetime, timezone

import pytest

from src.core.dpm.engine import run_simulation
from src.core.dpm_runs.models import DpmRunRecord
from src.core.dpm_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.models import EngineOptions
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _build_service(*, workflow_enabled: bool = False) -> DpmRunSupportService:
    return DpmRunSupportService(
        repository=InMemoryDpmRunRepository(),
        workflow_enabled=workflow_enabled,
    )


def _sample_result():
    return run_simulation(
        portfolio_snapshot(
            portfolio_id="pf_service_artifact_1",
            base_currency="SGD",
            positions=[],
            cash_balances=[cash("SGD", "10000.00")],
        ),
        market_data_snapshot(prices=[price("EQ_1", "100.00", "SGD")], fx_rates=[]),
        model_portfolio(targets=[target("EQ_1", "1.0")]),
        [shelf_entry("EQ_1", status="APPROVED")],
        EngineOptions(),
        request_hash="sha256:req-service-artifact-1",
        correlation_id="corr_service_artifact_1",
    )


def test_service_operation_state_mutation_and_missing_operation_errors():
    service = _build_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-service-op-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    service.mark_operation_running(operation_id=accepted.operation_id)
    running = service.get_async_operation(operation_id=accepted.operation_id)
    assert running.status == "RUNNING"
    assert running.started_at is not None

    service.complete_operation_success(operation_id=accepted.operation_id, result_json={"ok": True})
    succeeded = service.get_async_operation(operation_id=accepted.operation_id)
    assert succeeded.status == "SUCCEEDED"
    assert succeeded.result == {"ok": True}
    assert succeeded.error is None

    accepted_failed = service.submit_analyze_async(
        correlation_id="corr-service-op-2",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    service.complete_operation_failure(
        operation_id=accepted_failed.operation_id,
        code="FAILED_TEST",
        message="failed",
    )
    failed = service.get_async_operation(operation_id=accepted_failed.operation_id)
    assert failed.status == "FAILED"
    assert failed.result is None
    assert failed.error is not None
    assert failed.error.code == "FAILED_TEST"
    assert failed.error.message == "failed"

    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.mark_operation_running(operation_id="dop_missing")
    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.complete_operation_success(operation_id="dop_missing", result_json={"ok": True})
    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.complete_operation_failure(
            operation_id="dop_missing",
            code="ERR",
            message="missing",
        )


def test_service_apply_workflow_action_missing_run():
    service = _build_service(workflow_enabled=True)
    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.apply_workflow_action(
            rebalance_run_id="rr_missing",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_1",
            correlation_id="corr-workflow-missing",
        )


def test_service_persisted_artifact_mode_stores_and_reads_artifact():
    repository = InMemoryDpmRunRepository()
    service = DpmRunSupportService(
        repository=repository,
        artifact_store_mode="PERSISTED",
    )
    result = _sample_result()
    service.record_run(
        result=result,
        request_hash="sha256:req-service-artifact-1",
        portfolio_id="pf_service_artifact_1",
        idempotency_key="idem_service_artifact_1",
    )

    stored = repository.get_run_artifact(rebalance_run_id=result.rebalance_run_id)
    assert stored is not None
    artifact = service.get_run_artifact(rebalance_run_id=result.rebalance_run_id)
    assert artifact.rebalance_run_id == result.rebalance_run_id
    assert artifact.evidence.hashes.artifact_hash.startswith("sha256:")


def test_service_persisted_artifact_mode_backfills_missing_persisted_artifact():
    repository = InMemoryDpmRunRepository()
    service = DpmRunSupportService(
        repository=repository,
        artifact_store_mode="PERSISTED",
    )
    result = _sample_result()
    run = DpmRunRecord(
        rebalance_run_id=result.rebalance_run_id,
        correlation_id=result.correlation_id,
        request_hash="sha256:req-service-artifact-backfill",
        idempotency_key=None,
        portfolio_id="pf_service_artifact_1",
        created_at=datetime.now(timezone.utc),
        result_json=result.model_dump(mode="json"),
    )
    repository.save_run(run)

    assert repository.get_run_artifact(rebalance_run_id=result.rebalance_run_id) is None
    artifact = service.get_run_artifact(rebalance_run_id=result.rebalance_run_id)
    assert artifact.rebalance_run_id == result.rebalance_run_id
    assert repository.get_run_artifact(rebalance_run_id=result.rebalance_run_id) is not None
