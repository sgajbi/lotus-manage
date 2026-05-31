from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_campaign_definition_repository,
)
from src.api.routers.wave_campaign_definition_http import (
    get_campaign_definition_response,
)
from src.api.routers.wave_campaign_definition_routes import (
    router as campaign_definition_router,
)
from src.api.routers.wave_campaign_evidence_routes import (
    router as campaign_evidence_router,
)
from src.api.routers.wave_campaign_launch_routes import (
    router as campaign_launch_router,
)
from src.api.routers.wave_campaign_read_model_routes import (
    router as campaign_read_model_router,
)
from src.api.routers.wave_campaign_readiness_routes import (
    router as campaign_readiness_router,
)
from src.api.routers.wave_create_preview_routes import register_wave_create_preview_routes
from src.api.routers.wave_source_check_routes import (
    router as source_check_router,
)
from src.api.routers.wave_simulation_routes import (
    router as simulation_router,
)
from src.api.routers.wave_selection_routes import (
    router as selection_router,
)
from src.api.routers.wave_workflow_routes import (
    router as workflow_router,
)
from src.api.routers.wave_read_routes import register_wave_read_routes
from src.api.routers.wave_read_support_routes import (
    router as wave_read_support_router,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
)
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionRepository,
)

router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])
logger = logging.getLogger(__name__)

router.include_router(campaign_definition_router)
router.include_router(campaign_read_model_router)


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign definition",
    description="Retrieves one immutable Manage-owned bulk-review campaign definition.",
)
def get_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        repository=repository,
    )


router.include_router(campaign_evidence_router)
router.include_router(campaign_readiness_router)
router.include_router(campaign_launch_router)
register_wave_create_preview_routes(
    router,
    core_resolver_factory_provider=lambda: build_core_resolver_client,
)
register_wave_read_routes(router)


router.include_router(source_check_router)
router.include_router(simulation_router)
router.include_router(selection_router)
router.include_router(workflow_router)
router.include_router(wave_read_support_router)
