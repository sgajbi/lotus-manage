from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.waves import DpmWaveSourceRef
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)
from src.core.waves.campaign_discovery import (
    build_bulk_review_campaign_discovery_item,
    build_bulk_review_campaign_universe_posture,
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
from src.core.waves.campaign_workflow_automation import (
    build_bulk_review_campaign_workflow_automation_item,
    build_bulk_review_campaign_workflow_automation_page,
)
from src.core.waves.campaign_assignment_actions import (
    build_bulk_review_campaign_definition_assignment_action_page,
    record_bulk_review_campaign_definition_assignment_action,
)
from src.core.waves.campaign_assignment_tasks import (
    build_bulk_review_campaign_definition_assignment_task_page,
    open_bulk_review_campaign_definition_assignment_task,
    transition_bulk_review_campaign_definition_assignment_task,
)
from src.core.waves.campaign_maker_checker_controls import (
    build_bulk_review_campaign_definition_maker_checker_control_page,
    record_bulk_review_campaign_definition_maker_checker_control,
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
    assert item.universe_posture.discovery_mode == "PERSISTED_DEFINITION_ONLY"
    assert item.universe_posture.source_scope == "PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES"
    assert item.universe_posture.global_portfolio_universe_discovery == "UNSUPPORTED"
    assert item.universe_posture.global_portfolio_universe_owner_posture == (
        "DEFERRED_SOURCE_OWNER"
    )
    assert item.universe_posture.required_source_product == (
        "GlobalPortfolioUniverseCampaignCandidateSet:v1"
    )
    assert item.universe_posture.candidate_source_ref_posture == "SOURCE_BACKED"
    assert item.universe_posture.source_systems == ["lotus-core"]
    assert "candidate_portfolio_discovery" in item.universe_posture.blocked_capabilities
    assert "certified_source_owner" in item.universe_posture.promotion_requirements
    assert (
        "GlobalPortfolioUniverseCampaignCandidateSet:v1"
        in item.universe_posture.promotion_requirements
    )
    assert "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY" in item.universe_posture.operating_boundaries
    assert item.universe_posture.content_hash.startswith("sha256:")
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


def test_campaign_universe_posture_is_machine_readable_boundary() -> None:
    posture = build_bulk_review_campaign_universe_posture(definition=_definition())

    assert posture.product_name == "BulkReviewCampaignUniversePosture"
    assert posture.product_version == "v1"
    assert posture.discovery_mode == "PERSISTED_DEFINITION_ONLY"
    assert posture.source_scope == "PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES"
    assert posture.global_portfolio_universe_discovery == "UNSUPPORTED"
    assert posture.global_portfolio_universe_owner_posture == "DEFERRED_SOURCE_OWNER"
    assert posture.required_source_product == "GlobalPortfolioUniverseCampaignCandidateSet:v1"
    assert posture.candidate_source_ref_posture == "SOURCE_BACKED"
    assert posture.source_systems == ["lotus-core"]
    assert posture.blocked_capabilities == [
        "bank_wide_portfolio_universe_scan",
        "candidate_portfolio_discovery",
        "candidate_eligibility_calculation",
        "source_fact_recalculation",
        "membership_recomputation",
    ]
    assert posture.promotion_requirements == [
        "certified_source_owner",
        "GlobalPortfolioUniverseCampaignCandidateSet:v1",
        "source_product_contract",
        "producer_lineage_and_freshness_controls",
        "manage_consumer_declaration",
        "gateway_bff_realization",
        "workbench_gateway_only_realization",
    ]
    assert posture.operating_boundaries == [
        "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
        "NO_SOURCE_FACT_RECALCULATION",
        "NO_MEMBERSHIP_RECOMPUTATION",
        "NO_ORDER_GENERATION",
        "NO_OMS_EXECUTION_CLAIM",
    ]
    assert posture.content_hash.startswith("sha256:")


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
    assert "NO_MAKER_CHECKER_CONTROL_STATE_MUTATION" in ready.operating_boundaries
    assert "NO_MAKER_CHECKER_WORKFLOW" not in ready.operating_boundaries
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


def test_campaign_assignment_actions_record_append_only_posture() -> None:
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=_definition(),
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001", "pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    escalated = record_bulk_review_campaign_definition_assignment_action(
        definition=assigned,
        action_type="ESCALATED",
        action_ref="BRC-ASSIGN-2026-05-002",
        recorded_by="ops",
        action_reason="Approval evidence requires governance attention.",
        assigned_actor_ids=["governance_ops"],
        escalation_tier="GOVERNANCE",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-action-002",
    )

    assert len(escalated.assignment_actions) == 2
    assert escalated.assignment_actions[0].action_id.startswith("brc_assignment_action_")
    assert escalated.assignment_actions[0].assigned_actor_ids == ["pm_001"]
    assert "maker_checker_workflow" in escalated.assignment_actions[0].forbidden_actions
    assert escalated.content_hash.startswith("sha256:")

    page = build_bulk_review_campaign_definition_assignment_action_page(
        definition=escalated,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignDefinitionAssignmentActionPage"
    assert page.count == 2
    assert page.latest_action_type == "ESCALATED"
    assert page.current_assigned_actor_ids == ["governance_ops"]
    assert page.current_escalation_tier == "GOVERNANCE"
    assert page.current_sla_posture == "ATTENTION"


def test_campaign_assignment_actions_validate_conflicts_and_resolved_state() -> None:
    definition = _definition()
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    replay = record_bulk_review_campaign_definition_assignment_action(
        definition=assigned,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    resolved = record_bulk_review_campaign_definition_assignment_action(
        definition=assigned,
        action_type="RESOLVED",
        action_ref="BRC-ASSIGN-2026-05-002",
        recorded_by="ops",
        action_reason="Assignment completed.",
        assigned_actor_ids=[],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-002",
    )

    assert replay is assigned
    page = build_bulk_review_campaign_definition_assignment_action_page(
        definition=resolved,
        limit=50,
        offset=0,
    )
    assert page.latest_action_type == "RESOLVED"
    assert page.current_assigned_actor_ids == []
    assert page.current_escalation_tier == "NONE"

    try:
        record_bulk_review_campaign_definition_assignment_action(
            definition=assigned,
            action_type="ESCALATED",
            action_ref="BRC-ASSIGN-2026-05-001",
            recorded_by="ops",
            action_reason="Conflicting reuse.",
            assigned_actor_ids=["governance_ops"],
            escalation_tier="GOVERNANCE",
            sla_posture="ATTENTION",
            correlation_id="corr-campaign-assignment-action-conflict",
        )
    except ValueError as exc:
        assert str(exc) == "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT"
    else:  # pragma: no cover
        raise AssertionError("Expected duplicate assignment action ref conflict")


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        ({"action_ref": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_REQUIRED"),
        ({"recorded_by": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTOR_REQUIRED"),
        ({"action_reason": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REASON_REQUIRED"),
        (
            {"correlation_id": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_CORRELATION_REQUIRED",
        ),
        (
            {"assigned_actor_ids": []},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTORS_REQUIRED",
        ),
        (
            {"action_type": "RESOLVED", "assigned_actor_ids": [], "escalation_tier": "PM"},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_RESOLVED_TIER_INVALID",
        ),
    ],
)
def test_campaign_assignment_actions_validate_required_fields(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    request = {
        "definition": _definition(),
        "action_type": "ASSIGNED",
        "action_ref": "BRC-ASSIGN-2026-05-001",
        "recorded_by": "ops",
        "action_reason": "Route ready campaign to assigned PM.",
        "assigned_actor_ids": ["pm_001"],
        "escalation_tier": "PM",
        "sla_posture": "ON_TRACK",
        "correlation_id": "corr-campaign-assignment-action-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        record_bulk_review_campaign_definition_assignment_action(**request)


def test_campaign_assignment_actions_require_active_definition() -> None:
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition().model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTIVE_REQUIRED",
    ):
        record_bulk_review_campaign_definition_assignment_action(
            definition=retired,
            action_type="ASSIGNED",
            action_ref="BRC-ASSIGN-2026-05-001",
            recorded_by="ops",
            action_reason="Route ready campaign to assigned PM.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            correlation_id="corr-campaign-assignment-action-001",
        )


def test_campaign_assignment_tasks_open_transition_and_page_current_state() -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    acknowledged = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="ACKNOWLEDGED",
        transition_ref="BRC-TASK-2026-05-001:ack",
        transitioned_by="pm_001",
        transition_reason="Assigned PM acknowledged the task.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )
    escalated = transition_bulk_review_campaign_definition_assignment_task(
        definition=acknowledged,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="ESCALATED",
        transition_ref="BRC-TASK-2026-05-001:esc",
        transitioned_by="ops",
        transition_reason="Governance evidence requires operations attention.",
        assigned_actor_ids=["ops_lead"],
        escalation_tier="OPS",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-task-transition-002",
    )
    replay = transition_bulk_review_campaign_definition_assignment_task(
        definition=escalated,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="ESCALATED",
        transition_ref="BRC-TASK-2026-05-001:esc",
        transitioned_by="ops",
        transition_reason="Governance evidence requires operations attention.",
        assigned_actor_ids=["ops_lead"],
        escalation_tier="OPS",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-task-transition-002",
    )

    assert replay is escalated
    assert escalated.assignment_tasks[0].status == "ACKNOWLEDGED"
    assert escalated.assignment_tasks[0].assigned_actor_ids == ["ops_lead"]
    assert escalated.assignment_tasks[0].escalation_tier == "OPS"
    assert len(escalated.assignment_tasks[0].transitions) == 3
    assert "oms_execution" in escalated.assignment_tasks[0].forbidden_actions
    assert escalated.content_hash.startswith("sha256:")

    page = build_bulk_review_campaign_definition_assignment_task_page(
        definition=escalated,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignDefinitionAssignmentTaskPage"
    assert page.count == 1
    assert page.open_task_count == 1
    assert page.status_counts == {"ACKNOWLEDGED": 1}
    assert page.escalation_tier_counts == {"OPS": 1}
    assert page.sla_posture_counts == {"ATTENTION": 1}


def test_campaign_workflow_automation_classifies_candidates_active_tasks_and_blocks() -> None:
    candidate = build_bulk_review_campaign_workflow_automation_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )

    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    active = build_bulk_review_campaign_workflow_automation_item(
        definition=opened,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )
    blocked_definition = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="BLOCKED",
        transition_ref="BRC-TASK-2026-05-001:blocked",
        transitioned_by="pm_001",
        transition_reason="Governance evidence is incomplete.",
        sla_posture="BREACHED_OR_BLOCKED",
        correlation_id="corr-campaign-assignment-task-transition-blocked",
    )
    blocked = build_bulk_review_campaign_workflow_automation_item(
        definition=blocked_definition,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )

    assert candidate.product_name == "BulkReviewCampaignWorkflowAutomationItem"
    assert candidate.automation_status == "AUTOMATION_CANDIDATE"
    assert candidate.automation_action == "OPEN_ASSIGNMENT_TASK"
    assert candidate.proposed_task_type == "ASSIGNMENT"
    assert candidate.proposed_task_ref is not None
    assert "NO_AUTOMATIC_TASK_MUTATION" in candidate.operating_boundaries
    assert "NO_AUTOMATIC_MAKER_CHECKER_MUTATION" in candidate.operating_boundaries
    assert "NO_MAKER_CHECKER_WORKFLOW" not in candidate.operating_boundaries
    assert candidate.capability_posture.manage_assignment_task_readiness == "SUPPORTED"
    assert (
        candidate.capability_posture.manage_assignment_task_mutation == "CONTROLLED_ENDPOINT_ONLY"
    )
    assert candidate.capability_posture.external_workflow_orchestration == "UNSUPPORTED"
    assert candidate.capability_posture.external_workflow_events_projected is False
    assert candidate.capability_posture.external_workflow_owner_posture == "DEFERRED_SOURCE_OWNER"
    assert candidate.capability_posture.required_source_product == (
        "ExternalWorkflowOrchestrationRecord:v1"
    )
    assert "external_workflow_task_creation" in candidate.capability_posture.blocked_capabilities
    assert (
        "external_workflow_state_synchronization"
        in candidate.capability_posture.blocked_capabilities
    )
    assert candidate.capability_posture.promotion_requirements == [
        "certified_external_workflow_source_owner",
        "ExternalWorkflowOrchestrationRecord:v1",
        "source_product_contract",
        "producer_lineage_and_freshness_controls",
        "manage_consumer_declaration",
        "gateway_bff_realization",
        "workbench_gateway_only_realization",
        "external_workflow_audit_and_reconciliation_evidence",
    ]
    assert "NO_EXTERNAL_WORKFLOW_ORCHESTRATION" in candidate.capability_posture.operating_boundaries
    assert candidate.capability_posture.content_hash.startswith("sha256:")
    assert candidate.capability_posture.content_hash == hash_canonical_payload(
        strip_keys(
            candidate.capability_posture.model_dump(mode="json"),
            exclude={"content_hash"},
        )
    )
    assert candidate.content_hash == hash_canonical_payload(
        strip_keys(candidate.model_dump(mode="json"), exclude={"content_hash"})
    )

    assert active.automation_status == "MANUAL_REVIEW_REQUIRED"
    assert active.automation_action == "MONITOR_ACTIVE_TASK"
    assert active.active_task_refs == ["BRC-TASK-2026-05-001"]

    assert blocked.automation_status == "BLOCKED"
    assert blocked.automation_action == "ESCALATE_ASSIGNMENT_TASK"
    assert blocked.blocked_task_refs == ["BRC-TASK-2026-05-001"]

    page = build_bulk_review_campaign_workflow_automation_page(
        definitions=[_definition(), opened, blocked_definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
        include_closed=False,
        automation_status=None,
        automation_action=None,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignWorkflowAutomation"
    assert page.automation_status_counts == {
        "AUTOMATION_CANDIDATE": 1,
        "MANUAL_REVIEW_REQUIRED": 1,
        "BLOCKED": 1,
    }
    assert page.automation_action_counts == {
        "OPEN_ASSIGNMENT_TASK": 1,
        "MONITOR_ACTIVE_TASK": 1,
        "ESCALATE_ASSIGNMENT_TASK": 1,
    }
    assert page.capability_posture.external_workflow_orchestration == "UNSUPPORTED"
    assert page.capability_posture.external_workflow_events_projected is False
    assert page.capability_posture.required_source_product == (
        "ExternalWorkflowOrchestrationRecord:v1"
    )
    assert "external_workflow_escalation" in page.capability_posture.blocked_capabilities
    assert (
        "external_workflow_audit_and_reconciliation_evidence"
        in page.capability_posture.promotion_requirements
    )
    assert page.capability_posture.content_hash == candidate.capability_posture.content_hash
    assert page.content_hash == hash_canonical_payload(
        strip_keys(page.model_dump(mode="json"), exclude={"content_hash"})
    )

    empty_page = build_bulk_review_campaign_workflow_automation_page(
        definitions=[],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
        include_closed=False,
        automation_status=None,
        automation_action=None,
        limit=50,
        offset=0,
    )

    assert empty_page.items == []
    assert empty_page.capability_posture.manage_assignment_task_readiness == "SUPPORTED"
    assert empty_page.capability_posture.external_workflow_orchestration == "UNSUPPORTED"
    assert empty_page.capability_posture.external_workflow_events_projected is False
    assert empty_page.capability_posture.blocked_capabilities == (
        candidate.capability_posture.blocked_capabilities
    )
    assert empty_page.capability_posture.promotion_requirements == (
        candidate.capability_posture.promotion_requirements
    )
    assert empty_page.capability_posture.content_hash == candidate.capability_posture.content_hash


def test_campaign_workflow_automation_filters_actions_and_closed_rows() -> None:
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition().model_dump(mode="python"),
            "campaign_id": "campaign-holdings-retired-automation-20260510",
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-automation",
            "content_hash": "",
        }
    )

    closed_item = build_bulk_review_campaign_workflow_automation_item(
        definition=retired,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )
    filtered = build_bulk_review_campaign_workflow_automation_page(
        definitions=[_definition(), retired],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
        include_closed=True,
        automation_status=None,
        automation_action="NO_AUTOMATION_CLOSED",
        limit=50,
        offset=0,
    )

    assert closed_item.automation_status == "CLOSED"
    assert closed_item.automation_action == "NO_AUTOMATION_CLOSED"
    assert closed_item.proposed_task_ref is None
    assert filtered.count == 1
    assert filtered.items[0].campaign_id == "campaign-holdings-retired-automation-20260510"


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        ({"task_ref": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_REQUIRED"),
        ({"opened_by": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTOR_REQUIRED"),
        ({"task_reason": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REASON_REQUIRED"),
        ({"assigned_actor_ids": []}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED"),
        ({"correlation_id": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CORRELATION_REQUIRED"),
    ],
)
def test_campaign_assignment_tasks_validate_open_request(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    request = {
        "definition": _definition(),
        "task_ref": "BRC-TASK-2026-05-001",
        "task_type": "ASSIGNMENT",
        "opened_by": "ops",
        "task_reason": "Campaign requires PM acknowledgement.",
        "assigned_actor_ids": ["pm_001"],
        "escalation_tier": "PM",
        "sla_posture": "ON_TRACK",
        "correlation_id": "corr-campaign-assignment-task-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        open_bulk_review_campaign_definition_assignment_task(**request)


def test_campaign_assignment_tasks_reject_invalid_transitions_and_closed_mutation() -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    resolved = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="RESOLVED",
        transition_ref="BRC-TASK-2026-05-001:resolved",
        transitioned_by="pm_001",
        transition_reason="Campaign task completed.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CLOSED_TRANSITION_FORBIDDEN",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=resolved,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="STARTED",
            transition_ref="BRC-TASK-2026-05-001:start",
            transitioned_by="pm_001",
            transition_reason="Invalid closed task mutation.",
            correlation_id="corr-campaign-assignment-task-transition-002",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="missing-task",
            transition_type="ACKNOWLEDGED",
            transition_ref="missing:ack",
            transitioned_by="pm_001",
            transition_reason="Missing task.",
            correlation_id="corr-campaign-assignment-task-transition-003",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=resolved,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="CANCELLED",
            transition_ref="BRC-TASK-2026-05-001:resolved",
            transitioned_by="ops",
            transition_reason="Conflicting transition ref.",
            correlation_id="corr-campaign-assignment-task-transition-conflict",
        )


def test_campaign_assignment_tasks_replay_and_conflict_on_task_ref() -> None:
    request = {
        "definition": _definition(),
        "task_ref": "BRC-TASK-2026-05-001",
        "task_type": "ASSIGNMENT",
        "opened_by": "ops",
        "task_reason": "Campaign requires PM acknowledgement.",
        "assigned_actor_ids": ["pm_001"],
        "escalation_tier": "PM",
        "sla_posture": "ON_TRACK",
        "correlation_id": "corr-campaign-assignment-task-001",
    }
    opened = open_bulk_review_campaign_definition_assignment_task(**request)
    replay = open_bulk_review_campaign_definition_assignment_task(
        **(request | {"definition": opened})
    )

    assert replay is opened

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT",
    ):
        open_bulk_review_campaign_definition_assignment_task(
            **(
                request
                | {
                    "definition": opened,
                    "task_reason": "Conflicting duplicate task ref.",
                }
            )
        )


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        (
            {"transition_ref": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_REQUIRED",
        ),
        (
            {"transitioned_by": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_ACTOR_REQUIRED",
        ),
        (
            {"transition_reason": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REASON_REQUIRED",
        ),
        (
            {"correlation_id": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_CORRELATION_REQUIRED",
        ),
    ],
)
def test_campaign_assignment_tasks_validate_transition_required_fields(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    request = {
        "definition": opened,
        "task_ref": "BRC-TASK-2026-05-001",
        "transition_type": "ACKNOWLEDGED",
        "transition_ref": "BRC-TASK-2026-05-001:ack",
        "transitioned_by": "pm_001",
        "transition_reason": "Assigned PM acknowledged the task.",
        "correlation_id": "corr-campaign-assignment-task-transition-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        transition_bulk_review_campaign_definition_assignment_task(**request)


def test_campaign_assignment_tasks_validate_transition_edges() -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_OPENED_TRANSITION_FORBIDDEN",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="OPENED",
            transition_ref="BRC-TASK-2026-05-001:opened-duplicate",
            transitioned_by="ops",
            transition_reason="Opening is only allowed through task creation.",
            correlation_id="corr-campaign-assignment-task-transition-opened",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="REASSIGNED",
            transition_ref="BRC-TASK-2026-05-001:reassign-missing",
            transitioned_by="ops",
            transition_reason="Reassignment must name the accountable actor.",
            correlation_id="corr-campaign-assignment-task-transition-reassign-missing",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_DUE_AT_REQUIRED",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="DUE_DATE_CHANGED",
            transition_ref="BRC-TASK-2026-05-001:due-missing",
            transitioned_by="ops",
            transition_reason="Due date changes must carry the new due time.",
            correlation_id="corr-campaign-assignment-task-transition-due-missing",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_INVALID",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="UNBLOCKED",
            transition_ref="BRC-TASK-2026-05-001:unblocked-invalid",
            transitioned_by="ops",
            transition_reason="Open tasks cannot be unblocked before they are blocked.",
            correlation_id="corr-campaign-assignment-task-transition-unblocked-invalid",
        )

    due_at = datetime(2026, 5, 12, 8, tzinfo=timezone.utc)
    due_changed = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="DUE_DATE_CHANGED",
        transition_ref="BRC-TASK-2026-05-001:due",
        transitioned_by="ops",
        transition_reason="Operations set the campaign assignment due date.",
        due_at=due_at,
        correlation_id="corr-campaign-assignment-task-transition-due",
    )
    blocked = transition_bulk_review_campaign_definition_assignment_task(
        definition=due_changed,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="BLOCKED",
        transition_ref="BRC-TASK-2026-05-001:blocked",
        transitioned_by="pm_001",
        transition_reason="PM is waiting for source-owned campaign evidence.",
        sla_posture="BREACHED_OR_BLOCKED",
        correlation_id="corr-campaign-assignment-task-transition-blocked",
    )
    unblocked = transition_bulk_review_campaign_definition_assignment_task(
        definition=blocked,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="UNBLOCKED",
        transition_ref="BRC-TASK-2026-05-001:unblocked",
        transitioned_by="ops",
        transition_reason="Source-owned campaign evidence is now available.",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-transition-unblocked",
    )

    assert unblocked.assignment_tasks[0].status == "IN_PROGRESS"
    assert unblocked.assignment_tasks[0].due_at == due_at
    assert unblocked.assignment_tasks[0].sla_posture == "ON_TRACK"


def test_campaign_assignment_tasks_reject_empty_reassignment_assignees() -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="REASSIGNED",
            transition_ref="BRC-TASK-2026-05-001:reassign-empty",
            transitioned_by="ops",
            transition_reason="Reassignment must retain accountable actors.",
            assigned_actor_ids=[],
            correlation_id="corr-campaign-assignment-task-transition-reassign-empty",
        )


def test_campaign_assignment_tasks_reject_inactive_definition_for_open_and_transition() -> None:
    retired = _definition().model_copy(
        update={
            "status": "RETIRED",
            "retired_at": "2026-05-21T10:00:00+08:00",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTIVE_REQUIRED",
    ):
        open_bulk_review_campaign_definition_assignment_task(
            definition=retired,
            task_ref="BRC-TASK-2026-05-001",
            task_type="ASSIGNMENT",
            opened_by="ops",
            task_reason="Campaign requires PM acknowledgement.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            correlation_id="corr-campaign-assignment-task-001",
        )

    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    retired_with_task = opened.model_copy(
        update={
            "status": "RETIRED",
            "retired_at": "2026-05-21T10:00:00+08:00",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTIVE_REQUIRED",
    ):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=retired_with_task,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="ACKNOWLEDGED",
            transition_ref="BRC-TASK-2026-05-001:ack",
            transitioned_by="pm_001",
            transition_reason="Assigned PM acknowledged the task.",
            correlation_id="corr-campaign-assignment-task-transition-001",
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"transition_type": "STARTED"},
        {"transitioned_by": "ops"},
        {"transition_reason": "Conflicting replay reason."},
        {"correlation_id": "corr-campaign-assignment-task-transition-conflict"},
        {"assigned_actor_ids": ["pm_002"]},
        {"escalation_tier": "OPS"},
        {"sla_posture": "BREACHED_OR_BLOCKED"},
        {"due_at": datetime(2026, 5, 12, 8, tzinfo=timezone.utc)},
        {
            "source_refs": [
                DpmWaveSourceRef(
                    source_system="lotus-manage",
                    source_type="CAMPAIGN_ASSIGNMENT_TASK",
                    source_id="brc-task-conflicting-source-ref",
                )
            ]
        },
    ],
)
def test_campaign_assignment_tasks_reject_conflicting_transition_replays(
    overrides: dict[str, object],
) -> None:
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=_definition(),
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    acknowledged = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="ACKNOWLEDGED",
        transition_ref="BRC-TASK-2026-05-001:ack",
        transitioned_by="pm_001",
        transition_reason="Assigned PM acknowledged the task.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )
    request = {
        "definition": acknowledged,
        "task_ref": "BRC-TASK-2026-05-001",
        "transition_type": "ACKNOWLEDGED",
        "transition_ref": "BRC-TASK-2026-05-001:ack",
        "transitioned_by": "pm_001",
        "transition_reason": "Assigned PM acknowledged the task.",
        "correlation_id": "corr-campaign-assignment-task-transition-001",
    } | overrides

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT",
    ):
        transition_bulk_review_campaign_definition_assignment_task(**request)


def test_campaign_maker_checker_controls_record_actor_separation() -> None:
    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=_definition(),
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )
    reviewed = record_bulk_review_campaign_definition_maker_checker_control(
        definition=submitted,
        control_action="REVIEW_COMPLETED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PASSED",
        control_reason="Independent reviewer accepted the campaign definition evidence.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    replay = record_bulk_review_campaign_definition_maker_checker_control(
        definition=reviewed,
        control_action="REVIEW_COMPLETED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PASSED",
        control_reason="Independent reviewer accepted the campaign definition evidence.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )

    assert replay is reviewed
    assert len(reviewed.maker_checker_controls) == 2
    assert reviewed.maker_checker_controls[0].control_id.startswith("brc_maker_checker_control_")
    assert "oms_execution" in reviewed.maker_checker_controls[0].forbidden_actions
    assert reviewed.content_hash.startswith("sha256:")

    page = build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=reviewed,
        limit=50,
        offset=0,
    )

    assert page.product_name == "BulkReviewCampaignDefinitionMakerCheckerControlPage"
    assert page.count == 2
    assert page.latest_control_action == "REVIEW_COMPLETED"
    assert page.current_control_outcome == "PASSED"
    assert page.current_reviewer_actor_id == "cio_ops_committee"


def test_campaign_maker_checker_controls_record_reviewer_assignment_and_exceptions() -> None:
    assigned = record_bulk_review_campaign_definition_maker_checker_control(
        definition=_definition(),
        control_action="REVIEWER_ASSIGNED",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PENDING",
        control_reason="Independent reviewer assigned for campaign definition control.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )
    exception_open = record_bulk_review_campaign_definition_maker_checker_control(
        definition=assigned,
        control_action="CONTROL_EXCEPTION_RAISED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        control_outcome="EXCEPTION_OPEN",
        control_reason="Control evidence requires remediation.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    exception_resolved = record_bulk_review_campaign_definition_maker_checker_control(
        definition=exception_open,
        control_action="CONTROL_EXCEPTION_RESOLVED",
        control_ref="BRC-MC-2026-05-003",
        recorded_by="ops",
        control_outcome="EXCEPTION_RESOLVED",
        control_reason="Control evidence remediation accepted.",
        correlation_id="corr-campaign-maker-checker-control-003",
    )

    page = build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=exception_resolved,
        limit=50,
        offset=0,
    )

    assert page.count == 3
    assert page.latest_control_action == "CONTROL_EXCEPTION_RESOLVED"
    assert page.current_control_outcome == "EXCEPTION_RESOLVED"


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        (
            {"control_ref": " "},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_REQUIRED",
        ),
        (
            {"recorded_by": " "},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_ACTOR_REQUIRED",
        ),
        (
            {"control_reason": " "},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REASON_REQUIRED",
        ),
        (
            {"correlation_id": " "},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_CORRELATION_REQUIRED",
        ),
        (
            {"submitter_actor_id": None},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMITTER_REQUIRED",
        ),
        (
            {"control_outcome": "PASSED"},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMISSION_OUTCOME_INVALID",
        ),
        (
            {"control_action": "REVIEWER_ASSIGNED", "submitter_actor_id": None},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_REQUIRED",
        ),
        (
            {
                "control_action": "REVIEWER_ASSIGNED",
                "submitter_actor_id": None,
                "reviewer_actor_id": "cio_ops_committee",
                "required_reviewer_role": "CIO_OPERATIONS_REVIEWER",
                "control_outcome": "PASSED",
            },
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ASSIGNMENT_OUTCOME_INVALID",
        ),
        (
            {"control_action": "REVIEW_COMPLETED", "reviewer_actor_id": None},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTORS_REQUIRED",
        ),
        (
            {"control_action": "REVIEW_COMPLETED", "reviewer_actor_id": "pm_001"},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTOR_SEPARATION_REQUIRED",
        ),
        (
            {"control_action": "REVIEW_COMPLETED", "reviewer_actor_id": "cio_ops_committee"},
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEW_OUTCOME_INVALID",
        ),
        (
            {
                "control_action": "CONTROL_EXCEPTION_RAISED",
                "submitter_actor_id": None,
                "control_outcome": "PENDING",
            },
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_OUTCOME_INVALID",
        ),
        (
            {
                "control_action": "CONTROL_EXCEPTION_RESOLVED",
                "submitter_actor_id": None,
                "control_outcome": "PENDING",
            },
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_RESOLUTION_INVALID",
        ),
    ],
)
def test_campaign_maker_checker_controls_validate_required_fields(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    request = {
        "definition": _definition(),
        "control_action": "SUBMITTED_FOR_REVIEW",
        "control_ref": "BRC-MC-2026-05-001",
        "recorded_by": "ops",
        "submitter_actor_id": "pm_001",
        "reviewer_actor_id": None,
        "required_reviewer_role": None,
        "control_outcome": "PENDING",
        "control_reason": "Campaign definition submitted for independent review.",
        "correlation_id": "corr-campaign-maker-checker-control-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        record_bulk_review_campaign_definition_maker_checker_control(**request)


def test_campaign_maker_checker_controls_reject_conflicting_refs_and_inactive_definitions() -> None:
    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=_definition(),
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_CONFLICT",
    ):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=submitted,
            control_action="CONTROL_EXCEPTION_RAISED",
            control_ref="BRC-MC-2026-05-001",
            recorded_by="ops",
            control_outcome="EXCEPTION_OPEN",
            control_reason="Conflicting reuse.",
            correlation_id="corr-campaign-maker-checker-control-conflict",
        )

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition().model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_ACTIVE_REQUIRED",
    ):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=retired,
            control_action="SUBMITTED_FOR_REVIEW",
            control_ref="BRC-MC-2026-05-002",
            recorded_by="ops",
            submitter_actor_id="pm_001",
            control_outcome="PENDING",
            control_reason="Campaign definition submitted for independent review.",
            correlation_id="corr-campaign-maker-checker-control-002",
        )
