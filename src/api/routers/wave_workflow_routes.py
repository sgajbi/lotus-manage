from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_repository
from src.api.routers.wave_request_models import DpmWaveWorkflowCommandRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import WaveCorrelationIdHeader, WaveIdPath
from src.api.routers.wave_workflow_command_http import run_wave_workflow_command_response
from src.api.services import wave_service
from src.core.waves import DpmWaveRepository


router = APIRouter()


@router.post(
    "/{wave_id}/approve",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve selected rebalance wave items",
    description=(
        "Approves selected or proof-pack-ready wave items with actor attribution. Source-blocked, "
        "simulation-blocked, degraded, failed, or otherwise unselected items are never approved; "
        "mixed waves become `APPROVED_WITH_EXCEPTIONS`. Repeating the command after approval "
        "returns the persisted wave without appending duplicate approval evidence."
    ),
    responses={
        200: {"description": "Wave approval recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no eligible items or is not approval-ready."},
    },
)
def approve_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.approve_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_approve_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/stage",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Stage approved rebalance wave items",
    description=(
        "Stages approved wave items for internal operations handoff. The endpoint does not stage "
        "blocked or unapproved items and does not claim external order execution. Repeating the "
        "command after staging or handoff readiness returns the persisted wave without duplicate "
        "events."
    ),
    responses={
        200: {"description": "Wave staging recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no approved items or is not stage-ready."},
    },
)
def stage_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.stage_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_stage_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/handoff",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Create internal operations handoff evidence",
    description=(
        "Creates append-only internal operations handoff evidence for staged wave items. This is "
        "a manage-owned readiness package only: it records `external_execution_claimed=false` and "
        "does not send orders, client communications, or external execution instructions."
    ),
    responses={
        200: {"description": "Wave handoff evidence recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no staged items or is not handoff-ready."},
    },
)
def handoff_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.handoff_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_handoff_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/cancel",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a rebalance wave before external execution",
    description=(
        "Cancels an eligible RFC-0041 wave with actor attribution and preserves all item evidence. "
        "Items that have not reached internal handoff are marked `EXCLUDED` with cancellation "
        "diagnostics; manage still records `external_execution_claimed=false`. The endpoint does "
        "not cancel external orders, because manage wave handoff is an internal readiness package "
        "and not an execution instruction. Repeating the command after cancellation returns the "
        "persisted wave without duplicate cancellation events."
    ),
    responses={
        200: {"description": "Wave cancellation recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave state cannot be cancelled."},
    },
)
def cancel_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.cancel_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_cancel_{wave_id}",
        wave_repository=wave_repository,
    )
