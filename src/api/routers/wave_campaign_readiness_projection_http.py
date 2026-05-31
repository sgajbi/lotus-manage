from __future__ import annotations

from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_launch_package_http import (
    get_campaign_definition_launch_package_response as get_campaign_definition_launch_package_response,
)
from src.api.routers.wave_campaign_workflow_overview_http import (
    get_campaign_definition_workflow_overview_response as get_campaign_definition_workflow_overview_response,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_preview_readiness,
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
