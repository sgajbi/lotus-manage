from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionLaunchRecord,
)


class DpmBulkReviewCampaignDefinitionLifecycleEvent(BaseModel):
    """Auditable lifecycle event projected from one campaign definition record."""

    product_name: Literal["BulkReviewCampaignDefinitionLifecycleEvent"] = (
        "BulkReviewCampaignDefinitionLifecycleEvent"
    )
    product_version: Literal["v1"] = "v1"
    event_type: Literal["CREATED", "LAUNCHED", "RETIRED", "SUPERSEDED"] = Field(
        description="Campaign-definition lifecycle event type.",
        examples=["CREATED"],
    )
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    occurred_at: str = Field(
        description="Event timestamp in ISO-8601 format.",
        examples=["2026-05-16T08:30:00+00:00"],
    )
    actor_id: str = Field(description="Actor recorded for the lifecycle event.", examples=["ops"])
    reason: str | None = Field(
        default=None,
        description="Business reason recorded for the lifecycle event when supplied.",
    )
    correlation_id: str = Field(
        description="Correlation id recorded for the lifecycle event.",
        examples=["corr-campaign-definition-001"],
    )
    status_after: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] = Field(
        description="Campaign-definition status after the lifecycle event.",
        examples=["ACTIVE"],
    )
    content_hash: str = Field(
        description="Content hash for the campaign definition after the lifecycle event."
    )
    replacement_campaign_id: str | None = Field(
        default=None,
        description="Replacement campaign id for supersession events.",
    )
    replacement_campaign_version: str | None = Field(
        default=None,
        description="Replacement campaign version for supersession events.",
    )
    replacement_content_hash: str | None = Field(
        default=None,
        description="Replacement definition content hash for supersession events.",
    )
    wave_id: str | None = Field(
        default=None,
        description="Durable wave id for launch events.",
    )
    requested_as_of_date: str | None = Field(
        default=None,
        description="Requested as-of date used for launch events.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Deterministic durable-create idempotency key for launch events.",
    )


class DpmBulkReviewCampaignDefinitionLifecycleEventPage(BaseModel):
    """Bounded lifecycle event page for one campaign definition."""

    items: list[DpmBulkReviewCampaignDefinitionLifecycleEvent]
    count: int


def build_bulk_review_campaign_definition_lifecycle_events(
    *,
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    events = [
        build_bulk_review_campaign_definition_created_event(definition=definition),
        *[
            build_bulk_review_campaign_definition_launch_event(
                definition=definition,
                launch=launch,
            )
            for launch in definition.launch_history
        ],
    ]
    retired_event = build_bulk_review_campaign_definition_retired_event(definition=definition)
    if retired_event is not None:
        events.append(retired_event)
    superseded_event = build_bulk_review_campaign_definition_superseded_event(definition=definition)
    if superseded_event is not None:
        events.append(superseded_event)
    return DpmBulkReviewCampaignDefinitionLifecycleEventPage(
        items=events,
        count=len(events),
    )


def build_bulk_review_campaign_definition_created_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmBulkReviewCampaignDefinitionLifecycleEvent:
    return DpmBulkReviewCampaignDefinitionLifecycleEvent(
        event_type="CREATED",
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        occurred_at=definition.created_at.isoformat(),
        actor_id=definition.created_by,
        reason=definition.rationale,
        correlation_id=definition.correlation_id,
        status_after="ACTIVE",
        content_hash=definition.content_hash,
    )


def build_bulk_review_campaign_definition_launch_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    launch: DpmBulkReviewCampaignDefinitionLaunchRecord,
) -> DpmBulkReviewCampaignDefinitionLifecycleEvent:
    return DpmBulkReviewCampaignDefinitionLifecycleEvent(
        event_type="LAUNCHED",
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        occurred_at=launch.launched_at.isoformat(),
        actor_id=launch.launched_by,
        reason="Durable bulk-review campaign wave launched.",
        correlation_id=launch.correlation_id,
        status_after=definition.status,
        content_hash=definition.content_hash,
        wave_id=launch.wave_id,
        requested_as_of_date=launch.requested_as_of_date,
        idempotency_key=launch.idempotency_key,
    )


def build_bulk_review_campaign_definition_retired_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmBulkReviewCampaignDefinitionLifecycleEvent | None:
    if definition.status != "RETIRED":
        return None
    return DpmBulkReviewCampaignDefinitionLifecycleEvent(
        event_type="RETIRED",
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        occurred_at=definition.retired_at.isoformat() if definition.retired_at else "",
        actor_id=definition.retired_by or "",
        reason=definition.retirement_reason,
        correlation_id=definition.retirement_correlation_id or "",
        status_after="RETIRED",
        content_hash=definition.content_hash,
    )


def build_bulk_review_campaign_definition_superseded_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmBulkReviewCampaignDefinitionLifecycleEvent | None:
    if definition.status != "SUPERSEDED":
        return None
    return DpmBulkReviewCampaignDefinitionLifecycleEvent(
        event_type="SUPERSEDED",
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        occurred_at=definition.superseded_at.isoformat() if definition.superseded_at else "",
        actor_id=definition.superseded_by or "",
        reason=definition.supersession_reason,
        correlation_id=definition.supersession_correlation_id or "",
        status_after="SUPERSEDED",
        content_hash=definition.content_hash,
        replacement_campaign_id=definition.superseded_by_campaign_id,
        replacement_campaign_version=definition.superseded_by_campaign_version,
        replacement_content_hash=definition.superseded_by_content_hash,
    )
