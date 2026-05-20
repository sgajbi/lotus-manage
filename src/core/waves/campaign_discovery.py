from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


class DpmBulkReviewCampaignUniversePosture(BaseModel):
    """Machine-readable boundary for campaign candidate-universe support."""

    product_name: Literal["BulkReviewCampaignUniversePosture"] = "BulkReviewCampaignUniversePosture"
    product_version: Literal["v1"] = "v1"
    source_scope: Literal["PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES"] = Field(
        default="PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES",
        description=(
            "The only supported candidate universe for this row: source-backed portfolios already "
            "persisted on the Manage-owned campaign definition."
        ),
    )
    global_portfolio_universe_discovery: Literal["UNSUPPORTED"] = Field(
        default="UNSUPPORTED",
        description=(
            "Manage does not scan the bank-wide portfolio universe or discover new candidate "
            "portfolios for bulk-review campaigns."
        ),
    )
    candidate_source_ref_posture: Literal["SOURCE_BACKED", "NO_CANDIDATES"] = Field(
        description=(
            "Whether the persisted candidate set carries source refs. Campaign definitions reject "
            "unsourced candidates, so populated rows are source-backed."
        )
    )
    source_systems: list[str] = Field(
        description="Sorted source systems represented by persisted candidate source refs.",
        examples=[["lotus-core", "lotus-risk"]],
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: [
            "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
            "NO_SOURCE_FACT_RECALCULATION",
            "NO_MEMBERSHIP_RECOMPUTATION",
            "NO_ORDER_GENERATION",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        description=(
            "Explicit non-claims for the campaign discovery universe posture. These boundaries are "
            "part of the API contract, not free-text guidance."
        ),
    )


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
    universe_posture: DpmBulkReviewCampaignUniversePosture
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
        universe_posture=build_bulk_review_campaign_universe_posture(definition=definition),
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


def build_bulk_review_campaign_universe_posture(
    *,
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmBulkReviewCampaignUniversePosture:
    source_systems = sorted(
        {
            source_ref.source_system
            for candidate in definition.candidates
            for source_ref in candidate.source_refs
            if source_ref.source_system.strip()
        }
    )
    return DpmBulkReviewCampaignUniversePosture(
        candidate_source_ref_posture="SOURCE_BACKED" if source_systems else "NO_CANDIDATES",
        source_systems=source_systems,
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
