from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_idea_action_intake_parameters import (
    IdeaActionIntakeCorrelationIdHeader,
    IdeaActionIntakeIdempotencyKeyHeader,
)
from src.api.routers.rebalance_runs_idea_action_intake_principal import (
    require_idea_action_intake_principal,
)
from src.api.routers.rebalance_runs_idea_action_intake_responses import (
    IDEA_ACTION_INTAKE_RESPONSES,
)
from src.core.rebalance_runs import (
    IDEA_ACTION_INTAKE_REQUEST_EXAMPLE,
    IdeaActionIntakeIdempotencyConflictError,
    IdeaActionIntakeInvalidIdempotencyKeyError,
    IdeaActionIntakeRequest,
    IdeaActionIntakeResponse,
    process_idea_action_intake,
)
from src.core.rebalance_runs.idea_action_intake_authority import IdeaActionIntakePrincipal


_IDEA_ACTION_INTAKE_DESCRIPTION = (
    "Accepts a source-safe lotus-idea conversion-intent handoff for management-side review. "
    "This route proves a Manage-owned executable action-intake receipt with trusted caller scope, "
    "idempotent replay, and bounded accepted/rejected outcomes. It does not grant rebalance "
    "authority, create an action-register row, create orders, route OMS instructions, contact "
    "clients, authorize publication, or promote a supported feature."
)


@shared.router.post(
    "/rebalance/idea-action-intake",
    response_model=IdeaActionIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Accept lotus-idea Action Intake Receipt",
    description=_IDEA_ACTION_INTAKE_DESCRIPTION,
    responses=IDEA_ACTION_INTAKE_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"example": IDEA_ACTION_INTAKE_REQUEST_EXAMPLE}}
        }
    },
)
def accept_idea_action_intake(
    request: Request,
    payload: IdeaActionIntakeRequest,
    idempotency_key: IdeaActionIntakeIdempotencyKeyHeader,
    x_correlation_id: IdeaActionIntakeCorrelationIdHeader = None,
    principal: IdeaActionIntakePrincipal = Depends(require_idea_action_intake_principal),
) -> IdeaActionIntakeResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return process_idea_action_intake(
            payload,
            correlation_id=(x_correlation_id or "corr-idea-action-intake").strip()
            or "corr-idea-action-intake",
            idempotency_key=idempotency_key,
            principal=principal,
        )
    except IdeaActionIntakeInvalidIdempotencyKeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except IdeaActionIntakeIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
