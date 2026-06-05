from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.rebalance_runs.in_memory import (
    _supportability_summary_data,
    _unique_lineage_edge_count,
)


def test_supportability_summary_data_returns_empty_counts_and_bounds() -> None:
    summary = _supportability_summary_data(
        runs=[],
        operations=[],
        workflow_decisions={},
        lineage_edges_by_entity={},
    )

    assert summary.run_count == 0
    assert summary.operation_count == 0
    assert summary.operation_status_counts == {}
    assert summary.run_status_counts == {}
    assert summary.workflow_decision_count == 0
    assert summary.workflow_action_counts == {}
    assert summary.workflow_reason_code_counts == {}
    assert summary.lineage_edge_count == 0
    assert summary.oldest_run_created_at is None
    assert summary.newest_operation_created_at is None


def test_supportability_summary_data_aggregates_repository_snapshots() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run_one = _run("rr-summary-1", "READY", now)
    run_two = _run("rr-summary-2", "BLOCKED", now + timedelta(minutes=1))
    operation_one = _operation("dop-summary-1", "PENDING", now + timedelta(seconds=1))
    operation_two = _operation("dop-summary-2", "SUCCEEDED", now + timedelta(minutes=2))
    decision_one = _decision("dwd-summary-1", "APPROVE", "REVIEW_APPROVED", now)
    decision_two = _decision("dwd-summary-2", "APPROVE", "REVIEW_APPROVED", now)
    edge = _lineage_edge(now)

    summary = _supportability_summary_data(
        runs=[run_one, run_two],
        operations=[operation_one, operation_two],
        workflow_decisions={"rr-summary-1": [decision_one, decision_two]},
        lineage_edges_by_entity={
            "corr-summary-1": [edge],
            "rr-summary-1": [edge],
        },
    )

    assert summary.run_count == 2
    assert summary.operation_count == 2
    assert summary.run_status_counts == {"READY": 1, "BLOCKED": 1}
    assert summary.operation_status_counts == {"PENDING": 1, "SUCCEEDED": 1}
    assert summary.workflow_decision_count == 2
    assert summary.workflow_action_counts == {"APPROVE": 2}
    assert summary.workflow_reason_code_counts == {"REVIEW_APPROVED": 2}
    assert summary.lineage_edge_count == 1
    assert summary.oldest_run_created_at == now
    assert summary.newest_run_created_at == now + timedelta(minutes=1)
    assert summary.oldest_operation_created_at == now + timedelta(seconds=1)
    assert summary.newest_operation_created_at == now + timedelta(minutes=2)


def test_unique_lineage_edge_count_uses_canonical_edge_identity() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    edge = _lineage_edge(now)
    distinct_edge = _lineage_edge(now + timedelta(seconds=1))

    assert (
        _unique_lineage_edge_count(
            {
                "corr-summary-1": [edge, distinct_edge],
                "rr-summary-1": [edge],
            }
        )
        == 2
    )


def _run(run_id: str, status: str, created_at: datetime) -> DpmRunRecord:
    return DpmRunRecord(
        rebalance_run_id=run_id,
        correlation_id=f"corr-{run_id}",
        request_hash=f"sha256:{run_id}",
        idempotency_key=None,
        portfolio_id=f"pf-{run_id}",
        created_at=created_at,
        result_json={"rebalance_run_id": run_id, "status": status},
    )


def _operation(
    operation_id: str,
    status: str,
    created_at: datetime,
) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="ANALYZE_SCENARIOS",
        status=status,
        correlation_id=f"corr-{operation_id}",
        created_at=created_at,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )


def _decision(
    decision_id: str,
    action: str,
    reason_code: str,
    decided_at: datetime,
) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=decision_id,
        run_id="rr-summary-1",
        action=action,
        reason_code=reason_code,
        comment=None,
        actor_id="ops-summary",
        decided_at=decided_at,
        correlation_id=f"corr-{decision_id}",
    )


def _lineage_edge(created_at: datetime) -> DpmLineageEdgeRecord:
    return DpmLineageEdgeRecord(
        source_entity_id="corr-summary-1",
        edge_type="CORRELATION_TO_RUN",
        target_entity_id="rr-summary-1",
        created_at=created_at,
        metadata_json={"request_hash": "sha256:summary"},
    )
