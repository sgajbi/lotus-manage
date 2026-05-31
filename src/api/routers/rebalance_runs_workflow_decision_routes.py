from typing import Annotated, Any, Optional

from fastapi import HTTPException, Path, Query, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowHistoryResponse,
    DpmWorkflowDecisionListResponse,
)
from src.core.rebalance_runs.models import DpmWorkflowActionType


_RouteResponses = dict[int | str, dict[str, Any]]

_WORKFLOW_HISTORY_RESPONSES: _RouteResponses = {
    200: {"description": "Append-only workflow decision history for the resolved run."},
    404: {"description": "Workflow disabled, run not found, or idempotency mapping not found."},
    422: {"description": "Unsupported query parameters were supplied."},
}


@shared.router.get(
    "/rebalance/workflow/decisions",
    response_model=DpmWorkflowDecisionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Workflow Decisions",
    description=(
        "Returns paginated workflow decisions across runs with optional filters for "
        "supportability investigations. Supported filters are `rebalance_run_id`, `action`, "
        "`actor_id`, `reason_code`, `decided_from`, `decided_to`, `limit`, and `cursor`; "
        "unsupported aliases are rejected."
    ),
    responses={
        200: {
            "description": (
                "Bounded page of workflow decisions ordered by newest decision timestamp."
            ),
        },
        404: {"description": "Support APIs or workflow APIs are disabled."},
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def list_dpm_workflow_decisions(
    request: Request,
    rebalance_run_id: Annotated[
        Optional[str],
        Query(
            description="Optional lotus-manage run id filter.",
            examples=["rr_abc12345"],
        ),
    ] = None,
    action: Annotated[
        Optional[DpmWorkflowActionType],
        Query(
            description="Optional workflow action filter.",
            examples=["APPROVE"],
        ),
    ] = None,
    actor_id: Annotated[
        Optional[str],
        Query(
            description="Optional reviewer actor id filter.",
            examples=["reviewer_001"],
        ),
    ] = None,
    reason_code: Annotated[
        Optional[str],
        Query(
            description="Optional uppercase reason code filter.",
            examples=["REVIEW_APPROVED"],
        ),
    ] = None,
    decided_from: Annotated[
        Optional[shared.datetime],
        Query(
            description="Decision timestamp lower bound (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    decided_to: Annotated[
        Optional[shared.datetime],
        Query(
            description="Decision timestamp upper bound (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["dwd_001"],
        ),
    ] = None,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmWorkflowDecisionListResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(
        request,
        allowed_params={
            "rebalance_run_id",
            "action",
            "actor_id",
            "reason_code",
            "decided_from",
            "decided_to",
            "limit",
            "cursor",
        },
    )
    return service.list_workflow_decisions(
        rebalance_run_id=rebalance_run_id,
        action=action,
        actor_id=actor_id,
        reason_code=reason_code,
        decided_from=decided_from,
        decided_to=decided_to,
        limit=limit,
        cursor=cursor,
    )


@shared.router.get(
    "/rebalance/workflow/decisions/by-correlation/{correlation_id}",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Workflow Decisions by Correlation Id",
    description=(
        "Returns append-only workflow decision history for the run resolved by correlation id. "
        "Use this endpoint when an incident or Gateway trace has the submitted run correlation id "
        "but not the run id. This endpoint does not accept query parameters."
    ),
    responses=_WORKFLOW_HISTORY_RESPONSES,
)
def get_dpm_workflow_decisions_by_correlation(
    request: Request,
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow_history_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
