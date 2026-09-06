from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.routers.mandate_tenant_query import MandateTenantId
from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.routers.wave_request_models import DpmWaveSelectionRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import (
    WaveCorrelationIdHeader,
    WaveIdPath,
    WaveItemIdPath,
)
from src.api.routers.wave_selection_http import select_wave_item_alternative_response
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmWaveRepository


router = APIRouter()


@router.post(
    "/{wave_id}/items/{wave_item_id}/select",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative for a wave item",
    description=(
        "Records item-level RFC-0039 alternative selection with actor, reason, and optional "
        "comment. When requested, it generates an RFC-0040 proof pack from the selected "
        "alternative. Proof-pack failures are represented as degraded selection posture instead "
        "of unsupported proof-pack readiness."
    ),
    responses={
        200: {"description": "Wave item selection recorded and persisted."},
        404: {"description": "Wave, item, alternative set, or alternative id was not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave or item is not eligible for selection."},
    },
)
def select_wave_item_alternative(
    wave_id: WaveIdPath,
    wave_item_id: WaveItemIdPath,
    request: DpmWaveSelectionRequest,
    tenant_id: MandateTenantId,
    x_correlation_id: WaveCorrelationIdHeader = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return select_wave_item_alternative_response(
        tenant_id=tenant_id,
        wave_id=wave_id,
        wave_item_id=wave_item_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_select_{wave_id}_{wave_item_id}",
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
        wave_repository=wave_repository,
    )
