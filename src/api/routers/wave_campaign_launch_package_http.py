from __future__ import annotations

from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_launch_package,
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
