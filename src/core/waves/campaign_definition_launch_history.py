from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionLaunchRecord,
)


class DpmBulkReviewCampaignDefinitionLaunchHistoryPage(BaseModel):
    """Bounded launch audit page for one persisted campaign definition."""

    product_name: Literal["BulkReviewCampaignDefinitionLaunchHistory"] = (
        "BulkReviewCampaignDefinitionLaunchHistory"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    items: list[DpmBulkReviewCampaignDefinitionLaunchRecord] = Field(
        description="Append-only durable wave launch audit records for this definition."
    )
    limit: int = Field(description="Maximum number of launch records returned.")
    offset: int = Field(description="Zero-based launch-record offset.")
    count: int = Field(description="Number of launch records returned in this page.")
    total_count: int = Field(description="Total launch records available for this definition.")
    operating_boundaries: list[str] = Field(
        default_factory=lambda: [
            "NO_MAKER_CHECKER_WORKFLOW",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_GENERATION",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        description="Unsupported downstream claims that this launch history must not imply.",
    )


def build_bulk_review_campaign_definition_launch_history_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    """Return a bounded append-only durable launch history page."""

    items = definition.launch_history[offset : offset + limit]
    return DpmBulkReviewCampaignDefinitionLaunchHistoryPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
        total_count=len(definition.launch_history),
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
