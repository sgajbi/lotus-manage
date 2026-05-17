from __future__ import annotations

from datetime import datetime, timezone

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionLaunchRecord,
)


def record_bulk_review_campaign_definition_launch(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    wave_id: str,
    launched_by: str,
    requested_as_of_date: str,
    correlation_id: str,
    idempotency_key: str,
    launched_at: datetime | None = None,
) -> DpmBulkReviewCampaignDefinition:
    """Return a definition with one append-only durable launch audit record."""

    for launch in definition.launch_history:
        if launch.idempotency_key == idempotency_key:
            return definition

    return DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "launch_history": [
                *[launch.model_dump(mode="python") for launch in definition.launch_history],
                DpmBulkReviewCampaignDefinitionLaunchRecord(
                    wave_id=wave_id,
                    launched_at=launched_at or datetime.now(timezone.utc),
                    launched_by=launched_by,
                    requested_as_of_date=requested_as_of_date,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                ).model_dump(mode="python"),
            ],
            "content_hash": "",
        }
    )
