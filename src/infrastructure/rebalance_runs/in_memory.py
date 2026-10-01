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
    DpmSimulationSubmissionClaimRecord,
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
        self._idempotency: dict[tuple[Optional[str], str], DpmRunIdempotencyRecord] = {}
        self._idempotency_history: dict[
            tuple[Optional[str], str], list[DpmRunIdempotencyHistoryRecord]
        ] = {}
        self._submission_claims: dict[tuple[str, str], DpmSimulationSubmissionClaimRecord] = {}
        self._run_artifacts: dict[str, dict[str, Any]] = {}
        self._operations: dict[str, DpmAsyncOperationRecord] = {}
        self._operation_by_correlation: dict[tuple[Optional[str], str], str] = {}
        self._workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]] = {}
        self._lineage_edges_by_entity: dict[str, list[DpmLineageEdgeRecord]] = {}

    def claim_simulation_submission(
        self,
        *,
        tenant_id: str,
        idempotency_key: str,
        request_hash: str,
        claim_token: str,
        claimed_at: datetime,
        claim_expires_at: datetime,
    ) -> DpmSimulationSubmissionClaimRecord:
        key = (tenant_id, idempotency_key)
        with self._lock:
            existing = self._submission_claims.get(key)
            if existing is None or (
                existing.status == "IN_PROGRESS"
                and existing.request_hash == request_hash
                and existing.claim_expires_at <= claimed_at
            ):
                existing = DpmSimulationSubmissionClaimRecord(
                    tenant_id=tenant_id,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    status="IN_PROGRESS",
                    claim_token=claim_token,
                    claimed_at=claimed_at,
                    claim_expires_at=claim_expires_at,
                )
                self._submission_claims[key] = existing
            return deepcopy(existing)

    def get_simulation_submission_claim(
        self, *, tenant_id: str, idempotency_key: str
    ) -> Optional[DpmSimulationSubmissionClaimRecord]:
        with self._lock:
            claim = self._submission_claims.get((tenant_id, idempotency_key))
            return deepcopy(claim) if claim is not None else None

    def abandon_simulation_submission_claim(
        self, *, tenant_id: str, idempotency_key: str, claim_token: str, abandoned_at: datetime
    ) -> None:
        with self._lock:
            claim = self._submission_claims.get((tenant_id, idempotency_key))
            if (
                claim is not None
                and claim.status == "IN_PROGRESS"
                and claim.claim_token == claim_token
            ):
                claim.claim_expires_at = abandoned_at

    def complete_simulation_submission(
        self,
        *,
        tenant_id: str,
        idempotency_key: str,
        request_hash: str,
        claim_token: str,
        run: DpmRunRecord,
        artifact_json: Optional[dict[str, Any]],
        idempotency_history: DpmRunIdempotencyHistoryRecord,
        lineage_edges: list[DpmLineageEdgeRecord],
        completed_at: datetime,
    ) -> None:
        key = (tenant_id, idempotency_key)
        with self._lock:
            claim = self._submission_claims.get(key)
            if (
                claim is None
                or claim.status != "IN_PROGRESS"
                or claim.claim_token != claim_token
                or claim.request_hash != request_hash
            ):
                raise DpmRunRepositoryConflictError("DPM_SIMULATION_SUBMISSION_CLAIM_LOST")
            self._runs[run.rebalance_run_id] = deepcopy(run)
            self._run_id_by_correlation[run.correlation_id] = run.rebalance_run_id
            if artifact_json is not None:
                self._run_artifacts[run.rebalance_run_id] = deepcopy(artifact_json)
            self._idempotency[key] = DpmRunIdempotencyRecord(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                rebalance_run_id=run.rebalance_run_id,
                created_at=completed_at,
            )
            self._idempotency_history.setdefault(key, []).append(deepcopy(idempotency_history))
            for edge in lineage_edges:
                self._lineage_edges_by_entity.setdefault(edge.source_entity_id, []).append(
                    deepcopy(edge)
                )
                if edge.target_entity_id != edge.source_entity_id:
                    self._lineage_edges_by_entity.setdefault(edge.target_entity_id, []).append(
                        deepcopy(edge)
                    )
            claim.status = "COMPLETED"
            claim.rebalance_run_id = run.rebalance_run_id
            claim.completed_at = completed_at
            claim.claim_expires_at = completed_at

    def save_run(self, run: DpmRunRecord) -> None:
        with self._lock:
            self._runs[run.rebalance_run_id] = deepcopy(run)
            self._run_id_by_correlation[run.correlation_id] = run.rebalance_run_id

    def save_run_with_lineage(
        self, *, run: DpmRunRecord, lineage_edges: list[DpmLineageEdgeRecord]
    ) -> None:
        if any(
            edge.tenant_id != run.tenant_id or edge.target_entity_id != run.rebalance_run_id
            for edge in lineage_edges
        ):
            raise ValueError("DPM_RUN_LINEAGE_SCOPE_MISMATCH")
        with self._lock:
            if (
                run.rebalance_run_id in self._runs
                or run.correlation_id in self._run_id_by_correlation
            ):
                raise DpmRunRepositoryConflictError("DPM_RUN_ALREADY_EXISTS")
            self._runs[run.rebalance_run_id] = deepcopy(run)
            self._run_id_by_correlation[run.correlation_id] = run.rebalance_run_id
            for edge in lineage_edges:
                self._lineage_edges_by_entity.setdefault(edge.source_entity_id, []).append(
                    deepcopy(edge)
                )
                if edge.target_entity_id != edge.source_entity_id:
                    self._lineage_edges_by_entity.setdefault(edge.target_entity_id, []).append(
                        deepcopy(edge)
                    )

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run = self._runs.get(rebalance_run_id)
            return deepcopy(run) if run is not None else None

    def get_run_for_tenant(
        self, *, tenant_id: str, rebalance_run_id: str
    ) -> Optional[DpmRunRecord]:
        run = self.get_run(rebalance_run_id=rebalance_run_id)
        return run if run is not None and run.tenant_id == tenant_id else None

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run_id = self._run_id_by_correlation.get(correlation_id)
            if run_id is None:
                return None
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    def get_run_by_correlation_for_tenant(
        self, *, tenant_id: str, correlation_id: str
    ) -> Optional[DpmRunRecord]:
        with self._lock:
            matching = [
                run
                for run in self._runs.values()
                if run.tenant_id == tenant_id and run.correlation_id == correlation_id
            ]
            if not matching:
                return None
            return deepcopy(
                max(matching, key=lambda item: (item.created_at, item.rebalance_run_id))
            )

    def get_run_by_request_hash(self, *, request_hash: str) -> Optional[DpmRunRecord]:
        with self._lock:
            matching = [run for run in self._runs.values() if run.request_hash == request_hash]
            if not matching:
                return None
            latest = max(matching, key=lambda item: (item.created_at, item.rebalance_run_id))
            return deepcopy(latest)

    def get_run_by_request_hash_for_tenant(
        self, *, tenant_id: str, request_hash: str
    ) -> Optional[DpmRunRecord]:
        with self._lock:
            matching = [
                run
                for run in self._runs.values()
                if run.tenant_id == tenant_id and run.request_hash == request_hash
            ]
            if not matching:
                return None
            return deepcopy(
                max(matching, key=lambda item: (item.created_at, item.rebalance_run_id))
            )

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

    def list_runs_for_tenant(
        self,
        *,
        tenant_id: str,
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
                runs=[run for run in self._runs.values() if run.tenant_id == tenant_id],
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
            self._idempotency[(record.tenant_id, record.idempotency_key)] = deepcopy(record)

    def get_idempotency_mapping(self, *, idempotency_key: str) -> Optional[DpmRunIdempotencyRecord]:
        with self._lock:
            record = next(
                (value for (_, key), value in self._idempotency.items() if key == idempotency_key),
                None,
            )
            return deepcopy(record) if record is not None else None

    def get_idempotency_mapping_for_tenant(
        self, *, tenant_id: str, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get((tenant_id, idempotency_key))
            return deepcopy(record) if record is not None else None

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None:
        with self._lock:
            history = self._idempotency_history.setdefault(
                (record.tenant_id, record.idempotency_key), []
            )
            history.append(deepcopy(record))

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]:
        with self._lock:
            history = next(
                (
                    value
                    for (_, key), value in self._idempotency_history.items()
                    if key == idempotency_key
                ),
                [],
            )
            return [deepcopy(item) for item in history]

    def list_idempotency_history_for_tenant(
        self, *, tenant_id: str, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]:
        with self._lock:
            history = self._idempotency_history.get((tenant_id, idempotency_key), [])
            return [deepcopy(item) for item in history]

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._save_operation(operation)

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._save_operation(operation)

    def claim_operation_execution(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return None
            lease_expired = (
                operation.status == "RUNNING"
                and operation.execution_lease_expires_at is not None
                and operation.execution_lease_expires_at <= claimed_at
            )
            if operation.request_json is None or not (
                operation.status == "PENDING" or lease_expired
            ):
                return None
            operation.status = "RUNNING"
            operation.started_at = claimed_at
            operation.finished_at = None
            operation.result_json = None
            operation.error_json = None
            operation.execution_token = execution_token
            operation.execution_attempt += 1
            operation.execution_claimed_at = claimed_at
            operation.execution_lease_expires_at = lease_expires_at
            return operation.model_copy(deep=True)

    def publish_operation_success(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        result_json: dict[str, Any],
        finished_at: datetime,
    ) -> bool:
        with self._lock:
            operation = self._operations.get(operation_id)
            if (
                operation is None
                or operation.tenant_id != tenant_id
                or operation.status != "RUNNING"
                or operation.execution_token != execution_token
            ):
                return False
            operation.status = "SUCCEEDED"
            operation.result_json = deepcopy(result_json)
            operation.error_json = None
            operation.finished_at = finished_at
            operation.execution_lease_expires_at = None
            return True

    def publish_operation_failure(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        error_json: dict[str, str],
        finished_at: datetime,
    ) -> bool:
        with self._lock:
            operation = self._operations.get(operation_id)
            if (
                operation is None
                or operation.tenant_id != tenant_id
                or operation.status != "RUNNING"
                or operation.execution_token != execution_token
            ):
                return False
            operation.status = "FAILED"
            operation.result_json = None
            operation.error_json = deepcopy(error_json)
            operation.finished_at = finished_at
            operation.execution_lease_expires_at = None
            return True

    def _save_operation(self, operation: DpmAsyncOperationRecord) -> None:
        correlation_key = (operation.tenant_id, operation.correlation_id)
        existing_operation_id = self._operation_by_correlation.get(correlation_key)
        if existing_operation_id is not None and existing_operation_id != operation.operation_id:
            raise DpmRunRepositoryConflictError("DPM_ASYNC_OPERATION_CORRELATION_CONFLICT")
        self._operations[operation.operation_id] = deepcopy(operation)
        self._operation_by_correlation[correlation_key] = operation.operation_id

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_for_tenant(
        self, *, tenant_id: str, operation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        operation = self.get_operation(operation_id=operation_id)
        return operation if operation is not None and operation.tenant_id == tenant_id else None

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation_id = next(
                (
                    stored_operation_id
                    for (
                        _,
                        stored_correlation_id,
                    ), stored_operation_id in self._operation_by_correlation.items()
                    if stored_correlation_id == correlation_id
                ),
                None,
            )
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_correlation_for_tenant(
        self, *, tenant_id: str, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_correlation.get((tenant_id, correlation_id))
            operation = self._operations.get(operation_id) if operation_id is not None else None
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

    def list_operations_for_tenant(
        self,
        *,
        tenant_id: str,
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
                operations=[
                    operation
                    for operation in self._operations.values()
                    if operation.tenant_id == tenant_id
                ],
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
                if operation.status == "RUNNING":
                    # A RUNNING row is recovery state.  Its lease, rather than the
                    # general retention TTL, decides when another worker may claim it.
                    continue
                anchor = operation.finished_at or operation.created_at
                if anchor < cutoff:
                    self._operations.pop(operation_id, None)
                    correlation_key = (operation.tenant_id, operation.correlation_id)
                    if self._operation_by_correlation.get(correlation_key) == operation_id:
                        self._operation_by_correlation.pop(correlation_key, None)
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
