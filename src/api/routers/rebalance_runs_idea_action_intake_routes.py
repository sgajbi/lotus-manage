from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    IDEA_ACTION_INTAKE_ERROR_EXAMPLE,
    IDEA_ACTION_INTAKE_REQUEST_EXAMPLE,
    IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE,
    IdeaActionIntakeRequest,
    IdeaActionIntakeResponse,
    acknowledge_idea_action_intake,
)


_IDEA_ACTION_INTAKE_DESCRIPTION = (
    "Accepts a source-safe lotus-idea conversion-intent handoff for management-side review. "
    "This route proves only a Manage-owned route foundation for future action-register "
    "realization. It does not grant rebalance authority, create an action register row, create "
    "orders, route OMS instructions, contact clients, authorize publication, or promote a "
    "supported feature."
)


@shared.router.post(
    "/rebalance/idea-action-intake",
    response_model=IdeaActionIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Accept lotus-idea Action Intake Foundation",
    description=_IDEA_ACTION_INTAKE_DESCRIPTION,
    responses={
        202: {
            "description": (
                "Source-safe route-foundation acknowledgement. This is not execution or "
                "action-register creation proof."
            ),
            "content": {"application/json": {"example": IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE}},
        },
        422: {
            "description": "Invalid payload or unsupported query parameters were supplied.",
            "content": {"application/json": {"example": IDEA_ACTION_INTAKE_ERROR_EXAMPLE}},
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"example": IDEA_ACTION_INTAKE_REQUEST_EXAMPLE}}
        }
    },
)
def accept_idea_action_intake(
    request: Request,
    payload: IdeaActionIntakeRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional source-safe correlation id supplied by lotus-idea.",
            examples=["corr-idea-action-001"],
        ),
    ] = None,
) -> IdeaActionIntakeResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    return acknowledge_idea_action_intake(
        payload,
        correlation_id=x_correlation_id or "corr-idea-action-intake",
    )
