from __future__ import annotations

from fastapi import HTTPException

from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_workflow_telemetry import (
    campaign_workflow_http_exception,
    record_campaign_workflow_success,
    record_campaign_workflow_unexpected_error,
)
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
    surface = "launch_history"
    try:
        definition = get_campaign_definition_or_404(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
        )
        page = build_bulk_review_campaign_definition_launch_history_page(
            definition=definition,
            limit=limit,
            offset=offset,
        )
    except HTTPException as exc:
        raise campaign_workflow_http_exception(surface=surface, exc=exc) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_success(surface=surface)
    return page
