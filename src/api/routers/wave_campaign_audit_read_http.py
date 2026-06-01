from __future__ import annotations

from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_launch_history_page,
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
