from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_workflow_overview_http import (
    get_campaign_definition_workflow_overview_response,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignIncludeLaunchPackageQuery,
    CampaignLaunchActorIdOptionalQuery,
    CampaignLaunchCorrelationIdQuery,
    CampaignLaunchHistoryLimitQuery,
    CampaignLaunchHistoryOffsetQuery,
    CampaignLaunchRequestedAsOfDateQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview",
    response_model=DpmBulkReviewCampaignDefinitionWorkflowOverview,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign workflow overview",
    description=(
        "Returns an operator-safe workflow overview for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The overview composes discovery posture, "
        "fail-closed preview readiness, lifecycle events, launch history, and optional launch "
        "package guidance. It does not discover the global portfolio universe, recalculate "
        "source facts, run maker-checker workflow, approve trades, route orders, or claim OMS "
        "execution."
    ),
)
def get_bulk_review_campaign_definition_workflow_overview(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdOptionalQuery = None,
    active_on: CampaignActiveOnQuery = None,
    include_launch_package: CampaignIncludeLaunchPackageQuery = True,
    correlation_id: CampaignLaunchCorrelationIdQuery = None,
    launch_history_limit: CampaignLaunchHistoryLimitQuery = 20,
    launch_history_offset: CampaignLaunchHistoryOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
    return get_campaign_definition_workflow_overview_response(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
        launch_history_limit=launch_history_limit,
        launch_history_offset=launch_history_offset,
        include_launch_package=include_launch_package,
        correlation_id=correlation_id,
        repository=repository,
    )
