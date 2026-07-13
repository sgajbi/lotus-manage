from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_campaign_definition_repository,
    get_mandate_repository,
    get_wave_repository,
)
from src.api.routers.wave_campaign_launch_http import (
    launch_bulk_review_campaign_definition_response,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignDefinitionLaunchRequest
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
)
from src.api.services.core_resolver_service import build_core_resolver_client
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveRepository,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch bulk-review campaign definition",
    description=(
        "Creates a durable `BULK_REVIEW_CAMPAIGN` wave from one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1` only when its launch package is ready. The endpoint "
        "uses the persisted source-backed candidate set and deterministic launch idempotency key; "
        "it does not discover the global portfolio universe, recalculate membership, run "
        "maker-checker workflow, approve trades, route orders, or claim OMS execution."
    ),
)
def launch_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    return launch_bulk_review_campaign_definition_response(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
        campaign_definition_repository=campaign_definition_repository,
        core_resolver_factory=build_core_resolver_client,
    )
