from datetime import datetime, timezone

from src.core.rebalance_runs.models import DpmRunWorkflowDecisionRecord
from src.infrastructure.rebalance_runs.workflow_decision_query import (
    _optional_datetime_predicate,
    _optional_equality_predicate,
    _where_sql,
    _workflow_decision_cursor_index,
    build_workflow_decision_filter_query,
    workflow_decision_from_row,
    workflow_decision_page,
)


def _decision(decision_id: str) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=decision_id,
        run_id="rr_query_1",
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="ops_query",
        decided_at=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc),
        correlation_id=f"corr_{decision_id}",
    )


def test_workflow_decision_filter_query_uses_backend_placeholder_and_ordered_args() -> None:
    decided_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    decided_to = datetime(2026, 2, 21, 12, 0, tzinfo=timezone.utc)

    query = build_workflow_decision_filter_query(
        placeholder="%s",
        rebalance_run_id="rr_query_1",
        action="APPROVE",
        actor_id="ops_query",
        reason_code="REVIEW_APPROVED",
        decided_from=decided_from,
        decided_to=decided_to,
    )

    assert query.where_sql == (
        "WHERE run_id = %s AND action = %s AND actor_id = %s AND reason_code = %s "
        "AND decided_at >= %s AND decided_at <= %s"
    )
    assert query.args == (
        "rr_query_1",
        "APPROVE",
        "ops_query",
        "REVIEW_APPROVED",
        decided_from.isoformat(),
        decided_to.isoformat(),
    )
    assert (
        build_workflow_decision_filter_query(
            placeholder="?",
            rebalance_run_id=None,
            action=None,
            actor_id=None,
            reason_code=None,
            decided_from=None,
            decided_to=None,
        ).where_sql
        == ""
    )


def test_workflow_decision_predicate_helpers_preserve_sql_and_args() -> None:
    decided_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    equality = _optional_equality_predicate("actor_id", "ops_query", "?")
    from_predicate = _optional_datetime_predicate("decided_at", ">=", decided_from, "?")

    assert equality is not None
    assert equality.sql == "actor_id = ?"
    assert equality.arg == "ops_query"
    assert from_predicate is not None
    assert from_predicate.sql == "decided_at >= ?"
    assert from_predicate.arg == decided_from.isoformat()
    assert _optional_equality_predicate("actor_id", None, "?") is None
    assert _optional_datetime_predicate("decided_at", "<=", None, "?") is None
    assert _where_sql([equality, from_predicate]) == "WHERE actor_id = ? AND decided_at >= ?"
    assert _where_sql([]) == ""


def test_workflow_decision_row_and_page_helpers_preserve_repository_contract() -> None:
    decision = workflow_decision_from_row(
        {
            "decision_id": "dwd_query_1",
            "run_id": "rr_query_1",
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "ops_query",
            "decided_at": "2026-02-20T12:00:00+00:00",
            "correlation_id": "corr_query_1",
        }
    )

    assert decision.decision_id == "dwd_query_1"
    assert decision.decided_at == datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)

    page, cursor = workflow_decision_page(
        decisions=[_decision("dwd_3"), _decision("dwd_2"), _decision("dwd_1")],
        limit=1,
        cursor="dwd_3",
    )

    assert [item.decision_id for item in page] == ["dwd_2"]
    assert cursor == "dwd_2"
    assert workflow_decision_page(
        decisions=[_decision("dwd_1")],
        limit=10,
        cursor="missing",
    ) == ([], None)


def test_workflow_decision_cursor_index_finds_stable_cursor_position() -> None:
    decisions = [_decision("dwd_3"), _decision("dwd_2"), _decision("dwd_1")]

    assert _workflow_decision_cursor_index(decisions=decisions, cursor="dwd_2") == 1
    assert _workflow_decision_cursor_index(decisions=decisions, cursor="missing") is None
