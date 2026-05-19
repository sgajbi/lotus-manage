from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.core.waves.campaign_definition_launch_history import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    build_bulk_review_campaign_definition_launch_history_page,
)
from src.core.waves.campaign_definition_launch_package import (
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    build_bulk_review_campaign_definition_launch_package,
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


class DpmBulkReviewCampaignDefinitionWorkflowOverview(BaseModel):
    """Operator-safe workflow overview for one bulk-review campaign definition."""

    product_name: Literal["BulkReviewCampaignDefinitionWorkflowOverview"] = (
        "BulkReviewCampaignDefinitionWorkflowOverview"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    requested_as_of_date: str = Field(examples=["2026-05-10"])
    actor_id: str | None = Field(
        default=None,
        description="Actor evaluated against optional entitlement evidence.",
    )
    discovery: DpmBulkReviewCampaignDiscoveryItem = Field(
        description="Persisted definition identity, governance, expiry, and candidate posture."
    )
    preview_readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness = Field(
        description="Fail-closed preview/create supportability for the requested date and actor."
    )
    lifecycle_events: DpmBulkReviewCampaignDefinitionLifecycleEventPage = Field(
        description="Bounded create/retire/supersede lifecycle audit projection."
    )
    launch_history: DpmBulkReviewCampaignDefinitionLaunchHistoryPage = Field(
        description="Append-only durable launch audit page."
    )
    launch_package: DpmBulkReviewCampaignDefinitionLaunchPackage | None = Field(
        default=None,
        description=(
            "Preview/create request draft and idempotency guidance. Omitted when requested by the "
            "caller or when readiness is blocked."
        ),
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: [
            "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
            "NO_SOURCE_FACT_RECALCULATION",
            "NO_MAKER_CHECKER_WORKFLOW",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_GENERATION",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        description="Unsupported downstream claims the overview must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the overview payload.")


def build_bulk_review_campaign_definition_workflow_overview(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
    launch_history_limit: int,
    launch_history_offset: int,
    include_launch_package: bool,
    correlation_id: str | None = None,
) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
    """Compose existing campaign read models into one bounded workflow overview."""

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
        limit=launch_history_limit,
        offset=launch_history_offset,
    )
    launch_package = None
    if include_launch_package and readiness.preview_create_allowed and actor_id:
        launch_package = build_bulk_review_campaign_definition_launch_package(
            definition=definition,
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignDefinitionWorkflowOverview",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "discovery": discovery.model_dump(mode="json"),
        "preview_readiness": readiness.model_dump(mode="json"),
        "lifecycle_events": lifecycle_events.model_dump(mode="json"),
        "launch_history": launch_history.model_dump(mode="json"),
        "launch_package": launch_package.model_dump(mode="json") if launch_package else None,
        "operating_boundaries": [
            "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
            "NO_SOURCE_FACT_RECALCULATION",
            "NO_MAKER_CHECKER_WORKFLOW",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_GENERATION",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignDefinitionWorkflowOverview.model_validate(payload)


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
