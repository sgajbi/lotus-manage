from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_mandate_repository, get_wave_repository
from src.api.routers.wave_openapi_examples import SOURCE_CHECK_WAVE_EXAMPLE
from src.api.routers.wave_request_models import DpmWaveSourceCheckRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import WaveCorrelationIdHeader, WaveIdPath
from src.api.routers.wave_source_check_http import source_check_wave_response
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmWaveRepository


router = APIRouter()


@router.post(
    "/{wave_id}/source-check",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Source-check a durable rebalance wave",
    description=(
        "Evaluates RFC-0041 source readiness for each durable wave item using persisted mandate "
        "digital twins, mandate health snapshots, and their source lineage. Items are classified "
        "as `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, or `SOURCE_BLOCKED`; caller "
        "portfolio ids or supplied refs alone never promote an item to ready. Repeating the call "
        "after the wave is already `SOURCE_CHECKED` returns the persisted wave as an idempotent "
        "replay without appending a duplicate event."
    ),
    responses={
        200: {
            "description": "Durable source-checked wave with item classifications.",
            "content": {"application/json": {"example": SOURCE_CHECK_WAVE_EXAMPLE}},
        },
        404: {
            "description": "Wave not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_NOT_FOUND",
                            "message": "Wave dwv_missing was not found.",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Wave version conflict during optimistic update.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_VERSION_CONFLICT",
                            "message": "DPM_WAVE_VERSION_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Wave is not in a state that can be source-checked.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
                            "message": "Wave dwv_001 cannot be source-checked from state DRAFT.",
                        }
                    }
                }
            },
        },
    },
)
def source_check_wave(
    wave_id: WaveIdPath,
    request: DpmWaveSourceCheckRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return source_check_wave_response(
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_source_check_{wave_id}",
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
    )
