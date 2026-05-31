from typing import Annotated, Any

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowResponse,
)


_WORKFLOW_STATE_DESCRIPTION = (
    "Returns workflow gate state and latest reviewer decision for a discretionary mandate "
    "rebalance run. Use this endpoint when the caller needs the current review posture only; "
    "use workflow history when the full append-only decision trail is required. This endpoint "
    "does not accept query parameters."
)

_RouteResponses = dict[int | str, dict[str, Any]]

_WORKFLOW_STATE_RESPONSES: _RouteResponses = {
    200: {"description": "Current workflow state and latest reviewer decision for the run."},
    404: {"description": "Workflow disabled, run not found, or idempotency mapping not found."},
    422: {"description": "Unsupported query parameters were supplied."},
}


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow State",
    description=_WORKFLOW_STATE_DESCRIPTION,
    responses=_WORKFLOW_STATE_RESPONSES,
)
def get_dpm_run_workflow(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow State by Correlation Id",
    description=(
        "Returns workflow gate state for a discretionary mandate rebalance run resolved by "
        "submitted correlation id. Use this endpoint when an incident or Gateway trace has the "
        "run correlation id but not the run id. This endpoint does not accept query parameters."
    ),
    responses=_WORKFLOW_STATE_RESPONSES,
)
def get_dpm_run_workflow_by_correlation(
    request: Request,
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow State by Idempotency Key",
    description=(
        "Returns workflow gate state for a discretionary mandate rebalance run resolved by current "
        "idempotency-key mapping. Use this endpoint when a retry token is the available handle. "
        "This endpoint does not accept query parameters."
    ),
    responses=_WORKFLOW_STATE_RESPONSES,
)
def get_dpm_run_workflow_by_idempotency(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
