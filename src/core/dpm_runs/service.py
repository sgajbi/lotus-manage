import uuid
from datetime import datetime, timezone
from typing import Any, Optional, cast

from src.core.dpm_runs.artifact import build_dpm_run_artifact
from src.core.dpm_runs.models import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationListItemResponse,
    DpmAsyncOperationListResponse,
    DpmAsyncOperationRecord,
    DpmAsyncOperationStatusResponse,
    DpmLineageEdgeRecord,
    DpmLineageEdgeResponse,
    DpmLineageResponse,
    DpmRunArtifactResponse,
    DpmRunIdempotencyHistoryItem,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyHistoryResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunIdempotencyRecord,
    DpmRunListItemResponse,
    DpmRunListResponse,
    DpmRunLookupResponse,
    DpmRunRecord,
    DpmRunSupportBundleResponse,
    DpmRunWorkflowDecisionRecord,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmSupportabilitySummaryData,
    DpmSupportabilitySummaryResponse,
    DpmWorkflowActionType,
    DpmWorkflowDecisionListResponse,
    DpmWorkflowStatus,
)
from src.core.dpm_runs.repository import DpmRunRepository
from src.core.dpm_runs.serializers import (
    to_async_accepted,
    to_async_status,
    to_lookup_response,
    to_workflow_decision_response,
)
from src.core.dpm_runs.workflow import (
    resolve_workflow_status,
    resolve_workflow_transition,
    workflow_required_for_run_status,
)
from src.core.models import RebalanceResult


class DpmRunNotFoundError(Exception):
    pass


class DpmWorkflowDisabledError(Exception):
    pass


class DpmWorkflowTransitionError(Exception):
    pass


class DpmRunSupportService:
    def __init__(
        self,
        *,
        repository: DpmRunRepository,
        async_operation_ttl_seconds: int = 86400,
        supportability_retention_days: int = 0,
        workflow_enabled: bool = False,
        workflow_requires_review_for_statuses: Optional[set[str]] = None,
        artifact_store_mode: str = "DERIVED",
    ) -> None:
        self._repository = repository
        self._async_operation_ttl_seconds = max(1, async_operation_ttl_seconds)
        self._supportability_retention_days = max(0, supportability_retention_days)
        self._workflow_enabled = workflow_enabled
        self._workflow_requires_review_for_statuses = {
            value.strip()
            for value in (workflow_requires_review_for_statuses or {"PENDING_REVIEW"})
            if value.strip()
        }
        self._artifact_store_mode = (
            "PERSISTED" if artifact_store_mode.strip().upper() == "PERSISTED" else "DERIVED"
        )

    def record_run(
        self,
        *,
        result: RebalanceResult,
        request_hash: str,
        portfolio_id: str,
        idempotency_key: Optional[str],
        created_at: Optional[datetime] = None,
    ) -> None:
        self._cleanup_expired_supportability()
        now = created_at or datetime.now(timezone.utc)
        run = DpmRunRecord(
            rebalance_run_id=result.rebalance_run_id,
            correlation_id=result.correlation_id,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            portfolio_id=portfolio_id,
            created_at=now,
            result_json=result.model_dump(mode="json"),
        )
        self._repository.save_run(run)
        self._persist_run_artifact_if_needed(run=run)
        self._record_lineage_edge(
            source_entity_id=run.correlation_id,
            edge_type="CORRELATION_TO_RUN",
            target_entity_id=run.rebalance_run_id,
            metadata={"request_hash": run.request_hash},
            created_at=now,
        )
        if idempotency_key is not None:
            self._repository.save_idempotency_mapping(
                DpmRunIdempotencyRecord(
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    rebalance_run_id=result.rebalance_run_id,
                    created_at=now,
                )
            )
            self._repository.append_idempotency_history(
                DpmRunIdempotencyHistoryRecord(
                    idempotency_key=idempotency_key,
                    rebalance_run_id=run.rebalance_run_id,
                    correlation_id=run.correlation_id,
                    request_hash=run.request_hash,
                    created_at=now,
                )
            )
            self._record_lineage_edge(
                source_entity_id=idempotency_key,
                edge_type="IDEMPOTENCY_TO_RUN",
                target_entity_id=run.rebalance_run_id,
                metadata={"request_hash": run.request_hash},
                created_at=now,
            )

    def get_run(self, *, rebalance_run_id: str) -> DpmRunLookupResponse:
        self._cleanup_expired_supportability()
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return to_lookup_response(run)

    def get_run_by_correlation(self, *, correlation_id: str) -> DpmRunLookupResponse:
        self._cleanup_expired_supportability()
        run = self._repository.get_run_by_correlation(correlation_id=correlation_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return to_lookup_response(run)

    def get_run_by_request_hash(self, *, request_hash: str) -> DpmRunLookupResponse:
        self._cleanup_expired_supportability()
        run = self._repository.get_run_by_request_hash(request_hash=request_hash)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return to_lookup_response(run)

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
    ) -> DpmRunListResponse:
        self._cleanup_expired_supportability()
        rows, next_cursor = self._repository.list_runs(
            created_from=created_from,
            created_to=created_to,
            status=status,
            request_hash=request_hash,
            portfolio_id=portfolio_id,
            limit=limit,
            cursor=cursor,
        )
        return DpmRunListResponse(
            items=[
                DpmRunListItemResponse(
                    rebalance_run_id=row.rebalance_run_id,
                    correlation_id=row.correlation_id,
                    request_hash=row.request_hash,
                    idempotency_key=row.idempotency_key,
                    portfolio_id=row.portfolio_id,
                    status=str(row.result_json.get("status", "")),
                    created_at=row.created_at.isoformat(),
                )
                for row in rows
            ],
            next_cursor=next_cursor,
        )

    def get_idempotency_lookup(self, *, idempotency_key: str) -> DpmRunIdempotencyLookupResponse:
        self._cleanup_expired_supportability()
        record = self._repository.get_idempotency_mapping(idempotency_key=idempotency_key)
        if record is None:
            raise DpmRunNotFoundError("DPM_IDEMPOTENCY_KEY_NOT_FOUND")
        return DpmRunIdempotencyLookupResponse(
            idempotency_key=record.idempotency_key,
            request_hash=record.request_hash,
            rebalance_run_id=record.rebalance_run_id,
            created_at=record.created_at.isoformat(),
        )

    def get_idempotency_history(self, *, idempotency_key: str) -> DpmRunIdempotencyHistoryResponse:
        self._cleanup_expired_supportability()
        history = self._repository.list_idempotency_history(idempotency_key=idempotency_key)
        if not history:
            raise DpmRunNotFoundError("DPM_IDEMPOTENCY_KEY_NOT_FOUND")
        ordered_history = sorted(
            history,
            key=lambda item: (
                item.created_at,
                item.rebalance_run_id,
                item.correlation_id,
                item.request_hash,
            ),
        )
        return DpmRunIdempotencyHistoryResponse(
            idempotency_key=idempotency_key,
            history=[
                DpmRunIdempotencyHistoryItem(
                    rebalance_run_id=item.rebalance_run_id,
                    correlation_id=item.correlation_id,
                    request_hash=item.request_hash,
                    created_at=item.created_at.isoformat(),
                )
                for item in ordered_history
            ],
        )

    def get_run_artifact(self, *, rebalance_run_id: str) -> DpmRunArtifactResponse:
        self._cleanup_expired_supportability()
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self._resolve_run_artifact(run=run)

    def submit_analyze_async(
        self,
        *,
        correlation_id: Optional[str],
        request_json: dict[str, Any],
        created_at: Optional[datetime] = None,
    ) -> DpmAsyncAcceptedResponse:
        self._cleanup_expired_operations()
        now = created_at or _utc_now()
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = DpmAsyncOperationRecord(
            operation_id=f"dop_{uuid.uuid4().hex[:12]}",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json=request_json,
        )
        self._repository.create_operation(operation)
        self._record_lineage_edge(
            source_entity_id=operation.operation_id,
            edge_type="OPERATION_TO_CORRELATION",
            target_entity_id=operation.correlation_id,
            metadata={"operation_type": operation.operation_type},
            created_at=operation.created_at,
        )
        return to_async_accepted(operation)

    def list_async_operations(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        operation_type: Optional[str],
        status: Optional[str],
        correlation_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> DpmAsyncOperationListResponse:
        self._cleanup_expired_operations()
        operations, next_cursor = self._repository.list_operations(
            created_from=created_from,
            created_to=created_to,
            operation_type=operation_type,
            status=status,
            correlation_id=correlation_id,
            limit=limit,
            cursor=cursor,
        )
        return DpmAsyncOperationListResponse(
            items=[
                DpmAsyncOperationListItemResponse(
                    operation_id=operation.operation_id,
                    operation_type=operation.operation_type,
                    status=operation.status,
                    correlation_id=operation.correlation_id,
                    is_executable=(
                        operation.status == "PENDING" and operation.request_json is not None
                    ),
                    created_at=operation.created_at.isoformat(),
                    started_at=(
                        operation.started_at.isoformat()
                        if operation.started_at is not None
                        else None
                    ),
                    finished_at=(
                        operation.finished_at.isoformat()
                        if operation.finished_at is not None
                        else None
                    ),
                )
                for operation in operations
            ],
            next_cursor=next_cursor,
        )

    def get_lineage(self, *, entity_id: str) -> DpmLineageResponse:
        self._cleanup_expired_supportability()
        edges = self._repository.list_lineage_edges(entity_id=entity_id)
        edges = sorted(
            edges,
            key=lambda edge: (
                edge.created_at,
                edge.source_entity_id,
                edge.edge_type,
                edge.target_entity_id,
            ),
        )
        return DpmLineageResponse(
            entity_id=entity_id,
            edges=[
                DpmLineageEdgeResponse(
                    source_entity_id=edge.source_entity_id,
                    edge_type=edge.edge_type,
                    target_entity_id=edge.target_entity_id,
                    created_at=edge.created_at.isoformat(),
                    metadata=edge.metadata_json,
                )
                for edge in edges
            ],
            next_cursor=None,
        )

    def get_lineage_filtered(
        self,
        *,
        entity_id: str,
        edge_type: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> DpmLineageResponse:
        self._cleanup_expired_supportability()
        edges = self._repository.list_lineage_edges(entity_id=entity_id)
        edges = sorted(
            edges,
            key=lambda edge: (
                edge.created_at,
                edge.source_entity_id,
                edge.edge_type,
                edge.target_entity_id,
            ),
        )
        if edge_type is not None:
            edges = [edge for edge in edges if edge.edge_type == edge_type]
        if created_from is not None:
            edges = [edge for edge in edges if edge.created_at >= created_from]
        if created_to is not None:
            edges = [edge for edge in edges if edge.created_at <= created_to]

        if cursor is not None:
            cursor_index = next(
                (index for index, row in enumerate(edges) if _lineage_cursor(row) == cursor),
                None,
            )
            if cursor_index is None:
                edges = []
            else:
                edges = edges[cursor_index + 1 :]

        page = edges[:limit]
        next_cursor = _lineage_cursor(page[-1]) if len(edges) > limit else None
        return DpmLineageResponse(
            entity_id=entity_id,
            edges=[
                DpmLineageEdgeResponse(
                    source_entity_id=edge.source_entity_id,
                    edge_type=edge.edge_type,
                    target_entity_id=edge.target_entity_id,
                    created_at=edge.created_at.isoformat(),
                    metadata=edge.metadata_json,
                )
                for edge in page
            ],
            next_cursor=next_cursor,
        )

    def get_supportability_summary(
        self, *, store_backend: str, retention_days: int
    ) -> DpmSupportabilitySummaryResponse:
        self._cleanup_expired_operations()
        self._cleanup_expired_supportability()
        summary: DpmSupportabilitySummaryData = self._repository.get_supportability_summary()
        return DpmSupportabilitySummaryResponse(
            store_backend=store_backend,
            retention_days=retention_days,
            run_count=summary.run_count,
            operation_count=summary.operation_count,
            operation_status_counts=summary.operation_status_counts,
            run_status_counts=summary.run_status_counts,
            workflow_decision_count=summary.workflow_decision_count,
            workflow_action_counts=summary.workflow_action_counts,
            workflow_reason_code_counts=summary.workflow_reason_code_counts,
            lineage_edge_count=summary.lineage_edge_count,
            oldest_run_created_at=(
                summary.oldest_run_created_at.isoformat()
                if summary.oldest_run_created_at is not None
                else None
            ),
            newest_run_created_at=(
                summary.newest_run_created_at.isoformat()
                if summary.newest_run_created_at is not None
                else None
            ),
            oldest_operation_created_at=(
                summary.oldest_operation_created_at.isoformat()
                if summary.oldest_operation_created_at is not None
                else None
            ),
            newest_operation_created_at=(
                summary.newest_operation_created_at.isoformat()
                if summary.newest_operation_created_at is not None
                else None
            ),
        )

    def get_run_support_bundle(
        self,
        *,
        rebalance_run_id: str,
        include_artifact: bool,
        include_async_operation: bool,
        include_idempotency_history: bool,
    ) -> DpmRunSupportBundleResponse:
        self._cleanup_expired_operations()
        self._cleanup_expired_supportability()
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")

        artifact = self._resolve_run_artifact(run=run) if include_artifact else None
        async_operation = None
        if include_async_operation:
            operation = self._repository.get_operation_by_correlation(
                correlation_id=run.correlation_id
            )
            if operation is not None:
                async_operation = to_async_status(operation)

        idempotency_history = None
        if include_idempotency_history and run.idempotency_key is not None:
            history = self._repository.list_idempotency_history(idempotency_key=run.idempotency_key)
            ordered_history = sorted(
                history,
                key=lambda item: (
                    item.created_at,
                    item.rebalance_run_id,
                    item.correlation_id,
                    item.request_hash,
                ),
            )
            idempotency_history = DpmRunIdempotencyHistoryResponse(
                idempotency_key=run.idempotency_key,
                history=[
                    DpmRunIdempotencyHistoryItem(
                        rebalance_run_id=item.rebalance_run_id,
                        correlation_id=item.correlation_id,
                        request_hash=item.request_hash,
                        created_at=item.created_at.isoformat(),
                    )
                    for item in ordered_history
                ],
            )

        decisions = self._repository.list_workflow_decisions(rebalance_run_id=rebalance_run_id)
        decisions = sorted(decisions, key=lambda item: item.decided_at)
        workflow_history = DpmRunWorkflowHistoryResponse(
            run_id=rebalance_run_id,
            decisions=[to_workflow_decision_response(decision) for decision in decisions],
        )

        edges = self._repository.list_lineage_edges(entity_id=rebalance_run_id)
        edges = sorted(
            edges,
            key=lambda edge: (
                edge.created_at,
                edge.source_entity_id,
                edge.edge_type,
                edge.target_entity_id,
            ),
        )
        lineage = DpmLineageResponse(
            entity_id=rebalance_run_id,
            edges=[
                DpmLineageEdgeResponse(
                    source_entity_id=edge.source_entity_id,
                    edge_type=edge.edge_type,
                    target_entity_id=edge.target_entity_id,
                    created_at=edge.created_at.isoformat(),
                    metadata=edge.metadata_json,
                )
                for edge in edges
            ],
        )

        return DpmRunSupportBundleResponse(
            run=to_lookup_response(run),
            artifact=artifact,
            async_operation=async_operation,
            workflow_history=workflow_history,
            lineage=lineage,
            idempotency_history=idempotency_history,
        )

    def get_run_support_bundle_by_correlation(
        self,
        *,
        correlation_id: str,
        include_artifact: bool,
        include_async_operation: bool,
        include_idempotency_history: bool,
    ) -> DpmRunSupportBundleResponse:
        run = self._get_required_run_by_correlation(correlation_id=correlation_id)
        return self.get_run_support_bundle(
            rebalance_run_id=run.rebalance_run_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )

    def get_run_support_bundle_by_idempotency(
        self,
        *,
        idempotency_key: str,
        include_artifact: bool,
        include_async_operation: bool,
        include_idempotency_history: bool,
    ) -> DpmRunSupportBundleResponse:
        mapping = self._get_required_idempotency_mapping(idempotency_key=idempotency_key)
        return self.get_run_support_bundle(
            rebalance_run_id=mapping.rebalance_run_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )

    def get_run_support_bundle_by_operation(
        self,
        *,
        operation_id: str,
        include_artifact: bool,
        include_async_operation: bool,
        include_idempotency_history: bool,
    ) -> DpmRunSupportBundleResponse:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        return self.get_run_support_bundle(
            rebalance_run_id=self._get_required_run_by_correlation(
                correlation_id=operation.correlation_id
            ).rebalance_run_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )

    def mark_operation_running(self, *, operation_id: str) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)

    def complete_operation_success(self, *, operation_id: str, result_json: dict[str, Any]) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "SUCCEEDED"
        operation.result_json = result_json
        operation.error_json = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def complete_operation_failure(self, *, operation_id: str, code: str, message: str) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "FAILED"
        operation.result_json = None
        operation.error_json = {"code": code, "message": message}
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def get_async_operation(self, *, operation_id: str) -> DpmAsyncOperationStatusResponse:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status(operation)

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> DpmAsyncOperationStatusResponse:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation_by_correlation(correlation_id=correlation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status(operation)

    def prepare_analyze_operation_execution(
        self, *, operation_id: str
    ) -> tuple[dict[str, Any], str]:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        if operation.status != "PENDING" or operation.request_json is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_EXECUTABLE")
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)
        return cast(dict[str, Any], operation.request_json), operation.correlation_id

    def get_workflow(self, *, rebalance_run_id: str) -> DpmRunWorkflowResponse:
        self._cleanup_expired_supportability()
        run = self._get_required_run(rebalance_run_id=rebalance_run_id)
        return self._to_workflow_response(run=run)

    def get_workflow_by_correlation(self, *, correlation_id: str) -> DpmRunWorkflowResponse:
        self._cleanup_expired_supportability()
        run = self._get_required_run_by_correlation(correlation_id=correlation_id)
        return self._to_workflow_response(run=run)

    def get_workflow_history(self, *, rebalance_run_id: str) -> DpmRunWorkflowHistoryResponse:
        self._cleanup_expired_supportability()
        self._get_required_run(rebalance_run_id=rebalance_run_id)
        decisions = self._repository.list_workflow_decisions(rebalance_run_id=rebalance_run_id)
        decisions = sorted(decisions, key=lambda item: item.decided_at)
        return DpmRunWorkflowHistoryResponse(
            run_id=rebalance_run_id,
            decisions=[to_workflow_decision_response(decision) for decision in decisions],
        )

    def get_workflow_history_by_correlation(
        self, *, correlation_id: str
    ) -> DpmRunWorkflowHistoryResponse:
        self._cleanup_expired_supportability()
        run = self._get_required_run_by_correlation(correlation_id=correlation_id)
        return self.get_workflow_history(rebalance_run_id=run.rebalance_run_id)

    def get_workflow_by_idempotency(self, *, idempotency_key: str) -> DpmRunWorkflowResponse:
        self._cleanup_expired_supportability()
        mapping = self._get_required_idempotency_mapping(idempotency_key=idempotency_key)
        run = self._get_required_run(rebalance_run_id=mapping.rebalance_run_id)
        return self._to_workflow_response(run=run)

    def get_workflow_history_by_idempotency(
        self, *, idempotency_key: str
    ) -> DpmRunWorkflowHistoryResponse:
        self._cleanup_expired_supportability()
        mapping = self._get_required_idempotency_mapping(idempotency_key=idempotency_key)
        return self.get_workflow_history(rebalance_run_id=mapping.rebalance_run_id)

    def list_workflow_decisions(
        self,
        *,
        rebalance_run_id: Optional[str],
        action: Optional[DpmWorkflowActionType],
        actor_id: Optional[str],
        reason_code: Optional[str],
        decided_from: Optional[datetime],
        decided_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> DpmWorkflowDecisionListResponse:
        self._cleanup_expired_supportability()
        decisions, next_cursor = self._repository.list_workflow_decisions_filtered(
            rebalance_run_id=rebalance_run_id,
            action=action,
            actor_id=actor_id,
            reason_code=reason_code,
            decided_from=decided_from,
            decided_to=decided_to,
            limit=limit,
            cursor=cursor,
        )
        return DpmWorkflowDecisionListResponse(
            items=[to_workflow_decision_response(decision) for decision in decisions],
            next_cursor=next_cursor,
        )

    def apply_workflow_action(
        self,
        *,
        rebalance_run_id: str,
        action: DpmWorkflowActionType,
        reason_code: str,
        comment: Optional[str],
        actor_id: str,
        correlation_id: str,
    ) -> DpmRunWorkflowResponse:
        self._cleanup_expired_supportability()
        if not self._workflow_enabled:
            raise DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED")
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        run_status = str(run.result_json.get("status", ""))
        if not self._workflow_required_for_run_status(run_status=run_status):
            raise DpmWorkflowTransitionError("DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS")

        latest_decision = self._latest_workflow_decision(rebalance_run_id=rebalance_run_id)
        current_status = self._resolve_workflow_status(
            run_status=run_status,
            latest_decision=latest_decision,
        )
        next_status = resolve_workflow_transition(current_status=current_status, action=action)
        if next_status is None:
            raise DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION")

        decision = DpmRunWorkflowDecisionRecord(
            decision_id=f"dwd_{uuid.uuid4().hex[:12]}",
            run_id=rebalance_run_id,
            action=action,
            reason_code=reason_code,
            comment=comment,
            actor_id=actor_id,
            decided_at=_utc_now(),
            correlation_id=correlation_id,
        )
        self._repository.append_workflow_decision(decision)
        return DpmRunWorkflowResponse(
            run_id=rebalance_run_id,
            run_status=run_status,
            workflow_status=next_status,
            requires_review=True,
            latest_decision=to_workflow_decision_response(decision),
        )

    def apply_workflow_action_by_correlation(
        self,
        *,
        correlation_id: str,
        action: DpmWorkflowActionType,
        reason_code: str,
        comment: Optional[str],
        actor_id: str,
        action_correlation_id: str,
    ) -> DpmRunWorkflowResponse:
        run = self._get_required_run_by_correlation(correlation_id=correlation_id)
        return self.apply_workflow_action(
            rebalance_run_id=run.rebalance_run_id,
            action=action,
            reason_code=reason_code,
            comment=comment,
            actor_id=actor_id,
            correlation_id=action_correlation_id,
        )

    def apply_workflow_action_by_idempotency(
        self,
        *,
        idempotency_key: str,
        action: DpmWorkflowActionType,
        reason_code: str,
        comment: Optional[str],
        actor_id: str,
        action_correlation_id: str,
    ) -> DpmRunWorkflowResponse:
        mapping = self._get_required_idempotency_mapping(idempotency_key=idempotency_key)
        return self.apply_workflow_action(
            rebalance_run_id=mapping.rebalance_run_id,
            action=action,
            reason_code=reason_code,
            comment=comment,
            actor_id=actor_id,
            correlation_id=action_correlation_id,
        )

    def _cleanup_expired_operations(self) -> None:
        self._repository.purge_expired_operations(
            ttl_seconds=self._async_operation_ttl_seconds,
            now=_utc_now(),
        )

    def _cleanup_expired_supportability(self) -> None:
        if self._supportability_retention_days < 1:
            return
        self._repository.purge_expired_runs(
            retention_days=self._supportability_retention_days,
            now=_utc_now(),
        )

    def _record_lineage_edge(
        self,
        *,
        source_entity_id: str,
        edge_type: str,
        target_entity_id: str,
        metadata: dict[str, Any],
        created_at: datetime,
    ) -> None:
        self._repository.append_lineage_edge(
            DpmLineageEdgeRecord(
                source_entity_id=source_entity_id,
                edge_type=edge_type,
                target_entity_id=target_entity_id,
                created_at=created_at,
                metadata_json=metadata,
            )
        )

    def _get_required_run(self, *, rebalance_run_id: str) -> DpmRunRecord:
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return run

    def _get_required_run_by_correlation(self, *, correlation_id: str) -> DpmRunRecord:
        run = self._repository.get_run_by_correlation(correlation_id=correlation_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return run

    def _get_required_idempotency_mapping(self, *, idempotency_key: str) -> DpmRunIdempotencyRecord:
        mapping = self._repository.get_idempotency_mapping(idempotency_key=idempotency_key)
        if mapping is None:
            raise DpmRunNotFoundError("DPM_IDEMPOTENCY_KEY_NOT_FOUND")
        return mapping

    def _to_workflow_response(self, *, run: DpmRunRecord) -> DpmRunWorkflowResponse:
        run_status = str(run.result_json.get("status", ""))
        latest_decision = self._latest_workflow_decision(rebalance_run_id=run.rebalance_run_id)
        workflow_status = self._resolve_workflow_status(
            run_status=run_status,
            latest_decision=latest_decision,
        )
        return DpmRunWorkflowResponse(
            run_id=run.rebalance_run_id,
            run_status=run_status,
            workflow_status=workflow_status,
            requires_review=self._workflow_required_for_run_status(run_status=run_status),
            latest_decision=(
                to_workflow_decision_response(latest_decision)
                if latest_decision is not None
                else None
            ),
        )

    def _latest_workflow_decision(
        self, *, rebalance_run_id: str
    ) -> Optional[DpmRunWorkflowDecisionRecord]:
        decisions = self._repository.list_workflow_decisions(rebalance_run_id=rebalance_run_id)
        if not decisions:
            return None
        return max(decisions, key=lambda item: item.decided_at)

    def _workflow_required_for_run_status(self, *, run_status: str) -> bool:
        return workflow_required_for_run_status(
            workflow_enabled=self._workflow_enabled,
            run_status=run_status,
            requires_review_for_statuses=self._workflow_requires_review_for_statuses,
        )

    def _resolve_workflow_status(
        self,
        *,
        run_status: str,
        latest_decision: Optional[DpmRunWorkflowDecisionRecord],
    ) -> DpmWorkflowStatus:
        return resolve_workflow_status(
            workflow_enabled=self._workflow_enabled,
            run_status=run_status,
            latest_decision=latest_decision,
            requires_review_for_statuses=self._workflow_requires_review_for_statuses,
        )

    def _persist_run_artifact_if_needed(self, *, run: DpmRunRecord) -> None:
        if self._artifact_store_mode != "PERSISTED":
            return
        artifact = build_dpm_run_artifact(run=run)
        self._repository.save_run_artifact(
            rebalance_run_id=run.rebalance_run_id,
            artifact_json=artifact.model_dump(mode="json"),
        )

    def _resolve_run_artifact(self, *, run: DpmRunRecord) -> DpmRunArtifactResponse:
        if self._artifact_store_mode != "PERSISTED":
            return build_dpm_run_artifact(run=run)
        persisted = self._repository.get_run_artifact(rebalance_run_id=run.rebalance_run_id)
        if persisted is not None:
            return cast(DpmRunArtifactResponse, DpmRunArtifactResponse.model_validate(persisted))
        artifact = build_dpm_run_artifact(run=run)
        self._repository.save_run_artifact(
            rebalance_run_id=run.rebalance_run_id,
            artifact_json=artifact.model_dump(mode="json"),
        )
        return artifact


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _lineage_cursor(edge: DpmLineageEdgeRecord) -> str:
    return (
        f"{edge.created_at.isoformat()}|{edge.source_entity_id}|"
        f"{edge.edge_type}|{edge.target_entity_id}"
    )
