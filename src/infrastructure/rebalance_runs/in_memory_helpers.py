import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar, cast

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmSupportabilitySummaryData,
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class _ExpiredRunIdentities:
    run_ids: set[str]
    correlation_ids: set[str]
    idempotency_keys: set[str]

    @property
    def lineage_entity_ids(self) -> set[str]:
        return self.run_ids | self.correlation_ids | self.idempotency_keys


@dataclass(frozen=True)
class _WorkflowDecisionFilters:
    rebalance_run_id: str | None
    action: str | None
    actor_id: str | None
    reason_code: str | None
    decided_from: datetime | None
    decided_to: datetime | None


@dataclass(frozen=True)
class _RunListFilters:
    created_from: datetime | None
    created_to: datetime | None
    status: str | None
    request_hash: str | None
    portfolio_id: str | None


@dataclass(frozen=True)
class _OperationListFilters:
    created_from: datetime | None
    created_to: datetime | None
    operation_type: str | None
    status: str | None
    correlation_id: str | None


def _optional_datetime_is_on_or_after(
    actual: datetime,
    lower_bound: datetime | None,
) -> bool:
    return lower_bound is None or actual >= lower_bound


def _optional_datetime_is_on_or_before(
    actual: datetime,
    upper_bound: datetime | None,
) -> bool:
    return upper_bound is None or actual <= upper_bound


def _run_matches_filters(run: DpmRunRecord, filters: _RunListFilters) -> bool:
    return all(
        (
            _optional_datetime_is_on_or_after(run.created_at, filters.created_from),
            _optional_datetime_is_on_or_before(run.created_at, filters.created_to),
            _optional_value_matches(str(run.result_json.get("status", "")), filters.status),
            _optional_value_matches(run.request_hash, filters.request_hash),
            _optional_value_matches(run.portfolio_id, filters.portfolio_id),
        )
    )


def _operation_matches_filters(
    operation: DpmAsyncOperationRecord,
    filters: _OperationListFilters,
) -> bool:
    return all(
        (
            _optional_datetime_is_on_or_after(operation.created_at, filters.created_from),
            _optional_datetime_is_on_or_before(operation.created_at, filters.created_to),
            _optional_value_matches(operation.operation_type, filters.operation_type),
            _optional_value_matches(operation.status, filters.status),
            _optional_value_matches(operation.correlation_id, filters.correlation_id),
        )
    )


def _sorted_filtered_runs(
    runs: Sequence[DpmRunRecord],
    filters: _RunListFilters,
) -> list[DpmRunRecord]:
    return sorted(
        (run for run in runs if _run_matches_filters(run, filters)),
        key=lambda item: (item.created_at, item.rebalance_run_id),
        reverse=True,
    )


def _sorted_filtered_operations(
    operations: Sequence[DpmAsyncOperationRecord],
    filters: _OperationListFilters,
) -> list[DpmAsyncOperationRecord]:
    return sorted(
        (operation for operation in operations if _operation_matches_filters(operation, filters)),
        key=lambda item: (item.created_at, item.operation_id),
        reverse=True,
    )


def _cursor_page(
    rows: Sequence[_T],
    *,
    limit: int,
    cursor: str | None,
    identity: Callable[[_T], str],
) -> tuple[list[_T], str | None]:
    page_source = list(rows)
    if cursor is not None:
        cursor_index = next(
            (index for index, row in enumerate(page_source) if identity(row) == cursor),
            None,
        )
        if cursor_index is None:
            return [], None
        page_source = page_source[cursor_index + 1 :]
    page = page_source[:limit]
    next_cursor = identity(page[-1]) if len(page_source) > limit else None
    return page, next_cursor


def _list_runs_filtered(
    *,
    runs: Sequence[DpmRunRecord],
    filters: _RunListFilters,
    limit: int,
    cursor: str | None,
) -> tuple[list[DpmRunRecord], str | None]:
    rows = _sorted_filtered_runs(runs, filters)
    return _cursor_page(
        rows,
        limit=limit,
        cursor=cursor,
        identity=lambda row: row.rebalance_run_id,
    )


def _list_operations_filtered(
    *,
    operations: Sequence[DpmAsyncOperationRecord],
    filters: _OperationListFilters,
    limit: int,
    cursor: str | None,
) -> tuple[list[DpmAsyncOperationRecord], str | None]:
    rows = _sorted_filtered_operations(operations, filters)
    return _cursor_page(
        rows,
        limit=limit,
        cursor=cursor,
        identity=lambda row: row.operation_id,
    )


def _expired_runs(
    *,
    runs: dict[str, DpmRunRecord],
    cutoff: datetime,
) -> list[DpmRunRecord]:
    return [run for run in runs.values() if run.created_at < cutoff]


def _expired_run_identities(expired_runs: list[DpmRunRecord]) -> _ExpiredRunIdentities:
    return _ExpiredRunIdentities(
        run_ids={run.rebalance_run_id for run in expired_runs},
        correlation_ids={run.correlation_id for run in expired_runs},
        idempotency_keys={run.idempotency_key for run in expired_runs if run.idempotency_key},
    )


def _purge_expired_run_records(
    *,
    runs: dict[str, DpmRunRecord],
    run_artifacts: dict[str, dict[str, Any]],
    run_id_by_correlation: dict[str, str],
    expired_runs: list[DpmRunRecord],
) -> None:
    for run in expired_runs:
        runs.pop(run.rebalance_run_id, None)
        run_artifacts.pop(run.rebalance_run_id, None)
        if run_id_by_correlation.get(run.correlation_id) == run.rebalance_run_id:
            run_id_by_correlation.pop(run.correlation_id, None)


def _purge_expired_idempotency_mappings(
    *,
    idempotency: dict[str, DpmRunIdempotencyRecord],
    expired_run_ids: set[str],
    expired_idempotency_keys: set[str],
) -> None:
    for idempotency_key, mapping in list(idempotency.items()):
        if mapping.rebalance_run_id in expired_run_ids:
            idempotency.pop(idempotency_key, None)
            expired_idempotency_keys.add(idempotency_key)


def _purge_expired_idempotency_history(
    *,
    idempotency_history: dict[str, list[DpmRunIdempotencyHistoryRecord]],
    expired_run_ids: set[str],
) -> None:
    for idempotency_key, history in list(idempotency_history.items()):
        filtered = [row for row in history if row.rebalance_run_id not in expired_run_ids]
        if filtered:
            idempotency_history[idempotency_key] = filtered
        else:
            idempotency_history.pop(idempotency_key, None)


def _purge_expired_lineage_edges(
    *,
    lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]],
    expired_entities: set[str],
) -> None:
    for entity_id, edges in list(lineage_edges_by_entity.items()):
        filtered_edges = [
            edge
            for edge in edges
            if edge.source_entity_id not in expired_entities
            and edge.target_entity_id not in expired_entities
        ]
        if filtered_edges:
            lineage_edges_by_entity[entity_id] = filtered_edges
        else:
            lineage_edges_by_entity.pop(entity_id, None)


def _status_counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _workflow_decision_counts(
    workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]],
) -> tuple[int, dict[str, int], dict[str, int]]:
    decisions = [decision for rows in workflow_decisions.values() for decision in rows]
    return (
        len(decisions),
        _status_counts([decision.action for decision in decisions]),
        _status_counts([decision.reason_code for decision in decisions]),
    )


def _lineage_edge_identity(edge: DpmLineageEdgeRecord) -> tuple[str, str, str, str, str]:
    return (
        edge.source_entity_id,
        edge.edge_type,
        edge.target_entity_id,
        edge.created_at.isoformat(),
        json.dumps(edge.metadata_json, sort_keys=True, separators=(",", ":")),
    )


def _unique_lineage_edge_count(
    lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]],
) -> int:
    return len(
        {
            _lineage_edge_identity(edge)
            for edges in lineage_edges_by_entity.values()
            for edge in edges
        }
    )


def _datetime_bounds(values: list[datetime]) -> tuple[datetime | None, datetime | None]:
    if not values:
        return None, None
    return min(values), max(values)


def _supportability_summary_data(
    *,
    runs: list[DpmRunRecord],
    operations: list[DpmAsyncOperationRecord],
    workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]],
    lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]],
    portfolio_id: str | None = None,
) -> DpmSupportabilitySummaryData:
    scoped_runs = _scoped_runs(runs=runs, portfolio_id=portfolio_id)
    scoped_run_ids = {run.rebalance_run_id for run in scoped_runs}
    scoped_correlation_ids = {run.correlation_id for run in scoped_runs}
    scoped_idempotency_keys = {run.idempotency_key for run in scoped_runs if run.idempotency_key}
    scoped_operations = _scoped_operations(
        operations=operations,
        portfolio_id=portfolio_id,
        correlation_ids=scoped_correlation_ids,
    )
    scoped_operation_ids = {operation.operation_id for operation in scoped_operations}
    scoped_operation_correlation_ids = {
        operation.correlation_id for operation in scoped_operations if operation.correlation_id
    }
    scoped_workflow_decisions = _scoped_workflow_decisions(
        workflow_decisions=workflow_decisions,
        portfolio_id=portfolio_id,
        run_ids=scoped_run_ids,
    )
    scoped_lineage_edges_by_entity = _scoped_lineage_edges(
        lineage_edges_by_entity=lineage_edges_by_entity,
        portfolio_id=portfolio_id,
        entity_ids=(
            scoped_run_ids
            | scoped_correlation_ids
            | scoped_idempotency_keys
            | scoped_operation_ids
            | scoped_operation_correlation_ids
        ),
    )
    workflow_decision_count, workflow_action_counts, workflow_reason_code_counts = (
        _workflow_decision_counts(scoped_workflow_decisions)
    )
    oldest_run_created_at, newest_run_created_at = _datetime_bounds(
        [run.created_at for run in scoped_runs]
    )
    oldest_operation_created_at, newest_operation_created_at = _datetime_bounds(
        [operation.created_at for operation in scoped_operations]
    )
    return DpmSupportabilitySummaryData(
        run_count=len(scoped_runs),
        operation_count=len(scoped_operations),
        operation_status_counts=_status_counts(
            [operation.status for operation in scoped_operations]
        ),
        run_status_counts=_status_counts(
            [str(run.result_json.get("status", "")) for run in scoped_runs]
        ),
        workflow_decision_count=workflow_decision_count,
        workflow_action_counts=workflow_action_counts,
        workflow_reason_code_counts=workflow_reason_code_counts,
        lineage_edge_count=_unique_lineage_edge_count(scoped_lineage_edges_by_entity),
        oldest_run_created_at=oldest_run_created_at,
        newest_run_created_at=newest_run_created_at,
        oldest_operation_created_at=oldest_operation_created_at,
        newest_operation_created_at=newest_operation_created_at,
    )


def _scoped_runs(*, runs: list[DpmRunRecord], portfolio_id: str | None) -> list[DpmRunRecord]:
    if portfolio_id is None:
        return runs
    return [run for run in runs if run.portfolio_id == portfolio_id]


def _scoped_operations(
    *,
    operations: list[DpmAsyncOperationRecord],
    portfolio_id: str | None,
    correlation_ids: set[str],
) -> list[DpmAsyncOperationRecord]:
    if portfolio_id is None:
        return operations
    return [
        operation
        for operation in operations
        if _operation_matches_portfolio_scope(
            operation=operation,
            portfolio_id=portfolio_id,
            correlation_ids=correlation_ids,
        )
    ]


def _operation_matches_portfolio_scope(
    *,
    operation: DpmAsyncOperationRecord,
    portfolio_id: str,
    correlation_ids: set[str],
) -> bool:
    request_portfolio_id = _operation_request_portfolio_id(operation.request_json)
    if request_portfolio_id == portfolio_id:
        return True
    if operation.correlation_id not in correlation_ids:
        return False
    return request_portfolio_id is None


def _operation_request_portfolio_id(request_json: dict[str, object] | None) -> str | None:
    if request_json is None:
        return None
    batch_request = request_json.get("batch_request")
    if isinstance(batch_request, dict):
        portfolio_snapshot = batch_request.get("portfolio_snapshot")
        if isinstance(portfolio_snapshot, dict) and isinstance(
            portfolio_snapshot.get("portfolio_id"),
            str,
        ):
            portfolio_id = cast(str, portfolio_snapshot["portfolio_id"])
            return portfolio_id
    portfolio_snapshot = request_json.get("portfolio_snapshot")
    if isinstance(portfolio_snapshot, dict) and isinstance(
        portfolio_snapshot.get("portfolio_id"),
        str,
    ):
        portfolio_id = cast(str, portfolio_snapshot["portfolio_id"])
        return portfolio_id
    return None


def _scoped_workflow_decisions(
    *,
    workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]],
    portfolio_id: str | None,
    run_ids: set[str],
) -> dict[str, list[DpmRunWorkflowDecisionRecord]]:
    if portfolio_id is None:
        return workflow_decisions
    return {
        run_id: decisions for run_id, decisions in workflow_decisions.items() if run_id in run_ids
    }


def _scoped_lineage_edges(
    *,
    lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]],
    portfolio_id: str | None,
    entity_ids: set[str],
) -> dict[str, list[DpmLineageEdgeRecord]]:
    if portfolio_id is None:
        return lineage_edges_by_entity
    return {
        entity_id: edges
        for entity_id, edges in lineage_edges_by_entity.items()
        if entity_id in entity_ids
    }


def _all_workflow_decisions(
    workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]],
) -> list[DpmRunWorkflowDecisionRecord]:
    return [decision for decisions in workflow_decisions.values() for decision in decisions]


def _workflow_decision_matches_filters(
    decision: DpmRunWorkflowDecisionRecord,
    filters: _WorkflowDecisionFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(decision.run_id, filters.rebalance_run_id),
            _optional_value_matches(decision.action, filters.action),
            _optional_value_matches(decision.actor_id, filters.actor_id),
            _optional_value_matches(decision.reason_code, filters.reason_code),
            _decided_at_is_on_or_after(decision.decided_at, filters.decided_from),
            _decided_at_is_on_or_before(decision.decided_at, filters.decided_to),
        )
    )


def _optional_value_matches(actual: str, expected: str | None) -> bool:
    return expected is None or actual == expected


def _decided_at_is_on_or_after(decided_at: datetime, lower_bound: datetime | None) -> bool:
    return lower_bound is None or decided_at >= lower_bound


def _decided_at_is_on_or_before(decided_at: datetime, upper_bound: datetime | None) -> bool:
    return upper_bound is None or decided_at <= upper_bound


def _filter_workflow_decisions(
    decisions: list[DpmRunWorkflowDecisionRecord],
    filters: _WorkflowDecisionFilters,
) -> list[DpmRunWorkflowDecisionRecord]:
    return [
        decision for decision in decisions if _workflow_decision_matches_filters(decision, filters)
    ]


def _sorted_workflow_decisions(
    decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[DpmRunWorkflowDecisionRecord]:
    return sorted(
        decisions, key=lambda decision: (decision.decided_at, decision.decision_id), reverse=True
    )


def _workflow_decision_page(
    decisions: list[DpmRunWorkflowDecisionRecord],
    *,
    limit: int,
    cursor: str | None,
) -> tuple[list[DpmRunWorkflowDecisionRecord], str | None]:
    rows = decisions
    if cursor is not None:
        cursor_index = next(
            (index for index, decision in enumerate(rows) if decision.decision_id == cursor),
            None,
        )
        if cursor_index is None:
            return [], None
        rows = rows[cursor_index + 1 :]
    page = rows[:limit]
    next_cursor = page[-1].decision_id if len(rows) > limit else None
    return page, next_cursor


def _list_workflow_decisions_filtered(
    *,
    workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]],
    filters: _WorkflowDecisionFilters,
    limit: int,
    cursor: str | None,
) -> tuple[list[DpmRunWorkflowDecisionRecord], str | None]:
    decisions = _all_workflow_decisions(workflow_decisions)
    filtered = _filter_workflow_decisions(decisions, filters)
    sorted_decisions = _sorted_workflow_decisions(filtered)
    return _workflow_decision_page(sorted_decisions, limit=limit, cursor=cursor)
