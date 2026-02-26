from src.core.dpm_runs.models import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationRecord,
    DpmAsyncOperationStatusResponse,
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
        status_url=f"/rebalance/operations/{operation.operation_id}",
        execute_url=f"/rebalance/operations/{operation.operation_id}/execute",
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
        error=operation.error_json,
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
