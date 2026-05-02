from typing import Annotated, Any, Optional

from fastapi import Header, HTTPException, Path, Query, Request, status

from src.api.observability import record_workflow_decision
from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowActionRequest,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmWorkflowDecisionListResponse,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.rebalance_runs.models import DpmWorkflowActionType


_WORKFLOW_STATE_DESCRIPTION = (
    "Returns workflow gate state and latest reviewer decision for a discretionary mandate "
    "rebalance run. Use this endpoint when the caller needs the current review posture only; "
    "use workflow history when the full append-only decision trail is required. This endpoint "
    "does not accept query parameters."
)

_WORKFLOW_HISTORY_DESCRIPTION = (
    "Returns append-only workflow decision history for discretionary mandate run-level audit, "
    "review reconstruction, and supportability investigation. Use workflow state endpoints when "
    "only the current gate posture is required. This endpoint does not accept query parameters."
)

_WORKFLOW_ACTION_DESCRIPTION = (
    "Applies one workflow action (`APPROVE`, `REJECT`, `REQUEST_CHANGES`) for a discretionary "
    "mandate rebalance run and returns updated workflow state. Supply the reviewer action in the "
    "request body and optional `X-Correlation-Id` header for action traceability. This endpoint "
    "does not accept query parameters."
)

_RouteResponses = dict[int | str, dict[str, Any]]


_WORKFLOW_STATE_RESPONSES: _RouteResponses = {
    200: {"description": "Current workflow state and latest reviewer decision for the run."},
    404: {"description": "Workflow disabled, run not found, or idempotency mapping not found."},
    422: {"description": "Unsupported query parameters were supplied."},
}

_WORKFLOW_HISTORY_RESPONSES: _RouteResponses = {
    200: {"description": "Append-only workflow decision history for the resolved run."},
    404: {"description": "Workflow disabled, run not found, or idempotency mapping not found."},
    422: {"description": "Unsupported query parameters were supplied."},
}

_WORKFLOW_ACTION_RESPONSES: _RouteResponses = {
    200: {"description": "Updated workflow state after applying the reviewer action."},
    404: {"description": "Workflow disabled, run not found, or idempotency mapping not found."},
    409: {"description": "Workflow action is not valid for the current run state."},
    422: {"description": "Invalid action payload or unsupported query parameters were supplied."},
}


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


@shared.router.post(
    "/rebalance/runs/{rebalance_run_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply lotus-manage Run Workflow Action",
    description=_WORKFLOW_ACTION_DESCRIPTION,
    responses=_WORKFLOW_ACTION_RESPONSES,
)
def apply_dpm_run_workflow_action(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        response = service.apply_workflow_action(
            rebalance_run_id=rebalance_run_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            correlation_id=x_correlation_id or "c_none",
        )
        _record_workflow_action_metric(surface="run", action=payload.action, outcome="success")
        return response
    except DpmRunNotFoundError as exc:
        _record_workflow_action_metric(surface="run", action=payload.action, outcome="not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        _record_workflow_action_metric(surface="run", action=payload.action, outcome="disabled")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        _record_workflow_action_metric(surface="run", action=payload.action, outcome="conflict")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply lotus-manage Run Workflow Action by Correlation Id",
    description=(
        "Applies one workflow action for a discretionary mandate rebalance run resolved by "
        "submitted correlation id and returns updated workflow state. Use this endpoint when the "
        "run id is not available but the submitted run correlation id is. This endpoint does not "
        "accept query parameters."
    ),
    responses=_WORKFLOW_ACTION_RESPONSES,
)
def apply_dpm_run_workflow_action_by_correlation(
    request: Request,
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        response = service.apply_workflow_action_by_correlation(
            correlation_id=correlation_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=x_correlation_id or "c_none",
        )
        _record_workflow_action_metric(
            surface="trace",
            action=payload.action,
            outcome="success",
        )
        return response
    except DpmRunNotFoundError as exc:
        _record_workflow_action_metric(
            surface="trace",
            action=payload.action,
            outcome="not_found",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        _record_workflow_action_metric(
            surface="trace",
            action=payload.action,
            outcome="disabled",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        _record_workflow_action_metric(
            surface="trace",
            action=payload.action,
            outcome="conflict",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply lotus-manage Run Workflow Action by Idempotency Key",
    description=(
        "Applies one workflow action for a discretionary mandate rebalance run resolved by current "
        "idempotency-key mapping and returns updated workflow state. Use this endpoint when a "
        "retry token is the available operational handle. This endpoint does not accept query "
        "parameters."
    ),
    responses=_WORKFLOW_ACTION_RESPONSES,
)
def apply_dpm_run_workflow_action_by_idempotency(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-002"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        response = service.apply_workflow_action_by_idempotency(
            idempotency_key=idempotency_key,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=x_correlation_id or "c_none",
        )
        _record_workflow_action_metric(
            surface="retry",
            action=payload.action,
            outcome="success",
        )
        return response
    except DpmRunNotFoundError as exc:
        _record_workflow_action_metric(
            surface="retry",
            action=payload.action,
            outcome="not_found",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        _record_workflow_action_metric(
            surface="retry",
            action=payload.action,
            outcome="disabled",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        _record_workflow_action_metric(
            surface="retry",
            action=payload.action,
            outcome="conflict",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow History",
    description=_WORKFLOW_HISTORY_DESCRIPTION,
    responses=_WORKFLOW_HISTORY_RESPONSES,
)
def get_dpm_run_workflow_history(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow_history(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow History by Correlation Id",
    description=(
        "Returns append-only workflow decision history for a discretionary mandate rebalance run "
        "resolved by submitted correlation id. Use this endpoint when the run id is not available. "
        "This endpoint does not accept query parameters."
    ),
    responses=_WORKFLOW_HISTORY_RESPONSES,
)
def get_dpm_run_workflow_history_by_correlation(
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


@shared.router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Workflow History by Idempotency Key",
    description=(
        "Returns append-only workflow decision history for a discretionary mandate rebalance run "
        "resolved by current idempotency-key mapping. Use this endpoint when a retry token is the "
        "available operational handle. This endpoint does not accept query parameters."
    ),
    responses=_WORKFLOW_HISTORY_RESPONSES,
)
def get_dpm_run_workflow_history_by_idempotency(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_workflow_history_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
