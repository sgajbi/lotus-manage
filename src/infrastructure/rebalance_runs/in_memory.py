from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

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
from src.infrastructure.rebalance_runs.in_memory_helpers import (
    _OperationListFilters,
    _RunListFilters,
    _WorkflowDecisionFilters,
    _expired_run_identities,
    _expired_runs,
    _list_operations_filtered,
    _list_runs_filtered,
    _list_workflow_decisions_filtered,
    _purge_expired_idempotency_history,
    _purge_expired_idempotency_mappings,
    _purge_expired_lineage_edges,
    _purge_expired_run_records,
    _supportability_summary_data,
)


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

    def get_supportability_summary(
        self, *, portfolio_id: Optional[str] = None
    ) -> DpmSupportabilitySummaryData:
        with self._lock:
            return _supportability_summary_data(
                runs=list(self._runs.values()),
                operations=list(self._operations.values()),
                workflow_decisions=self._workflow_decisions,
                lineage_edges_by_entity=self._lineage_edges_by_entity,
                portfolio_id=portfolio_id,
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
