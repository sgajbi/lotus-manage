from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from src.core.rebalance_runs.models import DpmRunWorkflowDecisionRecord


@dataclass(frozen=True)
class WorkflowDecisionFilterQuery:
    where_sql: str
    args: tuple[str, ...]


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
    where_clauses: list[str] = []
    args: list[str] = []
    for column_name, value in (
        ("run_id", rebalance_run_id),
        ("action", action),
        ("actor_id", actor_id),
        ("reason_code", reason_code),
    ):
        if value is not None:
            where_clauses.append(f"{column_name} = {placeholder}")
            args.append(value)
    if decided_from is not None:
        where_clauses.append(f"decided_at >= {placeholder}")
        args.append(decided_from.isoformat())
    if decided_to is not None:
        where_clauses.append(f"decided_at <= {placeholder}")
        args.append(decided_to.isoformat())
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return WorkflowDecisionFilterQuery(where_sql=where_sql, args=tuple(args))


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
        cursor_index = next(
            (index for index, row in enumerate(decisions) if row.decision_id == cursor),
            None,
        )
        if cursor_index is None:
            return [], None
        decisions = decisions[cursor_index + 1 :]
    page = decisions[:limit]
    next_cursor = page[-1].decision_id if len(decisions) > limit else None
    return page, next_cursor
