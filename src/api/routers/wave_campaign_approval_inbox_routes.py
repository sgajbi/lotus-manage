from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_read_model_query import load_campaign_read_model_query
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignActorIdQuery,
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionStatusQuery,
    CampaignIncludeClosedQuery,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
    CampaignRequestedAsOfDateQuery,
)
from src.core.waves import (
    CampaignApprovalInboxStatus,
    DpmBulkReviewCampaignApprovalInboxPage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_approval_inbox_page,
)

router = APIRouter()


@router.get(
    "/campaign-approval-inbox",
    response_model=DpmBulkReviewCampaignApprovalInboxPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign approval attention inbox",
    description=(
        "Returns a read-only approval attention inbox over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The inbox classifies approval-complete, "
        "approval-required, approval-incomplete, expiry-attention, entitlement-attention, and "
        "closed campaign definitions from existing governance evidence and fail-closed readiness "
        "checks. It does not mutate approval state, create maker-checker workflow, approve trades, "
        "generate orders, or claim OMS execution."
    ),
)
def list_bulk_review_campaign_approval_inbox(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    inbox_status: CampaignApprovalInboxStatus | None = Query(
        default=None,
        description="Optional filter for one approval attention posture.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignApprovalInboxPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_approval_inbox_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
        include_closed=include_closed,
        inbox_status=inbox_status,
        limit=limit,
        offset=offset,
    )
