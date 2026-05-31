from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, status

from src.api.observability import record_workflow_decision
from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunWorkflowResponse,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.rebalance_runs.models import DpmWorkflowActionType

WorkflowActionCallback = Callable[[], DpmRunWorkflowResponse]


def _record_workflow_action_metric(
    *,
    surface: str,
    action: DpmWorkflowActionType,
    outcome: str,
) -> None:
    record_workflow_decision(
        surface=surface,
        action=action.lower(),
        outcome=outcome,
    )


def apply_workflow_action_with_http_mapping(
    *,
    surface: str,
    action: DpmWorkflowActionType,
    apply_action: WorkflowActionCallback,
) -> DpmRunWorkflowResponse:
    try:
        response = apply_action()
        _record_workflow_action_metric(surface=surface, action=action, outcome="success")
        return response
    except DpmRunNotFoundError as exc:
        _record_workflow_action_metric(surface=surface, action=action, outcome="not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        _record_workflow_action_metric(surface=surface, action=action, outcome="disabled")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        _record_workflow_action_metric(surface=surface, action=action, outcome="conflict")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
