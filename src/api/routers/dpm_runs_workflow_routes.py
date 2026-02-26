from typing import Annotated, Optional

from fastapi import Header, HTTPException, Path, Query, status

from src.api.routers import dpm_runs as shared
from src.core.dpm_runs import (
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowActionRequest,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmWorkflowDecisionListResponse,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.dpm_runs.models import DpmWorkflowActionType


@shared.router.get(
    "/rebalance/workflow/decisions",
    response_model=DpmWorkflowDecisionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List DPM Workflow Decisions",
    description=(
        "Returns paginated workflow decisions across runs with optional filters for "
        "supportability investigations."
    ),
)
def list_dpm_workflow_decisions(
    rebalance_run_id: Annotated[
        Optional[str],
        Query(
            description="Optional DPM run id filter.",
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
            alias="from",
            description="Decision timestamp lower bound (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    decided_to: Annotated[
        Optional[shared.datetime],
        Query(
            alias="to",
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
    summary="Get DPM Workflow Decisions by Correlation Id",
    description=(
        "Returns append-only workflow decision history for the run resolved by correlation id."
    ),
)
def get_dpm_workflow_decisions_by_correlation(
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
    try:
        return service.get_workflow_history_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State",
    description=(
        "Returns workflow gate state and latest decision for run-level review supportability."
    ),
)
def get_dpm_run_workflow(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State by Correlation Id",
    description="Returns workflow gate state for run resolved by correlation id.",
)
def get_dpm_run_workflow_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State by Idempotency Key",
    description="Returns workflow gate state for run resolved by idempotency key mapping.",
)
def get_dpm_run_workflow_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/runs/{rebalance_run_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action",
    description=(
        "Applies one workflow action (`APPROVE`, `REJECT`, `REQUEST_CHANGES`) and returns "
        "updated workflow state."
    ),
)
def apply_dpm_run_workflow_action(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.apply_workflow_action(
            rebalance_run_id=rebalance_run_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            correlation_id=correlation_id or "c_none",
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action by Correlation Id",
    description=(
        "Applies one workflow action for run resolved by correlation id and returns updated "
        "workflow state."
    ),
)
def apply_dpm_run_workflow_action_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    action_correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.apply_workflow_action_by_correlation(
            correlation_id=correlation_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=action_correlation_id or "c_none",
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action by Idempotency Key",
    description=(
        "Applies one workflow action for run resolved by idempotency key mapping and returns "
        "updated workflow state."
    ),
)
def apply_dpm_run_workflow_action_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
    action_correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-002"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.apply_workflow_action_by_idempotency(
            idempotency_key=idempotency_key,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=action_correlation_id or "c_none",
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History",
    description=(
        "Returns append-only workflow decision history for run-level audit and investigation."
    ),
)
def get_dpm_run_workflow_history(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow_history(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History by Correlation Id",
    description="Returns workflow decision history for run resolved by correlation id.",
)
def get_dpm_run_workflow_history_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow_history_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History by Idempotency Key",
    description="Returns workflow decision history for run resolved by idempotency key mapping.",
)
def get_dpm_run_workflow_history_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunWorkflowHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_workflow_enabled()
    try:
        return service.get_workflow_history_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
