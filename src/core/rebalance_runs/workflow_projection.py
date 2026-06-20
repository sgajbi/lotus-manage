from datetime import datetime
from typing import Sequence

import uuid

from src.core.rebalance_runs.models import (
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmWorkflowActionType,
    DpmWorkflowStatus,
)
from src.core.rebalance_runs.serializers import to_workflow_decision_response
from src.core.rebalance_runs.workflow import (
    resolve_workflow_status,
    workflow_required_for_run_status,
)


def latest_workflow_decision(
    decisions: Sequence[DpmRunWorkflowDecisionRecord],
) -> DpmRunWorkflowDecisionRecord | None:
    if not decisions:
        return None
    return max(decisions, key=lambda item: item.decided_at)


def build_workflow_history_response(
    *,
    rebalance_run_id: str,
    decisions: Sequence[DpmRunWorkflowDecisionRecord],
) -> DpmRunWorkflowHistoryResponse:
    ordered_decisions = sorted(decisions, key=lambda item: item.decided_at)
    return DpmRunWorkflowHistoryResponse(
        run_id=rebalance_run_id,
        decisions=[to_workflow_decision_response(decision) for decision in ordered_decisions],
    )


def build_workflow_response(
    *,
    run: DpmRunRecord,
    latest_decision: DpmRunWorkflowDecisionRecord | None,
    workflow_enabled: bool,
    requires_review_for_statuses: set[str],
) -> DpmRunWorkflowResponse:
    run_status = str(run.result_json.get("status", ""))
    workflow_status = resolve_workflow_status(
        workflow_enabled=workflow_enabled,
        run_status=run_status,
        latest_decision=latest_decision,
        requires_review_for_statuses=requires_review_for_statuses,
    )
    return DpmRunWorkflowResponse(
        run_id=run.rebalance_run_id,
        run_status=run_status,
        workflow_status=workflow_status,
        requires_review=workflow_required_for_run_status(
            workflow_enabled=workflow_enabled,
            run_status=run_status,
            requires_review_for_statuses=requires_review_for_statuses,
        ),
        latest_decision=(
            to_workflow_decision_response(latest_decision) if latest_decision is not None else None
        ),
    )


def build_workflow_decision_record(
    *,
    rebalance_run_id: str,
    action: DpmWorkflowActionType,
    reason_code: str,
    comment: str | None,
    actor_id: str,
    correlation_id: str,
    decided_at: datetime,
) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=f"dwd_{uuid.uuid4().hex[:12]}",
        run_id=rebalance_run_id,
        action=action,
        reason_code=reason_code,
        comment=comment,
        actor_id=actor_id,
        decided_at=decided_at,
        correlation_id=correlation_id,
    )


def build_workflow_action_response(
    *,
    rebalance_run_id: str,
    run_status: str,
    workflow_status: DpmWorkflowStatus,
    decision: DpmRunWorkflowDecisionRecord,
) -> DpmRunWorkflowResponse:
    return DpmRunWorkflowResponse(
        run_id=rebalance_run_id,
        run_status=run_status,
        workflow_status=workflow_status,
        requires_review=True,
        latest_decision=to_workflow_decision_response(decision),
    )
