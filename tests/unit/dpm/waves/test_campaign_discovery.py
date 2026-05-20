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
from src.core.waves.campaign_approval_inbox import (
    build_bulk_review_campaign_approval_inbox_item,
    build_bulk_review_campaign_approval_inbox_page,
)
from src.core.waves.campaign_workflow_board import (
    build_bulk_review_campaign_workflow_board_item,
    build_bulk_review_campaign_workflow_board_page,
)
from src.core.waves.campaign_assignment_plan import (
    build_bulk_review_campaign_assignment_plan_item,
    build_bulk_review_campaign_assignment_plan_page,
)


def _definition(
    *,
    expires_on: str | None = "2026-06-30",
    approval_ref: str | None = "BRC-APPROVAL-2026-05",
    approved_by: str | None = "cio_ops_committee",
    approved_at: str | None = "2026-05-14T08:30:00+08:00",
    entitled_actor_ids: list[str] | None = None,
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
            entitled_actor_ids=entitled_actor_ids or [],
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


def test_campaign_approval_inbox_classifies_governance_attention() -> None:
    complete = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    missing_approval = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(approval_ref=None, approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    incomplete = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    expired = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(expires_on="2026-05-01"),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    unauthorized = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(entitled_actor_ids=["ops"]),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert complete.product_name == "BulkReviewCampaignApprovalInboxItem"
    assert complete.inbox_status == "APPROVAL_COMPLETE"
    assert complete.approval_ref == "BRC-APPROVAL-2026-05"
    assert complete.approval_source_ref_count == 1
    assert complete.content_hash.startswith("sha256:")
    assert missing_approval.inbox_status == "APPROVAL_REQUIRED"
    assert incomplete.inbox_status == "APPROVAL_INCOMPLETE"
    assert expired.inbox_status == "EXPIRY_ATTENTION"
    assert unauthorized.inbox_status == "ENTITLEMENT_ATTENTION"
    assert "NO_APPROVAL_STATE_MUTATION" in unauthorized.operating_boundaries


def test_campaign_approval_inbox_page_filters_closed_and_status() -> None:
    page = build_bulk_review_campaign_approval_inbox_page(
        definitions=[
            _definition(),
            _definition(approval_ref=None, approved_by=None, approved_at=None),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_closed=False,
        inbox_status="APPROVAL_REQUIRED",
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignApprovalInbox"
    assert page.count == 1
    assert page.status_counts == {"APPROVAL_REQUIRED": 1}
    assert page.items[0].inbox_reason_codes == [
        "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"
    ]
    assert page.content_hash.startswith("sha256:")


def test_campaign_workflow_board_derives_actor_next_actions() -> None:
    ready = build_bulk_review_campaign_workflow_board_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    approval_required = build_bulk_review_campaign_workflow_board_item(
        definition=_definition(approval_ref=None, approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    unauthorized = build_bulk_review_campaign_workflow_board_item(
        definition=_definition(entitled_actor_ids=["ops"]),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert ready.product_name == "BulkReviewCampaignWorkflowBoardItem"
    assert ready.board_status == "READY_FOR_ACTOR"
    assert ready.next_action == "LAUNCH_CAMPAIGN"
    assert ready.assigned_actor_ids == ["pm_001"]
    assert ready.operating_queue.queue_status == "READY_TO_LAUNCH"
    assert ready.approval_inbox.inbox_status == "APPROVAL_COMPLETE"
    assert "NO_MAKER_CHECKER_WORKFLOW" in ready.operating_boundaries
    assert ready.content_hash.startswith("sha256:")

    assert approval_required.board_status == "ATTENTION_FOR_ACTOR"
    assert approval_required.next_action == "RECORD_APPROVAL_DECISION"
    assert approval_required.board_reason_codes == [
        "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"
    ]

    assert unauthorized.board_status == "ATTENTION_FOR_ACTOR"
    assert unauthorized.next_action == "REVIEW_ACTOR_ENTITLEMENT"
    assert unauthorized.assigned_actor_ids == ["ops"]


def test_campaign_workflow_board_page_filters_next_action_and_counts() -> None:
    page = build_bulk_review_campaign_workflow_board_page(
        definitions=[
            _definition(),
            _definition(approval_ref=None, approved_by=None, approved_at=None),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_closed=False,
        board_status=None,
        next_action="RECORD_APPROVAL_DECISION",
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignWorkflowBoard"
    assert page.count == 1
    assert page.status_counts == {"ATTENTION_FOR_ACTOR": 1}
    assert page.next_action_counts == {"RECORD_APPROVAL_DECISION": 1}
    assert page.items[0].next_action == "RECORD_APPROVAL_DECISION"
    assert page.content_hash.startswith("sha256:")


def test_campaign_assignment_plan_derives_escalation_tiers() -> None:
    ready = build_bulk_review_campaign_assignment_plan_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    approval_required = build_bulk_review_campaign_assignment_plan_item(
        definition=_definition(approval_ref=None, approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    unauthorized = build_bulk_review_campaign_assignment_plan_item(
        definition=_definition(entitled_actor_ids=["ops"]),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert ready.product_name == "BulkReviewCampaignAssignmentPlanItem"
    assert ready.escalation_tier == "PM"
    assert ready.sla_posture == "ON_TRACK"
    assert ready.escalation_reason_codes == ["CAMPAIGN_READY_FOR_ASSIGNED_ACTOR"]
    assert ready.workflow_board.next_action == "LAUNCH_CAMPAIGN"
    assert "NO_ASSIGNMENT_STATE_MUTATION" in ready.operating_boundaries
    assert ready.content_hash.startswith("sha256:")

    assert approval_required.escalation_tier == "GOVERNANCE"
    assert approval_required.sla_posture == "ATTENTION"
    assert approval_required.escalation_reason_codes == [
        "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"
    ]

    assert unauthorized.escalation_tier == "OPS"
    assert unauthorized.sla_posture == "BREACHED_OR_BLOCKED"
    assert unauthorized.assigned_actor_ids == ["ops"]


def test_campaign_assignment_plan_page_filters_tier_and_counts() -> None:
    page = build_bulk_review_campaign_assignment_plan_page(
        definitions=[
            _definition(),
            _definition(approval_ref=None, approved_by=None, approved_at=None),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_closed=False,
        escalation_tier="GOVERNANCE",
        next_action=None,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignAssignmentPlan"
    assert page.count == 1
    assert page.escalation_tier_counts == {"GOVERNANCE": 1}
    assert page.sla_posture_counts == {"ATTENTION": 1}
    assert page.items[0].next_action == "RECORD_APPROVAL_DECISION"
    assert page.content_hash.startswith("sha256:")
