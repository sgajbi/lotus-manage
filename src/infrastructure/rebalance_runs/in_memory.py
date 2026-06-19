import json
from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional, TypeVar

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmSupportabilitySummaryData,
)
from src.core.rebalance_runs.repository import DpmRunRepository, DpmRunRepositoryConflictError

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
) -> DpmSupportabilitySummaryData:
    workflow_decision_count, workflow_action_counts, workflow_reason_code_counts = (
        _workflow_decision_counts(workflow_decisions)
    )
    oldest_run_created_at, newest_run_created_at = _datetime_bounds(
        [run.created_at for run in runs]
    )
    oldest_operation_created_at, newest_operation_created_at = _datetime_bounds(
        [operation.created_at for operation in operations]
    )
    return DpmSupportabilitySummaryData(
        run_count=len(runs),
        operation_count=len(operations),
        operation_status_counts=_status_counts([operation.status for operation in operations]),
        run_status_counts=_status_counts([str(run.result_json.get("status", "")) for run in runs]),
        workflow_decision_count=workflow_decision_count,
        workflow_action_counts=workflow_action_counts,
        workflow_reason_code_counts=workflow_reason_code_counts,
        lineage_edge_count=_unique_lineage_edge_count(lineage_edges_by_entity),
        oldest_run_created_at=oldest_run_created_at,
        newest_run_created_at=newest_run_created_at,
        oldest_operation_created_at=oldest_operation_created_at,
        newest_operation_created_at=newest_operation_created_at,
    )


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


class InMemoryDpmRunRepository(DpmRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, DpmRunRecord] = {}
        self._run_id_by_correlation: dict[str, str] = {}
        self._idempotency: dict[str, DpmRunIdempotencyRecord] = {}
        self._idempotency_history: dict[str, list[DpmRunIdempotencyHistoryRecord]] = {}
        self._run_artifacts: dict[str, dict[str, Any]] = {}
        self._operations: dict[str, DpmAsyncOperationRecord] = {}
        self._operation_by_correlation: dict[str, str] = {}
        self._workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]] = {}
        self._lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]] = {}

    def save_run(self, run: DpmRunRecord) -> None:
        with self._lock:
            self._runs[run.rebalance_run_id] = deepcopy(run)
            self._run_id_by_correlation[run.correlation_id] = run.rebalance_run_id

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run = self._runs.get(rebalance_run_id)
            return deepcopy(run) if run is not None else None

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run_id = self._run_id_by_correlation.get(correlation_id)
            if run_id is None:
                return None
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    def get_run_by_request_hash(self, *, request_hash: str) -> Optional[DpmRunRecord]:
        with self._lock:
            matching = [run for run in self._runs.values() if run.request_hash == request_hash]
            if not matching:
                return None
            latest = max(matching, key=lambda item: (item.created_at, item.rebalance_run_id))
            return deepcopy(latest)

    def list_runs(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        status: Optional[str],
        request_hash: Optional[str],
        portfolio_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunRecord], Optional[str]]:
        with self._lock:
            page, next_cursor = _list_runs_filtered(
                runs=list(self._runs.values()),
                filters=_RunListFilters(
                    created_from=created_from,
                    created_to=created_to,
                    status=status,
                    request_hash=request_hash,
                    portfolio_id=portfolio_id,
                ),
                limit=limit,
                cursor=cursor,
            )
            return [deepcopy(row) for row in page], next_cursor

    def save_run_artifact(self, *, rebalance_run_id: str, artifact_json: dict[str, Any]) -> None:
        with self._lock:
            self._run_artifacts[rebalance_run_id] = deepcopy(artifact_json)

    def get_run_artifact(self, *, rebalance_run_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            artifact = self._run_artifacts.get(rebalance_run_id)
            return deepcopy(artifact) if artifact is not None else None

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None:
        with self._lock:
            self._idempotency[record.idempotency_key] = deepcopy(record)

    def get_idempotency_mapping(self, *, idempotency_key: str) -> Optional[DpmRunIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None:
        with self._lock:
            history = self._idempotency_history.setdefault(record.idempotency_key, [])
            history.append(deepcopy(record))

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]:
        with self._lock:
            history = self._idempotency_history.get(idempotency_key, [])
            return [deepcopy(item) for item in history]

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._save_operation(operation)

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._save_operation(operation)

    def _save_operation(self, operation: DpmAsyncOperationRecord) -> None:
        existing_operation_id = self._operation_by_correlation.get(operation.correlation_id)
        if existing_operation_id is not None and existing_operation_id != operation.operation_id:
            raise DpmRunRepositoryConflictError("DPM_ASYNC_OPERATION_CORRELATION_CONFLICT")
        self._operations[operation.operation_id] = deepcopy(operation)
        self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_correlation.get(correlation_id)
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def list_operations(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        operation_type: Optional[str],
        status: Optional[str],
        correlation_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmAsyncOperationRecord], Optional[str]]:
        with self._lock:
            page, next_cursor = _list_operations_filtered(
                operations=list(self._operations.values()),
                filters=_OperationListFilters(
                    created_from=created_from,
                    created_to=created_to,
                    operation_type=operation_type,
                    status=status,
                    correlation_id=correlation_id,
                ),
                limit=limit,
                cursor=cursor,
            )
            return [deepcopy(row) for row in page], next_cursor

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int:
        with self._lock:
            cutoff = now.astimezone(timezone.utc) - timedelta(seconds=ttl_seconds)
            removed = 0
            for operation_id, operation in list(self._operations.items()):
                anchor = operation.finished_at or operation.created_at
                if anchor < cutoff:
                    self._operations.pop(operation_id, None)
                    if self._operation_by_correlation.get(operation.correlation_id) == operation_id:
                        self._operation_by_correlation.pop(operation.correlation_id, None)
                    removed += 1
            return removed

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None:
        with self._lock:
            decisions = self._workflow_decisions.setdefault(decision.run_id, [])
            decisions.append(deepcopy(decision))

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]:
        with self._lock:
            decisions = self._workflow_decisions.get(rebalance_run_id, [])
            return [deepcopy(decision) for decision in decisions]

    def list_workflow_decisions_filtered(
        self,
        *,
        rebalance_run_id: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        reason_code: Optional[str],
        decided_from: Optional[datetime],
        decided_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunWorkflowDecisionRecord], Optional[str]]:
        with self._lock:
            page, next_cursor = _list_workflow_decisions_filtered(
                workflow_decisions=self._workflow_decisions,
                filters=_WorkflowDecisionFilters(
                    rebalance_run_id=rebalance_run_id,
                    action=action,
                    actor_id=actor_id,
                    reason_code=reason_code,
                    decided_from=decided_from,
                    decided_to=decided_to,
                ),
                limit=limit,
                cursor=cursor,
            )
            return [deepcopy(row) for row in page], next_cursor

    def append_lineage_edge(self, edge: DpmLineageEdgeRecord) -> None:
        with self._lock:
            source_edges = self._lineage_edges_by_entity.setdefault(edge.source_entity_id, [])
            source_edges.append(deepcopy(edge))
            if edge.target_entity_id != edge.source_entity_id:
                target_edges = self._lineage_edges_by_entity.setdefault(edge.target_entity_id, [])
                target_edges.append(deepcopy(edge))

    def list_lineage_edges(self, *, entity_id: str) -> list[DpmLineageEdgeRecord]:
        with self._lock:
            edges = self._lineage_edges_by_entity.get(entity_id, [])
            return [deepcopy(edge) for edge in edges]

    def get_supportability_summary(self) -> DpmSupportabilitySummaryData:
        with self._lock:
            return _supportability_summary_data(
                runs=list(self._runs.values()),
                operations=list(self._operations.values()),
                workflow_decisions=self._workflow_decisions,
                lineage_edges_by_entity=self._lineage_edges_by_entity,
            )

    def purge_expired_runs(self, *, retention_days: int, now: datetime) -> int:
        with self._lock:
            if retention_days < 1:
                return 0
            cutoff = now.astimezone(timezone.utc) - timedelta(days=retention_days)
            expired_runs = _expired_runs(runs=self._runs, cutoff=cutoff)
            if not expired_runs:
                return 0

            expired_identities = _expired_run_identities(expired_runs)
            _purge_expired_run_records(
                runs=self._runs,
                run_artifacts=self._run_artifacts,
                run_id_by_correlation=self._run_id_by_correlation,
                expired_runs=expired_runs,
            )
            _purge_expired_idempotency_mappings(
                idempotency=self._idempotency,
                expired_run_ids=expired_identities.run_ids,
                expired_idempotency_keys=expired_identities.idempotency_keys,
            )
            _purge_expired_idempotency_history(
                idempotency_history=self._idempotency_history,
                expired_run_ids=expired_identities.run_ids,
            )
            for run_id in expired_identities.run_ids:
                self._workflow_decisions.pop(run_id, None)
            _purge_expired_lineage_edges(
                lineage_edges_by_entity=self._lineage_edges_by_entity,
                expired_entities=expired_identities.lineage_entity_ids,
            )

            return len(expired_runs)
