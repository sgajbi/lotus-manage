from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_construction_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.routers.wave_request_models import DpmWaveSimulationRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import WaveCorrelationIdHeader, WaveIdPath
from src.api.routers.wave_simulation_http import simulate_wave_response
from src.api.services.authority_client_service import RiskAuthorityClient
from src.core.construction.repository import ConstructionRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmWaveRepository


router = APIRouter()


@router.post(
    "/{wave_id}/simulate",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate construction alternatives for source-ready wave items",
    description=(
        "Calls the RFC-0039 construction alternative authority for source-ready wave items that "
        "have caller-supplied construction inputs. Source-blocked, degraded, and review-required "
        "items are preserved with their reasons. Ready items without construction input become "
        "`SIMULATION_BLOCKED`; the endpoint does not synthesize portfolio holdings, market data, "
        "model targets, or shelf data from mandate identifiers."
    ),
    responses={
        200: {"description": "Durable simulated or partially simulated wave."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave is not source-checked or request is invalid."},
    },
)
def simulate_wave(
    wave_id: WaveIdPath,
    request: DpmWaveSimulationRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: RiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return simulate_wave_response(
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_simulate_{wave_id}",
        construction_repository=construction_repository,
        run_service=run_service,
        wave_repository=wave_repository,
        risk_authority_client=risk_authority_client,
    )
