from __future__ import annotations

from src.api.routers.wave_campaign_definition_http import (
    get_campaign_definition_or_404,
    parse_optional_campaign_discovery_date,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
    build_bulk_review_campaign_definition_launch_history_page,
    build_bulk_review_campaign_definition_launch_package,
    build_bulk_review_campaign_definition_preview_readiness,
    build_bulk_review_campaign_definition_workflow_overview,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    build_bulk_review_campaign_definition_lifecycle_events,
)


def list_campaign_definition_lifecycle_events_response(
    *,
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_lifecycle_events(definition=definition)


def list_campaign_definition_launch_history_response(
    *,
    campaign_id: str,
    campaign_version: str,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )


def get_campaign_definition_workflow_overview_response(
    *,
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: str | None,
    include_launch_package: bool,
    correlation_id: str | None,
    launch_history_limit: int,
    launch_history_offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    return build_bulk_review_campaign_definition_workflow_overview(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        launch_history_limit=launch_history_limit,
        launch_history_offset=launch_history_offset,
        include_launch_package=include_launch_package,
        correlation_id=correlation_id,
    )


def get_campaign_definition_preview_readiness_response(
    *,
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str,
    actor_id: str | None,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )


def get_campaign_definition_launch_package_response(
    *,
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str,
    actor_id: str,
    correlation_id: str | None,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_launch_package(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
    )
