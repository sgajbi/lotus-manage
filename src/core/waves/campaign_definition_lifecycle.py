from __future__ import annotations

from datetime import datetime, timezone

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository


class DpmBulkReviewCampaignDefinitionLifecycleError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


def retire_bulk_review_campaign_definition(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str,
    campaign_version: str,
    retired_by: str,
    retirement_reason: str,
    correlation_id: str,
    retired_at: datetime | None = None,
) -> DpmBulkReviewCampaignDefinition | None:
    existing = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if existing is None:
        return None
    if existing.status == "RETIRED":
        return existing
    if existing.status != "ACTIVE":
        raise DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
            "Only active campaign definitions can be retired.",
        )
    retired_payload = existing.model_dump(mode="python")
    retired_payload.update(
        {
            "status": "RETIRED",
            "retired_at": retired_at or datetime.now(timezone.utc),
            "retired_by": retired_by,
            "retirement_reason": retirement_reason,
            "retirement_correlation_id": correlation_id,
            "content_hash": "",
        }
    )
    retired_definition = DpmBulkReviewCampaignDefinition.model_validate(retired_payload)
    return repository.retire_definition(definition=retired_definition)


def supersede_bulk_review_campaign_definition(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str,
    campaign_version: str,
    replacement_version: str,
    superseded_by: str,
    supersession_reason: str,
    correlation_id: str,
    superseded_at: datetime | None = None,
) -> DpmBulkReviewCampaignDefinition | None:
    existing = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if existing is None:
        return None
    if existing.status == "SUPERSEDED":
        return existing
    if existing.status != "ACTIVE":
        raise DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
            "Only active campaign definitions can be superseded.",
        )
    replacement_version = replacement_version.strip()
    if not replacement_version or replacement_version == campaign_version:
        raise DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID",
            "superseded_by_campaign_version must identify a different version.",
        )
    replacement = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=replacement_version,
    )
    if replacement is None:
        raise DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
            "Replacement bulk-review campaign definition was not found.",
        )
    if replacement.status != "ACTIVE":
        raise DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_ACTIVE",
            "Replacement bulk-review campaign definition must be active.",
        )
    superseded_payload = existing.model_dump(mode="python")
    superseded_payload.update(
        {
            "status": "SUPERSEDED",
            "superseded_at": superseded_at or datetime.now(timezone.utc),
            "superseded_by": superseded_by,
            "supersession_reason": supersession_reason,
            "supersession_correlation_id": correlation_id,
            "superseded_by_campaign_id": replacement.campaign_id,
            "superseded_by_campaign_version": replacement.campaign_version,
            "superseded_by_content_hash": replacement.content_hash,
            "content_hash": "",
        }
    )
    superseded_definition = DpmBulkReviewCampaignDefinition.model_validate(superseded_payload)
    return repository.supersede_definition(definition=superseded_definition)
