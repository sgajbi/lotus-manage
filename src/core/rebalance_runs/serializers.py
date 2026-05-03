from src.core.rebalance_runs.models import (
    DpmAsyncAcceptedResponse,
    DpmAsyncError,
    DpmAsyncOperationRecord,
    DpmAsyncOperationStatusResponse,
    DpmLineageEdgeRecord,
    DpmLineageEdgeResponse,
    DpmLineageResponse,
    DpmRunIdempotencyHistoryItem,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyHistoryResponse,
    DpmRunLookupResponse,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmRunWorkflowDecisionResponse,
)
from src.core.models import RebalanceResult


def to_lookup_response(run: DpmRunRecord) -> DpmRunLookupResponse:
    return DpmRunLookupResponse(
        rebalance_run_id=run.rebalance_run_id,
        correlation_id=run.correlation_id,
        request_hash=run.request_hash,
        idempotency_key=run.idempotency_key,
        portfolio_id=run.portfolio_id,
        created_at=run.created_at.isoformat(),
        result=RebalanceResult.model_validate(run.result_json),
    )


def to_async_accepted(operation: DpmAsyncOperationRecord) -> DpmAsyncAcceptedResponse:
    return DpmAsyncAcceptedResponse(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        correlation_id=operation.correlation_id,
        created_at=operation.created_at.isoformat(),
        status_url=f"/api/v1/rebalance/operations/{operation.operation_id}",
        execute_url=f"/api/v1/rebalance/operations/{operation.operation_id}/execute",
    )


def to_async_status(operation: DpmAsyncOperationRecord) -> DpmAsyncOperationStatusResponse:
    return DpmAsyncOperationStatusResponse(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        is_executable=(operation.status == "PENDING" and operation.request_json is not None),
        correlation_id=operation.correlation_id,
        created_at=operation.created_at.isoformat(),
        started_at=(operation.started_at.isoformat() if operation.started_at else None),
        finished_at=(operation.finished_at.isoformat() if operation.finished_at else None),
        result=operation.result_json,
        error=(
            DpmAsyncError.model_validate(operation.error_json)
            if operation.error_json is not None
            else None
        ),
    )


def to_workflow_decision_response(
    decision: DpmRunWorkflowDecisionRecord,
) -> DpmRunWorkflowDecisionResponse:
    return DpmRunWorkflowDecisionResponse(
        decision_id=decision.decision_id,
        run_id=decision.run_id,
        action=decision.action,
        reason_code=decision.reason_code,
        comment=decision.comment,
        actor_id=decision.actor_id,
        decided_at=decision.decided_at.isoformat(),
        correlation_id=decision.correlation_id,
    )


def lineage_cursor(edge: DpmLineageEdgeRecord) -> str:
    return (
        f"{edge.created_at.isoformat()}|{edge.source_entity_id}|"
        f"{edge.edge_type}|{edge.target_entity_id}"
    )


def to_lineage_response(
    *,
    entity_id: str,
    edges: list[DpmLineageEdgeRecord],
    next_cursor: str | None,
) -> DpmLineageResponse:
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
        next_cursor=next_cursor,
    )


def to_idempotency_history_response(
    *,
    idempotency_key: str,
    history: list[DpmRunIdempotencyHistoryRecord],
) -> DpmRunIdempotencyHistoryResponse:
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
