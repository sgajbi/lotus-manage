from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.rebalance_runs.in_memory import (
    _WorkflowDecisionFilters,
    _all_workflow_decisions,
    _list_workflow_decisions_filtered,
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


def test_all_workflow_decisions_flattens_repository_buckets() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    decision_one = _decision("dwd-summary-1", "APPROVE", "REVIEW_APPROVED", now)
    decision_two = _decision(
        "dwd-summary-2",
        "REQUEST_CHANGES",
        "NEEDS_DETAIL",
        now + timedelta(seconds=1),
        run_id="rr-summary-2",
    )

    assert _all_workflow_decisions(
        {
            "rr-summary-1": [decision_one],
            "rr-summary-2": [decision_two],
        }
    ) == [decision_one, decision_two]


def test_list_workflow_decisions_filtered_applies_filters_and_descending_order() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    older = _decision("dwd-summary-1", "APPROVE", "REVIEW_APPROVED", now)
    newer = _decision(
        "dwd-summary-2",
        "APPROVE",
        "REVIEW_APPROVED",
        now + timedelta(seconds=1),
        actor_id="ops-target",
    )
    ignored = _decision(
        "dwd-summary-3",
        "REQUEST_CHANGES",
        "NEEDS_DETAIL",
        now + timedelta(seconds=2),
        actor_id="ops-target",
    )

    rows, cursor = _list_workflow_decisions_filtered(
        workflow_decisions={"rr-summary-1": [older, newer, ignored]},
        filters=_WorkflowDecisionFilters(
            rebalance_run_id="rr-summary-1",
            action="APPROVE",
            actor_id="ops-target",
            reason_code="REVIEW_APPROVED",
            decided_from=now,
            decided_to=now + timedelta(seconds=2),
        ),
        limit=10,
        cursor=None,
    )

    assert [decision.decision_id for decision in rows] == ["dwd-summary-2"]
    assert cursor is None


def test_list_workflow_decisions_filtered_pages_by_decision_cursor() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    older = _decision("dwd-summary-1", "APPROVE", "REVIEW_APPROVED", now)
    newer = _decision("dwd-summary-2", "APPROVE", "REVIEW_APPROVED", now + timedelta(seconds=1))
    filters = _WorkflowDecisionFilters(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
    )

    page_one, cursor = _list_workflow_decisions_filtered(
        workflow_decisions={"rr-summary-1": [older, newer]},
        filters=filters,
        limit=1,
        cursor=None,
    )
    page_two, cursor_two = _list_workflow_decisions_filtered(
        workflow_decisions={"rr-summary-1": [older, newer]},
        filters=filters,
        limit=1,
        cursor=cursor,
    )
    invalid_rows, invalid_cursor = _list_workflow_decisions_filtered(
        workflow_decisions={"rr-summary-1": [older, newer]},
        filters=filters,
        limit=10,
        cursor="dwd-missing",
    )

    assert [decision.decision_id for decision in page_one] == ["dwd-summary-2"]
    assert cursor == "dwd-summary-2"
    assert [decision.decision_id for decision in page_two] == ["dwd-summary-1"]
    assert cursor_two is None
    assert invalid_rows == []
    assert invalid_cursor is None


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
    *,
    run_id: str = "rr-summary-1",
    actor_id: str = "ops-summary",
) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=decision_id,
        run_id=run_id,
        action=action,
        reason_code=reason_code,
        comment=None,
        actor_id=actor_id,
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
