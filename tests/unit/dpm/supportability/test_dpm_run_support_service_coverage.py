from datetime import datetime, timedelta, timezone

import pytest

from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.core.rebalance_runs.service import (
    DpmAsyncOperationConflictError,
    DpmRunNotFoundError,
    DpmRunSupportService,
    _support_bundle_async_operation,
    _support_bundle_idempotency_history,
    _support_bundle_lineage,
    _support_bundle_workflow_history,
)
from src.core.models import EngineOptions
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
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


def test_service_rejects_duplicate_async_operation_correlation():
    service = _build_service()
    service.submit_analyze_async(
        correlation_id="corr-service-duplicate",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    with pytest.raises(
        DpmAsyncOperationConflictError,
        match="DPM_ASYNC_OPERATION_CORRELATION_CONFLICT",
    ):
        service.submit_analyze_async(
            correlation_id="corr-service-duplicate",
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
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


def test_supportability_summary_posture_empty_ready_stale_and_degraded():
    empty_service = _build_service()
    empty = empty_service.get_supportability_summary(store_backend="INMEMORY", retention_days=0)
    assert empty.supportability.state == "empty"
    assert empty.supportability.reason == "supportability_summary_empty"
    assert empty.supportability.freshness_bucket == "unknown"

    ready_service = _build_service()
    ready_service.record_run(
        result=_sample_result(),
        request_hash="sha256:req-supportability-ready",
        portfolio_id="pf_service_artifact_1",
        idempotency_key=None,
        created_at=datetime.now(timezone.utc),
    )
    ready = ready_service.get_supportability_summary(store_backend="INMEMORY", retention_days=0)
    assert ready.supportability.state == "ready"
    assert ready.supportability.reason == "supportability_summary_ready"
    assert ready.supportability.freshness_bucket == "current"

    stale_service = _build_service()
    stale_service.record_run(
        result=_sample_result(),
        request_hash="sha256:req-supportability-stale",
        portfolio_id="pf_service_artifact_1",
        idempotency_key=None,
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    stale = stale_service.get_supportability_summary(store_backend="INMEMORY", retention_days=0)
    assert stale.supportability.state == "stale"
    assert stale.supportability.reason == "supportability_summary_stale"
    assert stale.supportability.freshness_bucket == "stale"

    degraded_service = _build_service()
    accepted = degraded_service.submit_analyze_async(
        correlation_id="corr-supportability-degraded",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    degraded_service.complete_operation_failure(
        operation_id=accepted.operation_id,
        code="FAILED_TEST",
        message="failed",
    )
    degraded = degraded_service.get_supportability_summary(
        store_backend="INMEMORY",
        retention_days=0,
    )
    assert degraded.supportability.state == "degraded"
    assert degraded.supportability.reason == "supportability_summary_degraded"
    assert degraded.supportability.freshness_bucket == "current"


def test_support_bundle_helpers_project_optional_sections_and_sort_evidence():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = DpmRunRecord(
        rebalance_run_id="rr_support_bundle_1",
        correlation_id="corr_support_bundle_1",
        request_hash="sha256:req-support-bundle-1",
        idempotency_key="idem_support_bundle_1",
        portfolio_id="pf_support_bundle_1",
        created_at=now,
        result_json=_sample_result().model_dump(mode="json"),
    )

    operation = DpmAsyncOperationRecord(
        operation_id="dop_support_bundle_1",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=run.correlation_id,
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    async_operation = _support_bundle_async_operation(run=run, operation=operation)
    assert async_operation is not None
    assert async_operation.operation_id == "dop_support_bundle_1"
    assert async_operation.is_executable is True
    assert _support_bundle_async_operation(run=run, operation=None) is None

    history = _support_bundle_idempotency_history(
        run=run,
        history=[
            DpmRunIdempotencyHistoryRecord(
                idempotency_key=run.idempotency_key,
                rebalance_run_id=run.rebalance_run_id,
                correlation_id=run.correlation_id,
                request_hash=run.request_hash,
                created_at=now + timedelta(minutes=1),
            ),
            DpmRunIdempotencyHistoryRecord(
                idempotency_key=run.idempotency_key,
                rebalance_run_id="rr_support_bundle_0",
                correlation_id="corr_support_bundle_0",
                request_hash="sha256:req-support-bundle-0",
                created_at=now,
            ),
        ],
    )
    assert history is not None
    assert history.idempotency_key == run.idempotency_key
    assert [item.rebalance_run_id for item in history.history] == [
        "rr_support_bundle_0",
        run.rebalance_run_id,
    ]
    assert (
        _support_bundle_idempotency_history(
            run=run.model_copy(update={"idempotency_key": None}),
            history=[],
        )
        is None
    )

    workflow_history = _support_bundle_workflow_history(
        rebalance_run_id=run.rebalance_run_id,
        decisions=[
            DpmRunWorkflowDecisionRecord(
                decision_id="dwd_later",
                run_id=run.rebalance_run_id,
                action="APPROVE",
                reason_code="REVIEW_APPROVED",
                comment=None,
                actor_id="reviewer_1",
                decided_at=now + timedelta(minutes=2),
                correlation_id="corr_decision_later",
            ),
            DpmRunWorkflowDecisionRecord(
                decision_id="dwd_earlier",
                run_id=run.rebalance_run_id,
                action="REQUEST_CHANGES",
                reason_code="NEEDS_DETAIL",
                comment=None,
                actor_id="reviewer_2",
                decided_at=now,
                correlation_id="corr_decision_earlier",
            ),
        ],
    )
    assert [decision.decision_id for decision in workflow_history.decisions] == [
        "dwd_earlier",
        "dwd_later",
    ]

    lineage = _support_bundle_lineage(
        rebalance_run_id=run.rebalance_run_id,
        edges=[
            DpmLineageEdgeRecord(
                source_entity_id="idem_support_bundle_1",
                edge_type="IDEMPOTENCY_TO_RUN",
                target_entity_id=run.rebalance_run_id,
                created_at=now + timedelta(minutes=1),
                metadata_json={"request_hash": run.request_hash},
            ),
            DpmLineageEdgeRecord(
                source_entity_id=run.correlation_id,
                edge_type="CORRELATION_TO_RUN",
                target_entity_id=run.rebalance_run_id,
                created_at=now,
                metadata_json={"request_hash": run.request_hash},
            ),
        ],
    )
    assert [edge.edge_type for edge in lineage.edges] == [
        "CORRELATION_TO_RUN",
        "IDEMPOTENCY_TO_RUN",
    ]
