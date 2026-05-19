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
from src.core.waves.campaign_definition_workflow_overview import (
    build_bulk_review_campaign_definition_workflow_overview,
)
from src.core.waves.campaign_operating_queue import (
    build_bulk_review_campaign_operating_queue_item,
    build_bulk_review_campaign_operating_queue_page,
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


def test_campaign_workflow_overview_composes_bounded_operating_posture() -> None:
    overview = build_bulk_review_campaign_definition_workflow_overview(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id=None,
        active_on=date(2026, 5, 16),
        launch_history_limit=20,
        launch_history_offset=0,
        include_launch_package=True,
    )

    assert overview.product_name == "BulkReviewCampaignDefinitionWorkflowOverview"
    assert overview.discovery.governance_status == "APPROVED"
    assert overview.preview_readiness.preview_create_allowed is True
    assert overview.lifecycle_events.count == 1
    assert overview.launch_history.count == 0
    assert overview.launch_package is None
    assert overview.content_hash.startswith("sha256:")
    assert "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY" in overview.operating_boundaries


def test_campaign_workflow_overview_includes_launch_package_when_ready_for_actor() -> None:
    overview = build_bulk_review_campaign_definition_workflow_overview(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        launch_history_limit=20,
        launch_history_offset=0,
        include_launch_package=True,
        correlation_id="corr-workflow-overview",
    )

    assert overview.preview_readiness.preview_create_allowed is True
    assert overview.launch_package is not None
    assert overview.launch_package.correlation_id == "corr-workflow-overview"
    assert overview.launch_package.create_request.trigger_type == "BULK_REVIEW_CAMPAIGN"


def test_campaign_operating_queue_classifies_ready_and_attention_rows() -> None:
    ready_item = build_bulk_review_campaign_operating_queue_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    attention_item = build_bulk_review_campaign_operating_queue_item(
        definition=_definition(expires_on="2026-05-01"),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert ready_item.product_name == "BulkReviewCampaignOperatingQueueItem"
    assert ready_item.queue_status == "READY_TO_LAUNCH"
    assert ready_item.queue_reason_codes == ["CAMPAIGN_DEFINITION_READY_TO_LAUNCH"]
    assert ready_item.lifecycle_event_count == 1
    assert ready_item.launch_history_count == 0
    assert ready_item.content_hash.startswith("sha256:")

    assert attention_item.queue_status == "ATTENTION_REQUIRED"
    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in attention_item.queue_reason_codes
    assert "NO_OMS_EXECUTION_CLAIM" in attention_item.operating_boundaries


def test_campaign_operating_queue_page_filters_expired_rows_and_counts_statuses() -> None:
    page = build_bulk_review_campaign_operating_queue_page(
        definitions=[
            _definition(),
            _definition(expires_on="2026-05-01"),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_expired=False,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignOperatingQueue"
    assert page.count == 1
    assert page.status_counts == {"READY_TO_LAUNCH": 1}
    assert page.items[0].discovery.expiry_state == "ACTIVE"
    assert page.content_hash.startswith("sha256:")
