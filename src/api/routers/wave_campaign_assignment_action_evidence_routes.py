from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_action_http import (
    list_campaign_definition_assignment_actions_response,
    record_campaign_definition_assignment_action_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionRepository,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Record bulk-review campaign assignment action",
    description=(
        "Records an append-only assignment or escalation action on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. This mutates campaign assignment posture only: it "
        "does not mutate approval state, run maker-checker workflow, approve trades, generate "
        "orders, route orders, contact clients, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_assignment_action_endpoint(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return record_campaign_definition_assignment_action_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
    response_model=DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign assignment actions",
    description=(
        "Returns a bounded append-only assignment-action page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes current assigned actors, "
        "escalation tier, and SLA posture without creating maker-checker workflow, mutating "
        "approval state, trade approval, order generation, order routing, client contact, or OMS "
        "execution claims."
    ),
)
def list_bulk_review_campaign_definition_assignment_actions(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    return list_campaign_definition_assignment_actions_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )
