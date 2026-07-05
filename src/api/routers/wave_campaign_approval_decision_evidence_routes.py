from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_approval_decision_http import (
    list_campaign_definition_approval_decisions_response,
    record_campaign_definition_approval_decision_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionRepository,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Campaign definition not found."},
        409: {"description": "Approval decision reference conflict."},
        422: {"description": "Approval decision semantic validation failed."},
    },
    summary="Record bulk-review campaign approval decision",
    description=(
        "Records an append-only approval decision on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. This mutates campaign approval evidence only: it "
        "does not run maker-checker workflow, approve trades, generate orders, route orders, "
        "contact clients, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_approval_decision_endpoint(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return record_campaign_definition_approval_decision_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
    response_model=DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign approval decisions",
    description=(
        "Returns a bounded append-only approval-decision page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes approval posture without "
        "creating maker-checker workflow, trade approval, order generation, order routing, client "
        "contact, or OMS execution claims."
    ),
)
def list_bulk_review_campaign_definition_approval_decisions(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
    return list_campaign_definition_approval_decisions_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )
