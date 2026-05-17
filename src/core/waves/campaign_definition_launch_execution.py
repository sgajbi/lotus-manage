from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_launch_package import (
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionWaveRequestDraft,
    build_bulk_review_campaign_definition_launch_package,
)
from src.core.waves.campaign_definition_readiness import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


class DpmBulkReviewCampaignDefinitionLaunchBlocked(ValueError):
    def __init__(
        self,
        *,
        reason_codes: list[str],
        readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness,
    ) -> None:
        super().__init__("BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED")
        self.reason_codes = reason_codes
        self.readiness = readiness


class DpmBulkReviewCampaignDefinitionLaunchCommand(BaseModel):
    """Ready-only durable launch command derived from a persisted campaign definition."""

    launch_package: DpmBulkReviewCampaignDefinitionLaunchPackage = Field(
        description="Readiness package and idempotency/correlation headers used for launch."
    )
    create_request: DpmBulkReviewCampaignDefinitionWaveRequestDraft = Field(
        description="Bounded durable-wave create request draft."
    )
    idempotency_key: str = Field(description="Deterministic durable launch idempotency key.")
    correlation_id: str = Field(description="Correlation id carried into the durable wave.")


def build_bulk_review_campaign_definition_launch_command(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str,
    correlation_id: str | None,
) -> DpmBulkReviewCampaignDefinitionLaunchCommand:
    launch_package = build_bulk_review_campaign_definition_launch_package(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
    )
    if (
        launch_package.launch_state != "READY"
        or not launch_package.readiness.preview_create_allowed
    ):
        raise DpmBulkReviewCampaignDefinitionLaunchBlocked(
            reason_codes=launch_package.reason_codes,
            readiness=launch_package.readiness,
        )
    return DpmBulkReviewCampaignDefinitionLaunchCommand(
        launch_package=launch_package,
        create_request=launch_package.create_request,
        idempotency_key=launch_package.create_headers["Idempotency-Key"],
        correlation_id=launch_package.correlation_id,
    )
