from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_events import (
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.core.waves.campaign_definition_launch_history import (
    build_bulk_review_campaign_definition_launch_history_page,
)
from src.core.waves.campaign_definition_readiness import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    build_bulk_review_campaign_definition_preview_readiness,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_discovery import (
    DpmBulkReviewCampaignDiscoveryItem,
    build_bulk_review_campaign_discovery_item,
)
from src.core.waves.campaign_operating_boundaries import (
    CAMPAIGN_OPERATING_QUEUE_BOUNDARIES,
)


class DpmBulkReviewCampaignOperatingQueueItem(BaseModel):
    """Operator queue row for one persisted bulk-review campaign definition."""

    product_name: Literal["BulkReviewCampaignOperatingQueueItem"] = (
        "BulkReviewCampaignOperatingQueueItem"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    requested_as_of_date: str = Field(examples=["2026-05-10"])
    actor_id: str | None = Field(
        default=None,
        description="Actor evaluated against optional entitlement evidence.",
    )
    queue_status: Literal["READY_TO_LAUNCH", "ATTENTION_REQUIRED", "CLOSED"] = Field(
        description="Manage-owned operating posture for the persisted campaign definition."
    )
    queue_reason_codes: list[str] = Field(
        description="Bounded reason codes explaining why the definition sits in this queue state."
    )
    discovery: DpmBulkReviewCampaignDiscoveryItem = Field(
        description="Persisted definition identity, governance, expiry, and candidate posture."
    )
    preview_readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness = Field(
        description="Fail-closed preview/create supportability for the requested date and actor."
    )
    lifecycle_event_count: int = Field(
        description="Count of projected create, launch, retire, and supersede lifecycle events."
    )
    launch_history_count: int = Field(
        description="Count of durable waves launched from this campaign definition."
    )
    latest_launch_wave_id: str | None = Field(
        default=None,
        description="Most recent launched wave id, when launch history exists.",
    )
    latest_launched_at: str | None = Field(
        default=None,
        description="Most recent launch timestamp, when launch history exists.",
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(CAMPAIGN_OPERATING_QUEUE_BOUNDARIES),
        description="Unsupported downstream claims the operating queue must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the queue item payload.")


class DpmBulkReviewCampaignOperatingQueuePage(BaseModel):
    """Bounded operating queue page over persisted campaign definitions."""

    product_name: Literal["BulkReviewCampaignOperatingQueue"] = "BulkReviewCampaignOperatingQueue"
    product_version: Literal["v1"] = "v1"
    items: list[DpmBulkReviewCampaignOperatingQueueItem]
    limit: int
    offset: int
    count: int
    status_counts: dict[str, int] = Field(
        description="Queue item counts by operating posture for the returned page."
    )
    content_hash: str = Field(description="Canonical hash over the queue page payload.")


def build_bulk_review_campaign_operating_queue_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
) -> DpmBulkReviewCampaignOperatingQueueItem:
    """Compose existing campaign projections into one operator queue row."""

    discovery = build_bulk_review_campaign_discovery_item(
        definition=definition,
        active_on=active_on,
    )
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )
    lifecycle_events = build_bulk_review_campaign_definition_lifecycle_events(
        definition=definition,
    )
    launch_history = build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=1,
        offset=0,
    )
    queue_status, reason_codes = _classify_queue_posture(
        definition=definition,
        readiness=readiness,
        discovery=discovery,
    )
    latest_launch = launch_history.items[0] if launch_history.items else None
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignOperatingQueueItem",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "display_name": definition.display_name,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "queue_status": queue_status,
        "queue_reason_codes": reason_codes,
        "discovery": discovery.model_dump(mode="json"),
        "preview_readiness": readiness.model_dump(mode="json"),
        "lifecycle_event_count": lifecycle_events.count,
        "launch_history_count": len(definition.launch_history),
        "latest_launch_wave_id": latest_launch.wave_id if latest_launch else None,
        "latest_launched_at": latest_launch.launched_at.isoformat() if latest_launch else None,
        "operating_boundaries": list(CAMPAIGN_OPERATING_QUEUE_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignOperatingQueueItem.model_validate(payload)


def build_bulk_review_campaign_operating_queue_page(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
    include_expired: bool,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignOperatingQueuePage:
    items = [
        build_bulk_review_campaign_operating_queue_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]
    if active_on is not None and not include_expired:
        items = [item for item in items if item.discovery.expiry_state != "EXPIRED"]
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.queue_status] = status_counts.get(item.queue_status, 0) + 1

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignOperatingQueue",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "status_counts": status_counts,
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignOperatingQueuePage.model_validate(payload)


def _classify_queue_posture(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness,
    discovery: DpmBulkReviewCampaignDiscoveryItem,
) -> tuple[Literal["READY_TO_LAUNCH", "ATTENTION_REQUIRED", "CLOSED"], list[str]]:
    if definition.status in {"RETIRED", "SUPERSEDED"}:
        return "CLOSED", [f"CAMPAIGN_DEFINITION_{definition.status}"]
    if readiness.preview_create_allowed:
        return "READY_TO_LAUNCH", ["CAMPAIGN_DEFINITION_READY_TO_LAUNCH"]

    reasons = list(readiness.reason_codes)
    if discovery.expiry_state == "EXPIRED" and "CAMPAIGN_DEFINITION_EXPIRED" not in reasons:
        reasons.append("CAMPAIGN_DEFINITION_EXPIRED")
    if discovery.expiry_state == "INVALID" and "CAMPAIGN_DEFINITION_EXPIRY_INVALID" not in reasons:
        reasons.append("CAMPAIGN_DEFINITION_EXPIRY_INVALID")
    if not reasons:
        reasons.append("CAMPAIGN_DEFINITION_REVIEW_REQUIRED")
    return "ATTENTION_REQUIRED", reasons


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
