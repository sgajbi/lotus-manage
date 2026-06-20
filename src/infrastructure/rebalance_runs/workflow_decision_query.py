from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from src.core.rebalance_runs.models import DpmRunWorkflowDecisionRecord


@dataclass(frozen=True)
class WorkflowDecisionFilterQuery:
    where_sql: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class _WorkflowDecisionPredicate:
    sql: str
    arg: str


def build_workflow_decision_filter_query(
    *,
    placeholder: str,
    rebalance_run_id: Optional[str],
    action: Optional[str],
    actor_id: Optional[str],
    reason_code: Optional[str],
    decided_from: Optional[datetime],
    decided_to: Optional[datetime],
) -> WorkflowDecisionFilterQuery:
    predicates = _workflow_decision_filter_predicates(
        placeholder=placeholder,
        rebalance_run_id=rebalance_run_id,
        action=action,
        actor_id=actor_id,
        reason_code=reason_code,
        decided_from=decided_from,
        decided_to=decided_to,
    )
    return WorkflowDecisionFilterQuery(
        where_sql=_where_sql(predicates),
        args=tuple(predicate.arg for predicate in predicates),
    )


def _workflow_decision_filter_predicates(
    *,
    placeholder: str,
    rebalance_run_id: Optional[str],
    action: Optional[str],
    actor_id: Optional[str],
    reason_code: Optional[str],
    decided_from: Optional[datetime],
    decided_to: Optional[datetime],
) -> list[_WorkflowDecisionPredicate]:
    predicates = [
        predicate
        for predicate in (
            _optional_equality_predicate("run_id", rebalance_run_id, placeholder),
            _optional_equality_predicate("action", action, placeholder),
            _optional_equality_predicate("actor_id", actor_id, placeholder),
            _optional_equality_predicate("reason_code", reason_code, placeholder),
            _optional_datetime_predicate("decided_at", ">=", decided_from, placeholder),
            _optional_datetime_predicate("decided_at", "<=", decided_to, placeholder),
        )
        if predicate is not None
    ]
    return predicates


def _optional_equality_predicate(
    column_name: str,
    value: Optional[str],
    placeholder: str,
) -> _WorkflowDecisionPredicate | None:
    if value is None:
        return None
    return _WorkflowDecisionPredicate(sql=f"{column_name} = {placeholder}", arg=value)


def _optional_datetime_predicate(
    column_name: str,
    operator: str,
    value: Optional[datetime],
    placeholder: str,
) -> _WorkflowDecisionPredicate | None:
    if value is None:
        return None
    return _WorkflowDecisionPredicate(
        sql=f"{column_name} {operator} {placeholder}",
        arg=value.isoformat(),
    )


def _where_sql(predicates: list[_WorkflowDecisionPredicate]) -> str:
    if not predicates:
        return ""
    return f"WHERE {' AND '.join(predicate.sql for predicate in predicates)}"


def workflow_decision_from_row(row: Mapping[str, Any]) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=row["decision_id"],
        run_id=row["run_id"],
        action=row["action"],
        reason_code=row["reason_code"],
        comment=row["comment"],
        actor_id=row["actor_id"],
        decided_at=datetime.fromisoformat(row["decided_at"]),
        correlation_id=row["correlation_id"],
    )


def workflow_decisions_from_rows(
    rows: list[Mapping[str, Any]],
) -> list[DpmRunWorkflowDecisionRecord]:
    return [workflow_decision_from_row(row) for row in rows]


def workflow_decision_page(
    *,
    decisions: list[DpmRunWorkflowDecisionRecord],
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmRunWorkflowDecisionRecord], Optional[str]]:
    if cursor is not None:
        cursor_index = _workflow_decision_cursor_index(decisions=decisions, cursor=cursor)
        if cursor_index is None:
            return [], None
        decisions = decisions[cursor_index + 1 :]
    page = decisions[:limit]
    next_cursor = page[-1].decision_id if len(decisions) > limit else None
    return page, next_cursor


def _workflow_decision_cursor_index(
    *,
    decisions: list[DpmRunWorkflowDecisionRecord],
    cursor: str,
) -> int | None:
    return next(
        (index for index, row in enumerate(decisions) if row.decision_id == cursor),
        None,
    )
