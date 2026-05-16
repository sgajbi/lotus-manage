from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


class DpmBulkReviewCampaignDiscoveryItem(BaseModel):
    """Bounded front-office read model for one persisted campaign definition."""

    product_name: Literal["BulkReviewCampaignDiscovery"] = "BulkReviewCampaignDiscovery"
    product_version: Literal["v1"] = "v1"
    campaign_id: str
    campaign_version: str
    display_name: str
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"]
    as_of_date: str
    eligible_portfolio_types: list[str]
    candidate_count: int
    eligible_candidate_count: int
    governance_status: Literal["APPROVED", "INCOMPLETE", "NOT_SUPPLIED"]
    expiry_state: Literal["ACTIVE", "EXPIRED", "INVALID", "NOT_SUPPLIED"]
    expires_on: str | None = None
    access_purpose: str | None = None
    source_ref_count: int
    content_hash: str
    superseded_by_campaign_id: str | None = None
    superseded_by_campaign_version: str | None = None
    superseded_by_content_hash: str | None = None
    preview_reference: dict[str, str] = Field(
        description=(
            "Bounded reference clients can use to preview or create a BULK_REVIEW_CAMPAIGN wave "
            "from the persisted definition. Manage still resolves membership only from the "
            "source-backed candidate set in that definition."
        )
    )


class DpmBulkReviewCampaignDiscoveryPage(BaseModel):
    """Bounded page of persisted campaign-definition discovery records."""

    items: list[DpmBulkReviewCampaignDiscoveryItem]
    limit: int
    offset: int
    count: int


def build_bulk_review_campaign_discovery_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    active_on: date | None,
) -> DpmBulkReviewCampaignDiscoveryItem:
    eligible_types = {
        portfolio_type.strip()
        for portfolio_type in definition.eligible_portfolio_types
        if portfolio_type.strip()
    }
    governance = definition.governance
    governance_status: Literal["APPROVED", "INCOMPLETE", "NOT_SUPPLIED"] = "NOT_SUPPLIED"
    expiry_state: Literal["ACTIVE", "EXPIRED", "INVALID", "NOT_SUPPLIED"] = "NOT_SUPPLIED"
    expires_on: str | None = None
    access_purpose: str | None = None
    source_ref_count = len(definition.source_refs)
    if governance is not None:
        approval_values = [
            governance.approval_ref,
            governance.approved_by,
            governance.approved_at,
        ]
        governance_status = (
            "APPROVED"
            if all(approval_values)
            else "INCOMPLETE"
            if any(approval_values)
            else "NOT_SUPPLIED"
        )
        expires_on = governance.expires_on
        access_purpose = governance.access_purpose
        source_ref_count += len(governance.source_refs)
        expiry_state = classify_bulk_review_campaign_expiry(
            expires_on=governance.expires_on,
            active_on=active_on,
        )
    return DpmBulkReviewCampaignDiscoveryItem(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        display_name=definition.display_name,
        campaign_status=definition.status,
        as_of_date=definition.as_of_date,
        eligible_portfolio_types=definition.eligible_portfolio_types,
        candidate_count=len(definition.candidates),
        eligible_candidate_count=sum(
            1 for candidate in definition.candidates if candidate.portfolio_type in eligible_types
        ),
        governance_status=governance_status,
        expiry_state=expiry_state,
        expires_on=expires_on,
        access_purpose=access_purpose,
        source_ref_count=source_ref_count,
        content_hash=definition.content_hash,
        superseded_by_campaign_id=definition.superseded_by_campaign_id,
        superseded_by_campaign_version=definition.superseded_by_campaign_version,
        superseded_by_content_hash=definition.superseded_by_content_hash,
        preview_reference={
            "trigger_type": "BULK_REVIEW_CAMPAIGN",
            "campaign_definition_id": definition.campaign_id,
            "campaign_definition_version": definition.campaign_version,
            "as_of_date": definition.as_of_date,
        },
    )


def classify_bulk_review_campaign_expiry(
    *,
    expires_on: str | None,
    active_on: date | None,
) -> Literal["ACTIVE", "EXPIRED", "INVALID", "NOT_SUPPLIED"]:
    if not expires_on:
        return "NOT_SUPPLIED"
    try:
        expiry_date = date.fromisoformat(expires_on)
    except ValueError:
        return "INVALID"
    if active_on is None:
        return "ACTIVE"
    return "EXPIRED" if expiry_date < active_on else "ACTIVE"
