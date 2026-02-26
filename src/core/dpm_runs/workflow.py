from src.core.dpm_runs.models import (
    DpmRunWorkflowDecisionRecord,
    DpmWorkflowActionType,
    DpmWorkflowStatus,
)

VALID_WORKFLOW_TRANSITIONS: dict[
    tuple[DpmWorkflowStatus, DpmWorkflowActionType], DpmWorkflowStatus
] = {
    ("PENDING_REVIEW", "APPROVE"): "APPROVED",
    ("PENDING_REVIEW", "REJECT"): "REJECTED",
    ("PENDING_REVIEW", "REQUEST_CHANGES"): "PENDING_REVIEW",
    ("APPROVED", "REQUEST_CHANGES"): "PENDING_REVIEW",
    ("APPROVED", "REJECT"): "REJECTED",
    ("REJECTED", "REQUEST_CHANGES"): "PENDING_REVIEW",
}


def workflow_required_for_run_status(
    *, workflow_enabled: bool, run_status: str, requires_review_for_statuses: set[str]
) -> bool:
    return workflow_enabled and run_status in requires_review_for_statuses


def status_for_action(action: DpmWorkflowActionType) -> DpmWorkflowStatus:
    if action == "APPROVE":
        return "APPROVED"
    if action == "REJECT":
        return "REJECTED"
    return "PENDING_REVIEW"


def resolve_workflow_status(
    *,
    workflow_enabled: bool,
    run_status: str,
    latest_decision: DpmRunWorkflowDecisionRecord | None,
    requires_review_for_statuses: set[str],
) -> DpmWorkflowStatus:
    if not workflow_required_for_run_status(
        workflow_enabled=workflow_enabled,
        run_status=run_status,
        requires_review_for_statuses=requires_review_for_statuses,
    ):
        return "NOT_REQUIRED"
    if latest_decision is None:
        return "PENDING_REVIEW"
    return status_for_action(latest_decision.action)


def resolve_workflow_transition(
    *, current_status: DpmWorkflowStatus, action: DpmWorkflowActionType
) -> DpmWorkflowStatus | None:
    return VALID_WORKFLOW_TRANSITIONS.get((current_status, action))
