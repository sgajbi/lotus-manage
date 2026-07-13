from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    parse_optional_campaign_discovery_date,
)
from src.api.routers.wave_campaign_read_model_paging import (
    campaign_read_model_repository_paging,
    record_campaign_read_model_paging,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.services.wave_campaign_application import DpmWaveCampaignApplicationService
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignApprovalInboxPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    projection_safe = (
        requested_as_of_date is None
        and actor_id is None
        and active_on_date is None
        and inbox_status is None
    )
    paging = campaign_read_model_repository_paging(
        repository_safe=projection_safe,
        limit=limit,
        offset=offset,
        bounded_reason="workflow_projection_filters",
    )
    record_campaign_read_model_paging(surface="campaign_approval_inbox", paging=paging)
    campaign_query = application_service.load_campaign_read_model_query(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on_date,
        use_workflow_projection=projection_safe,
        include_closed=include_closed,
        page_limit=paging.page_limit,
        page_offset=paging.page_offset,
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
