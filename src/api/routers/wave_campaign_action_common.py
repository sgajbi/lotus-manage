from __future__ import annotations

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_not_found_http_exception,
)
from src.core.waves import DpmBulkReviewCampaignDefinition


def persisted_definition_or_404(
    persisted: DpmBulkReviewCampaignDefinition | None,
) -> DpmBulkReviewCampaignDefinition:
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted
