from __future__ import annotations

from fastapi import HTTPException, status

from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionRepository,
)


_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL = {
    "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
    "message": "Bulk-review campaign definition was not found.",
}


def get_campaign_definition_or_404(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str,
    campaign_version: str,
) -> DpmBulkReviewCampaignDefinition:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL,
        )
    return definition
