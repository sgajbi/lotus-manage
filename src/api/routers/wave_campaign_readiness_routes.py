from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_preview_readiness_http import (
    get_campaign_definition_preview_readiness_response,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignLaunchActorIdOptionalQuery,
    CampaignLaunchRequestedAsOfDateQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness",
    response_model=DpmBulkReviewCampaignDefinitionPreviewReadiness,
    status_code=status.HTTP_200_OK,
    summary="Check bulk-review campaign definition preview readiness",
    description=(
        "Evaluates whether one persisted Manage-owned `BulkReviewCampaignDefinition:v1` can be "
        "used for new `BULK_REVIEW_CAMPAIGN` preview/create. The response is a bounded "
        "fail-closed supportability check over lifecycle status, as-of date, source-backed "
        "candidate eligibility, approval evidence, expiry, and optional actor entitlement. It "
        "does not create a wave, discover the global portfolio universe, recalculate membership, "
        "run maker-checker workflow, approve trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_preview_readiness(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdOptionalQuery = None,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    return get_campaign_definition_preview_readiness_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        repository=repository,
    )
