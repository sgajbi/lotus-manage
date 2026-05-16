from __future__ import annotations

from datetime import date

from src.core.waves import DpmWaveSourceRef
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)
from src.core.waves.campaign_discovery import (
    build_bulk_review_campaign_discovery_item,
    classify_bulk_review_campaign_expiry,
)


def _definition(
    *,
    expires_on: str | None = "2026-06-30",
    approval_ref: str | None = "BRC-APPROVAL-2026-05",
    approved_by: str | None = "cio_ops_committee",
    approved_at: str | None = "2026-05-14T08:30:00+08:00",
) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        campaign_id="campaign-holdings-apple-tesla-20260510",
        campaign_version="2026.05",
        display_name="Apple and Tesla holdings review",
        as_of_date="2026-05-10",
        rationale="Review source-backed discretionary portfolios affected by the campaign.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="HoldingsAsOf",
                        source_id="holdings-asof-pb-sg-global-bal-001",
                    )
                ],
            ),
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_ADVISORY_001",
                portfolio_type="ADVISORY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="PortfolioProfile",
                        source_id="portfolio-profile-pb-sg-advisory-001",
                    )
                ],
            ),
        ],
        governance=DpmBulkReviewCampaignDefinitionGovernance(
            approval_ref=approval_ref,
            approved_by=approved_by,
            approved_at=approved_at,
            expires_on=expires_on,
            source_refs=[
                DpmWaveSourceRef(
                    source_system="lotus-manage",
                    source_type="CAMPAIGN_APPROVAL",
                    source_id="brc-approval-2026-05",
                )
            ],
        ),
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="CAMPAIGN_SOURCE_FILE",
                source_id="campaign-source-20260510",
            )
        ],
        created_by="ops",
        correlation_id="corr-campaign-definition-001",
    )


def test_campaign_discovery_item_projects_governance_and_candidate_posture() -> None:
    item = build_bulk_review_campaign_discovery_item(
        definition=_definition(),
        active_on=date(2026, 5, 16),
    )

    assert item.product_name == "BulkReviewCampaignDiscovery"
    assert item.campaign_status == "ACTIVE"
    assert item.governance_status == "APPROVED"
    assert item.expiry_state == "ACTIVE"
    assert item.candidate_count == 2
    assert item.eligible_candidate_count == 1
    assert item.source_ref_count == 2
    assert item.preview_reference == {
        "trigger_type": "BULK_REVIEW_CAMPAIGN",
        "campaign_definition_id": "campaign-holdings-apple-tesla-20260510",
        "campaign_definition_version": "2026.05",
        "as_of_date": "2026-05-10",
    }


def test_campaign_discovery_item_marks_incomplete_and_invalid_governance() -> None:
    item = build_bulk_review_campaign_discovery_item(
        definition=_definition(
            expires_on="not-a-date",
            approval_ref="BRC-APPROVAL-2026-05",
            approved_by=None,
            approved_at=None,
        ),
        active_on=date(2026, 5, 16),
    )

    assert item.governance_status == "INCOMPLETE"
    assert item.expiry_state == "INVALID"


def test_campaign_expiry_classifier_is_bounded_and_date_driven() -> None:
    assert classify_bulk_review_campaign_expiry(expires_on=None, active_on=None) == "NOT_SUPPLIED"
    assert classify_bulk_review_campaign_expiry(expires_on="bad-date", active_on=None) == "INVALID"
    assert (
        classify_bulk_review_campaign_expiry(
            expires_on="2026-05-15",
            active_on=date(2026, 5, 16),
        )
        == "EXPIRED"
    )
