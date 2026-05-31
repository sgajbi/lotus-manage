from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_action_http import (
    list_campaign_definition_maker_checker_controls_response,
    record_campaign_definition_maker_checker_control_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionRepository,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Record bulk-review campaign maker-checker control",
    description=(
        "Records append-only maker-checker control evidence on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. Completed reviews require distinct submitter and "
        "reviewer actors. This evidence does not approve trades, generate orders, route orders, "
        "contact clients, orchestrate external workflow systems, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_maker_checker_control_endpoint(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return record_campaign_definition_maker_checker_control_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
    response_model=DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign maker-checker controls",
    description=(
        "Returns a bounded append-only maker-checker control page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes current control posture "
        "without trade approval, order generation, order routing, client contact, external "
        "workflow orchestration, or OMS execution claims."
    ),
)
def list_bulk_review_campaign_definition_maker_checker_controls(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    return list_campaign_definition_maker_checker_controls_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )
