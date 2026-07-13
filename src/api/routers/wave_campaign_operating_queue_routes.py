from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_read_model_query import load_campaign_read_model_query
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignActorIdQuery,
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionStatusQuery,
    CampaignIncludeExpiredQuery,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
    CampaignRequestedAsOfDateQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignOperatingQueuePage,
    build_bulk_review_campaign_operating_queue_page,
)

router = APIRouter()


@router.get(
    "/campaign-operating-queue",
    response_model=DpmBulkReviewCampaignOperatingQueuePage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign operating queue",
    description=(
        "Returns a Manage-owned operating queue over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The queue composes discovery posture, "
        "fail-closed preview readiness, lifecycle event counts, launch-history posture, and "
        "bounded reason codes so operators can separate launch-ready campaigns from attention "
        "items and closed definitions. It does not discover the global portfolio universe, "
        "recalculate source facts, run maker-checker workflow, approve trades, generate orders, "
        "or claim OMS execution."
    ),
)
def list_bulk_review_campaign_operating_queue(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    include_expired: CampaignIncludeExpiredQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignOperatingQueuePage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_operating_queue_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )
