import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmSupportabilitySummaryData,
)
from src.core.dpm_runs.repository import DpmRunRepository


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
            rows = list(self._runs.values())
            if created_from is not None:
                rows = [row for row in rows if row.created_at >= created_from]
            if created_to is not None:
                rows = [row for row in rows if row.created_at <= created_to]
            if status is not None:
                rows = [row for row in rows if str(row.result_json.get("status", "")) == status]
            if request_hash is not None:
                rows = [row for row in rows if row.request_hash == request_hash]
            if portfolio_id is not None:
                rows = [row for row in rows if row.portfolio_id == portfolio_id]
            rows = sorted(
                rows, key=lambda item: (item.created_at, item.rebalance_run_id), reverse=True
            )
            if cursor is not None:
                cursor_index = next(
                    (index for index, row in enumerate(rows) if row.rebalance_run_id == cursor),
                    None,
                )
                if cursor_index is None:
                    return [], None
                rows = rows[cursor_index + 1 :]
            page = rows[:limit]
            next_cursor = page[-1].rebalance_run_id if len(rows) > limit else None
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
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
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
            rows = list(self._operations.values())
            if created_from is not None:
                rows = [row for row in rows if row.created_at >= created_from]
            if created_to is not None:
                rows = [row for row in rows if row.created_at <= created_to]
            if operation_type is not None:
                rows = [row for row in rows if row.operation_type == operation_type]
            if status is not None:
                rows = [row for row in rows if row.status == status]
            if correlation_id is not None:
                rows = [row for row in rows if row.correlation_id == correlation_id]
            rows = sorted(
                rows,
                key=lambda item: (item.created_at, item.operation_id),
                reverse=True,
            )
            if cursor is not None:
                cursor_index = next(
                    (index for index, row in enumerate(rows) if row.operation_id == cursor),
                    None,
                )
                if cursor_index is None:
                    return [], None
                rows = rows[cursor_index + 1 :]
            page = rows[:limit]
            next_cursor = page[-1].operation_id if len(rows) > limit else None
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
            rows = [
                decision
                for decisions in self._workflow_decisions.values()
                for decision in decisions
            ]
            if rebalance_run_id is not None:
                rows = [row for row in rows if row.run_id == rebalance_run_id]
            if action is not None:
                rows = [row for row in rows if row.action == action]
            if actor_id is not None:
                rows = [row for row in rows if row.actor_id == actor_id]
            if reason_code is not None:
                rows = [row for row in rows if row.reason_code == reason_code]
            if decided_from is not None:
                rows = [row for row in rows if row.decided_at >= decided_from]
            if decided_to is not None:
                rows = [row for row in rows if row.decided_at <= decided_to]
            rows = sorted(rows, key=lambda row: (row.decided_at, row.decision_id), reverse=True)
            if cursor is not None:
                cursor_index = next(
                    (index for index, row in enumerate(rows) if row.decision_id == cursor),
                    None,
                )
                if cursor_index is None:
                    return [], None
                rows = rows[cursor_index + 1 :]
            page = rows[:limit]
            next_cursor = page[-1].decision_id if len(rows) > limit else None
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
            runs = list(self._runs.values())
            operations = list(self._operations.values())
            operation_status_counts: dict[str, int] = {}
            run_status_counts: dict[str, int] = {}
            for run in runs:
                status = str(run.result_json.get("status", ""))
                if status:
                    run_status_counts[status] = run_status_counts.get(status, 0) + 1
            for operation in operations:
                operation_status_counts[operation.status] = (
                    operation_status_counts.get(operation.status, 0) + 1
                )
            workflow_decision_count = sum(
                len(decisions) for decisions in self._workflow_decisions.values()
            )
            workflow_action_counts: dict[str, int] = {}
            workflow_reason_code_counts: dict[str, int] = {}
            for decisions in self._workflow_decisions.values():
                for decision in decisions:
                    workflow_action_counts[decision.action] = (
                        workflow_action_counts.get(decision.action, 0) + 1
                    )
                    workflow_reason_code_counts[decision.reason_code] = (
                        workflow_reason_code_counts.get(decision.reason_code, 0) + 1
                    )
            unique_lineage_edge_keys = {
                (
                    edge.source_entity_id,
                    edge.edge_type,
                    edge.target_entity_id,
                    edge.created_at.isoformat(),
                    json.dumps(edge.metadata_json, sort_keys=True, separators=(",", ":")),
                )
                for edges in self._lineage_edges_by_entity.values()
                for edge in edges
            }
            lineage_edge_count = len(unique_lineage_edge_keys)

            run_created_values = [run.created_at for run in runs]
            operation_created_values = [operation.created_at for operation in operations]
            return DpmSupportabilitySummaryData(
                run_count=len(runs),
                operation_count=len(operations),
                operation_status_counts=operation_status_counts,
                run_status_counts=run_status_counts,
                workflow_decision_count=workflow_decision_count,
                workflow_action_counts=workflow_action_counts,
                workflow_reason_code_counts=workflow_reason_code_counts,
                lineage_edge_count=lineage_edge_count,
                oldest_run_created_at=min(run_created_values) if run_created_values else None,
                newest_run_created_at=max(run_created_values) if run_created_values else None,
                oldest_operation_created_at=(
                    min(operation_created_values) if operation_created_values else None
                ),
                newest_operation_created_at=(
                    max(operation_created_values) if operation_created_values else None
                ),
            )

    def purge_expired_runs(self, *, retention_days: int, now: datetime) -> int:
        with self._lock:
            if retention_days < 1:
                return 0
            cutoff = now.astimezone(timezone.utc) - timedelta(days=retention_days)
            expired_runs = [run for run in self._runs.values() if run.created_at < cutoff]
            if not expired_runs:
                return 0

            expired_run_ids = {run.rebalance_run_id for run in expired_runs}
            expired_correlation_ids = {run.correlation_id for run in expired_runs}
            expired_idempotency_keys = {
                run.idempotency_key for run in expired_runs if run.idempotency_key
            }

            for run in expired_runs:
                self._runs.pop(run.rebalance_run_id, None)
                self._run_artifacts.pop(run.rebalance_run_id, None)
                if self._run_id_by_correlation.get(run.correlation_id) == run.rebalance_run_id:
                    self._run_id_by_correlation.pop(run.correlation_id, None)

            for idempotency_key, mapping in list(self._idempotency.items()):
                if mapping.rebalance_run_id in expired_run_ids:
                    self._idempotency.pop(idempotency_key, None)
                    expired_idempotency_keys.add(idempotency_key)

            for idempotency_key, history in list(self._idempotency_history.items()):
                filtered = [row for row in history if row.rebalance_run_id not in expired_run_ids]
                if filtered:
                    self._idempotency_history[idempotency_key] = filtered
                else:
                    self._idempotency_history.pop(idempotency_key, None)

            for run_id in expired_run_ids:
                self._workflow_decisions.pop(run_id, None)

            expired_entities = expired_run_ids | expired_correlation_ids | expired_idempotency_keys
            for entity_id, edges in list(self._lineage_edges_by_entity.items()):
                filtered_edges = [
                    edge
                    for edge in edges
                    if edge.source_entity_id not in expired_entities
                    and edge.target_entity_id not in expired_entities
                ]
                if filtered_edges:
                    self._lineage_edges_by_entity[entity_id] = filtered_edges
                else:
                    self._lineage_edges_by_entity.pop(entity_id, None)

            return len(expired_runs)
