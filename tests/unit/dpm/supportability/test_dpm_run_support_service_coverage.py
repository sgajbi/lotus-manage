from datetime import datetime, timedelta, timezone
from decimal import Decimal

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


def _sample_result(
    *,
    portfolio_id: str = "pf_service_artifact_1",
    correlation_id: str = "corr_service_artifact_1",
    pending_review: bool = False,
):
    options = (
        EngineOptions(single_position_max_weight=Decimal("0.5"))
        if pending_review
        else EngineOptions()
    )
    return run_simulation(
        portfolio_snapshot(
            portfolio_id=portfolio_id,
            base_currency="SGD",
            positions=[],
            cash_balances=[cash("SGD", "10000.00")],
        ),
        market_data_snapshot(prices=[price("EQ_1", "100.00", "SGD")], fx_rates=[]),
        model_portfolio(targets=[target("EQ_1", "1.0")]),
        [shelf_entry("EQ_1", status="APPROVED")],
        options,
        request_hash=f"sha256:req-{portfolio_id}",
        correlation_id=correlation_id,
    )


def test_service_operation_state_mutation_and_missing_operation_errors():
    service = _build_service()
    accepted = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-service-op-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    claim = service.prepare_analyze_operation_execution(
        tenant_id="tenant-test", operation_id=accepted.operation_id
    )
    running = service.get_async_operation(
        tenant_id="tenant-test", operation_id=accepted.operation_id
    )
    assert running.status == "RUNNING"
    assert running.started_at is not None
    assert running.execution_attempt == 1
    assert running.execution_lease_expires_at is not None
    assert "execution_token" not in running.model_dump()

    service.complete_operation_success(claim=claim, result_json={"ok": True})
    service.complete_operation_success(claim=claim, result_json={"ok": True})
    with pytest.raises(
        DpmAsyncOperationConflictError,
        match="DPM_ASYNC_OPERATION_STALE_EXECUTION_OWNER",
    ):
        service.complete_operation_success(claim=claim, result_json={"ok": False})
    succeeded = service.get_async_operation(
        tenant_id="tenant-test", operation_id=accepted.operation_id
    )
    assert succeeded.status == "SUCCEEDED"
    assert succeeded.result == {"ok": True}
    assert succeeded.error is None

    accepted_failed = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-service-op-2",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    failed_claim = service.prepare_analyze_operation_execution(
        tenant_id="tenant-test", operation_id=accepted_failed.operation_id
    )
    service.complete_operation_failure(
        claim=failed_claim,
        code="FAILED_TEST",
        message="failed",
    )
    service.complete_operation_failure(
        claim=failed_claim,
        code="FAILED_TEST",
        message="failed",
    )
    with pytest.raises(
        DpmAsyncOperationConflictError,
        match="DPM_ASYNC_OPERATION_STALE_EXECUTION_OWNER",
    ):
        service.complete_operation_failure(
            claim=failed_claim,
            code="DIFFERENT_FAILURE",
            message="must not replace the owner's terminal result",
        )
    failed = service.get_async_operation(
        tenant_id="tenant-test", operation_id=accepted_failed.operation_id
    )
    assert failed.status == "FAILED"
    assert failed.result is None
    assert failed.error is not None
    assert failed.error.code == "FAILED_TEST"
    assert failed.error.message == "failed"

    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.prepare_analyze_operation_execution(
            tenant_id="tenant-test", operation_id="dop_missing"
        )


def test_service_async_operations_require_tenant_and_tenant_scope_lineage() -> None:
    repository = InMemoryDpmRunRepository()
    service = DpmRunSupportService(repository=repository)

    with pytest.raises(ValueError, match="DPM_ASYNC_OPERATION_TENANT_REQUIRED"):
        service.submit_analyze_async(
            tenant_id="  ",
            correlation_id="corr-no-tenant",
            request_json={"scenarios": {}},
        )

    accepted = service.submit_analyze_async(
        tenant_id=" tenant-a ",
        correlation_id="corr-owned",
        request_json={"scenarios": {}},
    )
    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.get_async_operation(
            tenant_id="tenant-b",
            operation_id=accepted.operation_id,
        )
    edges = repository.list_lineage_edges(entity_id=accepted.operation_id)
    assert len(edges) == 1
    assert edges[0].tenant_id == "tenant-a"


def test_service_rejects_duplicate_async_operation_correlation():
    service = _build_service()
    service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-service-duplicate",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    with pytest.raises(
        DpmAsyncOperationConflictError,
        match="DPM_ASYNC_OPERATION_CORRELATION_CONFLICT",
    ):
        service.submit_analyze_async(
            tenant_id="tenant-test",
            correlation_id="corr-service-duplicate",
            request_json={"scenarios": {"baseline": {"options": {}}}},
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
        tenant_id="tenant-test",
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
        tenant_id="tenant-test",
        correlation_id="corr-supportability-degraded",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    claim = degraded_service.prepare_analyze_operation_execution(
        tenant_id="tenant-test", operation_id=accepted.operation_id
    )
    degraded_service.complete_operation_failure(
        claim=claim,
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


def test_supportability_summary_can_be_scoped_to_portfolio() -> None:
    service = _build_service(workflow_enabled=True)
    scoped_result = _sample_result(
        portfolio_id="pf-scoped",
        correlation_id="corr-scoped",
        pending_review=True,
    )
    other_result = _sample_result(
        portfolio_id="pf-other",
        correlation_id="corr-other",
    )
    service.record_run(
        result=scoped_result,
        request_hash="sha256:req-scoped",
        portfolio_id="pf-scoped",
        idempotency_key="idem-scoped",
        tenant_id="tenant-test",
    )
    service.record_run(
        result=other_result,
        request_hash="sha256:req-other",
        portfolio_id="pf-other",
        idempotency_key="idem-other",
        tenant_id="tenant-test",
    )
    operation = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-scoped",
        request_json={"portfolio_id": "pf-scoped"},
    )
    claim = service.prepare_analyze_operation_execution(
        tenant_id="tenant-test", operation_id=operation.operation_id
    )
    service.complete_operation_success(claim=claim, result_json={"ok": True})
    service.apply_workflow_action(
        rebalance_run_id=scoped_result.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        actor_id="pm-1",
        comment=None,
        correlation_id="corr-workflow-scoped",
    )

    store_wide = service.get_supportability_summary(
        store_backend="INMEMORY",
        retention_days=7,
    )
    scoped = service.get_supportability_summary(
        store_backend="INMEMORY",
        retention_days=7,
        portfolio_id="pf-scoped",
    )

    assert store_wide.run_count == 2
    assert store_wide.portfolio_scope_confirmed is False
    assert scoped.portfolio_id == "pf-scoped"
    assert scoped.portfolio_scope_confirmed is True
    assert scoped.run_count == 1
    assert scoped.operation_count == 1
    assert scoped.workflow_decision_count == 1
    assert scoped.lineage_edge_count >= 1
    assert scoped.supportability.portfolio_id == "pf-scoped"
    assert scoped.supportability.portfolio_scope_confirmed is True
    assert scoped.source_batch_fingerprint.startswith("sha256:")


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
    async_operation = _support_bundle_async_operation(
        operation=operation, membership_operation_id=operation.operation_id
    )
    assert async_operation is not None
    assert async_operation.operation_id == "dop_support_bundle_1"
    assert async_operation.is_executable is True
    assert _support_bundle_async_operation(operation=operation) is None
    assert _support_bundle_async_operation(operation=None) is None

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


def test_support_bundle_lookup_variants_project_the_same_persisted_run() -> None:
    service = _build_service()
    result = _sample_result(
        portfolio_id="pf-support-bundle-service",
        correlation_id="corr-support-bundle-service",
    )
    service.record_run(
        result=result,
        request_hash="sha256:support-bundle-service",
        portfolio_id="pf-support-bundle-service",
        idempotency_key="idem-support-bundle-service",
        tenant_id="tenant-support-bundle-service",
    )
    operation = service.submit_analyze_async(
        tenant_id="tenant-support-bundle-service",
        correlation_id=result.correlation_id,
        request_json={"portfolio_id": "pf-support-bundle-service"},
    )

    assert service.get_run(rebalance_run_id=result.rebalance_run_id).rebalance_run_id == (
        result.rebalance_run_id
    )
    assert (
        service.get_run_by_correlation(correlation_id=result.correlation_id).rebalance_run_id
        == result.rebalance_run_id
    )
    assert (
        service.get_run_by_request_hash(
            request_hash="sha256:support-bundle-service"
        ).rebalance_run_id
        == result.rebalance_run_id
    )
    assert (
        service.get_idempotency_lookup(
            idempotency_key="idem-support-bundle-service"
        ).rebalance_run_id
        == result.rebalance_run_id
    )

    direct = service.get_run_support_bundle(
        rebalance_run_id=result.rebalance_run_id,
        include_artifact=True,
        include_async_operation=True,
        include_idempotency_history=True,
    )
    by_correlation = service.get_run_support_bundle_by_correlation(
        correlation_id=result.correlation_id,
        include_artifact=False,
        include_async_operation=False,
        include_idempotency_history=False,
    )
    by_idempotency = service.get_run_support_bundle_by_idempotency(
        idempotency_key="idem-support-bundle-service",
        include_artifact=False,
        include_async_operation=False,
        include_idempotency_history=True,
    )
    by_operation = service.get_run_support_bundle_by_operation(
        operation_id=operation.operation_id,
        include_artifact=False,
        include_async_operation=True,
        include_idempotency_history=False,
    )

    assert direct.run.rebalance_run_id == result.rebalance_run_id
    assert direct.artifact is not None
    assert direct.async_operation is None
    assert direct.idempotency_history is not None
    assert by_correlation.run == direct.run
    assert by_correlation.artifact is None
    assert by_idempotency.run == direct.run
    assert by_idempotency.idempotency_history is not None
    assert by_operation.scenarios == {}
    assert by_operation.async_operation is not None
