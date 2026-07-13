from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import src.core.waves.campaign_approval_inbox as approval_inbox_module
import src.core.waves.campaign_workflow_board as workflow_board_module
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
from src.core.waves.campaign_definition_readiness import (
    build_bulk_review_campaign_definition_preview_readiness,
)
from src.core.waves.campaign_operating_queue import (
    DpmBulkReviewCampaignOperatingQueuePage,
    _attention_queue_reason_codes,
    _classify_queue_posture,
    _closed_queue_posture,
    build_bulk_review_campaign_operating_queue_item,
    build_bulk_review_campaign_operating_queue_page,
)
from src.core.waves.campaign_approval_inbox import (
    DpmBulkReviewCampaignApprovalInboxPage,
    build_bulk_review_campaign_approval_inbox_item,
    build_bulk_review_campaign_approval_inbox_page,
)
from src.core.waves.campaign_workflow_board import (
    DpmBulkReviewCampaignWorkflowBoardPage,
    _filtered_workflow_board_items,
    _workflow_board_counts,
    _workflow_board_page_payload,
    build_bulk_review_campaign_workflow_board_item,
    build_bulk_review_campaign_workflow_board_page,
)
from src.core.waves.campaign_assignment_plan import (
    DpmBulkReviewCampaignAssignmentPlanPage,
    _assignment_plan_counts,
    _assignment_plan_page_payload,
    _filtered_assignment_plan_items,
    build_bulk_review_campaign_assignment_plan_item,
    build_bulk_review_campaign_assignment_plan_page,
)
from src.core.waves.campaign_workflow_automation import (
    DpmBulkReviewCampaignWorkflowAutomationPage,
    _filtered_workflow_automation_items,
    _workflow_automation_counts,
    _workflow_automation_page_payload,
    build_bulk_review_campaign_workflow_automation_item,
    build_bulk_review_campaign_workflow_automation_page,
)
from src.core.waves.campaign_assignment_actions import (
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    _assignment_action_page_state,
    _assignment_action_replay_result,
    _assignment_action_request,
    _sorted_assignment_actions,
    build_bulk_review_campaign_definition_assignment_action_page,
    record_bulk_review_campaign_definition_assignment_action,
)
from src.core.waves.campaign_assignment_tasks import (
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    _assignment_task_for_ref,
    _assignment_task_index,
    _assignment_task_page_slice,
    _assignment_task_transition,
    _assignment_tasks_sorted_latest,
    _definition_with_appended_assignment_task,
    _definition_with_replaced_assignment_task,
    _filtered_assignment_tasks,
    _open_task_request_fields,
    _open_assignment_task_count,
    _optional_transition_replay_fields_match,
    _replayed_open_task_definition,
    _replayed_transition_definition,
    _required_transition_replay_fields,
    _source_ref_payloads,
    _transition_assignees_replay_match,
    _transition_due_at_replay_match,
    _transition_escalation_tier_replay_match,
    _transition_next_assignees,
    _transition_requires_actor_ids,
    _transition_requires_due_at,
    _transition_requires_open_assignees,
    _transition_request_fields,
    _transition_sla_posture_replay_match,
    _transition_task_fields,
    _validate_transition_field_requirements,
    _validate_active_assignment_task_definition,
    _validate_transition_allowed,
    build_bulk_review_campaign_definition_assignment_task_page,
    open_bulk_review_campaign_definition_assignment_task,
    transition_bulk_review_campaign_definition_assignment_task,
)
from src.core.waves.campaign_maker_checker_controls import (
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    record_bulk_review_campaign_definition_maker_checker_control,
)
from src.core.waves.campaign_definition_approval_decisions import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    build_bulk_review_campaign_definition_approval_decision_page,
    record_bulk_review_campaign_definition_approval_decision,
)
from src.core.waves.campaign_definition_launch_history import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    build_bulk_review_campaign_definition_launch_history_page,
    record_bulk_review_campaign_definition_launch,
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
        tenant_id="tenant-sg",
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


def _definition_with_id(
    campaign_id: str,
    *,
    display_name: str | None = None,
    **kwargs: Any,
) -> DpmBulkReviewCampaignDefinition:
    return _definition(**kwargs).model_copy(
        update={
            "campaign_id": campaign_id,
            "display_name": display_name or campaign_id,
        }
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


def test_campaign_operating_queue_posture_helpers_preserve_precedence() -> None:
    retired_definition = _definition().model_copy(update={"status": "RETIRED"})
    retired_discovery = build_bulk_review_campaign_discovery_item(
        definition=retired_definition,
        active_on=date(2026, 5, 16),
    )
    retired_readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=retired_definition,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
    )

    assert _closed_queue_posture(definition=retired_definition) == (
        "CLOSED",
        ["CAMPAIGN_DEFINITION_RETIRED"],
    )
    assert _classify_queue_posture(
        definition=retired_definition,
        readiness=retired_readiness,
        discovery=retired_discovery,
    ) == ("CLOSED", ["CAMPAIGN_DEFINITION_RETIRED"])


def test_campaign_operating_queue_attention_reasons_are_deduplicated() -> None:
    expired_definition = _definition(expires_on="2026-05-01")
    expired_discovery = build_bulk_review_campaign_discovery_item(
        definition=expired_definition,
        active_on=date(2026, 5, 16),
    )
    expired_readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=expired_definition,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
    )

    reasons = _attention_queue_reason_codes(
        readiness=expired_readiness,
        discovery=expired_discovery,
    )

    assert reasons.count("CAMPAIGN_DEFINITION_EXPIRED") == 1
    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in reasons


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


def test_campaign_operating_queue_paginates_after_expiry_filtering() -> None:
    page = build_bulk_review_campaign_operating_queue_page(
        definitions=[
            _definition_with_id("campaign-expired-first", expires_on="2026-05-01"),
            _definition_with_id("campaign-active-first"),
            _definition_with_id("campaign-active-second"),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_expired=False,
        limit=1,
        offset=1,
    )

    assert page.count == 1
    assert [item.campaign_id for item in page.items] == ["campaign-active-second"]
    assert page.status_counts == {"READY_TO_LAUNCH": 1}


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


def test_campaign_approval_inbox_governance_payload_projects_counts() -> None:
    governance = _definition(entitled_actor_ids=["pm_001", "ops"]).governance

    payload = approval_inbox_module._approval_inbox_governance_payload(governance)

    assert payload == {
        "approval_ref": "BRC-APPROVAL-2026-05",
        "approved_by": "cio_ops_committee",
        "approved_at": "2026-05-14T08:30:00+08:00",
        "expires_on": "2026-06-30",
        "access_purpose": "DPM_BULK_REVIEW_CAMPAIGN",
        "entitled_actor_count": 2,
        "approval_source_ref_count": 1,
    }


def test_campaign_approval_inbox_governance_payload_handles_missing_governance() -> None:
    payload = approval_inbox_module._approval_inbox_governance_payload(None)

    assert payload == {
        "approval_ref": None,
        "approved_by": None,
        "approved_at": None,
        "expires_on": None,
        "access_purpose": None,
        "entitled_actor_count": 0,
        "approval_source_ref_count": 0,
    }


def test_campaign_approval_inbox_entitlement_helper_filters_attention_reasons() -> None:
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=_definition(entitled_actor_ids=["ops"]),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
    )

    assert approval_inbox_module._entitlement_attention_posture(readiness) == (
        "ENTITLEMENT_ATTENTION",
        ["BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"],
    )


def test_campaign_approval_inbox_expiry_helper_falls_back_to_discovery_state() -> None:
    definition = _definition(expires_on="invalid-date")
    discovery = build_bulk_review_campaign_discovery_item(
        definition=definition,
        active_on=date(2026, 5, 16),
    )
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
    )
    readiness = readiness.model_copy(update={"reason_codes": []})

    assert approval_inbox_module._expiry_attention_posture(
        discovery=discovery,
        readiness=readiness,
    ) == ("EXPIRY_ATTENTION", ["CAMPAIGN_DEFINITION_EXPIRY_INVALID"])


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


def test_campaign_approval_inbox_paginates_after_status_filtering() -> None:
    page = build_bulk_review_campaign_approval_inbox_page(
        definitions=[
            _definition_with_id("campaign-approved"),
            _definition_with_id(
                "campaign-approval-required-first",
                approval_ref=None,
                approved_by=None,
                approved_at=None,
            ),
            _definition_with_id(
                "campaign-approval-required-second",
                approval_ref=None,
                approved_by=None,
                approved_at=None,
            ),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_closed=False,
        inbox_status="APPROVAL_REQUIRED",
        limit=1,
        offset=1,
    )

    assert page.count == 1
    assert [item.campaign_id for item in page.items] == ["campaign-approval-required-second"]
    assert page.status_counts == {"APPROVAL_REQUIRED": 1}


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


def test_campaign_workflow_board_action_helpers_prioritize_approval_attention() -> None:
    operating_queue = build_bulk_review_campaign_operating_queue_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    approval_inbox = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(approval_ref=None, approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert workflow_board_module._approval_inbox_workflow_action(approval_inbox) == (
        "ATTENTION_FOR_ACTOR",
        "RECORD_APPROVAL_DECISION",
        ["BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"],
    )
    assert workflow_board_module._classify_workflow_board_posture(
        operating_queue=operating_queue,
        approval_inbox=approval_inbox,
    ) == (
        "ATTENTION_FOR_ACTOR",
        "RECORD_APPROVAL_DECISION",
        ["BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"],
    )


def test_campaign_workflow_board_action_helpers_fall_back_to_operating_queue() -> None:
    operating_queue = build_bulk_review_campaign_operating_queue_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )
    approval_inbox = build_bulk_review_campaign_approval_inbox_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    assert workflow_board_module._approval_inbox_workflow_action(approval_inbox) is None
    assert workflow_board_module._operating_queue_workflow_action(operating_queue) == (
        "READY_FOR_ACTOR",
        "LAUNCH_CAMPAIGN",
        operating_queue.queue_reason_codes,
    )
    assert workflow_board_module._classify_workflow_board_posture(
        operating_queue=operating_queue,
        approval_inbox=approval_inbox,
    ) == (
        "READY_FOR_ACTOR",
        "LAUNCH_CAMPAIGN",
        operating_queue.queue_reason_codes,
    )


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


def test_campaign_workflow_board_paginates_after_next_action_filtering() -> None:
    page = build_bulk_review_campaign_workflow_board_page(
        definitions=[
            _definition_with_id("campaign-ready"),
            _definition_with_id(
                "campaign-approval-required-first",
                approval_ref=None,
                approved_by=None,
                approved_at=None,
            ),
            _definition_with_id(
                "campaign-approval-required-second",
                approval_ref=None,
                approved_by=None,
                approved_at=None,
            ),
        ],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
        include_closed=False,
        board_status=None,
        next_action="RECORD_APPROVAL_DECISION",
        limit=1,
        offset=1,
    )

    assert page.count == 1
    assert [item.campaign_id for item in page.items] == ["campaign-approval-required-second"]
    assert page.status_counts == {"ATTENTION_FOR_ACTOR": 1}
    assert page.next_action_counts == {"RECORD_APPROVAL_DECISION": 1}


def test_campaign_workflow_board_helpers_filter_count_and_hash_rows() -> None:
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
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition().model_dump(mode="python"),
            "campaign_id": "campaign-holdings-retired-board-20260510",
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-board",
            "content_hash": "",
        }
    )
    closed = build_bulk_review_campaign_workflow_board_item(
        definition=retired,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    filtered = _filtered_workflow_board_items(
        items=[ready, approval_required, closed],
        include_closed=False,
        board_status="ATTENTION_FOR_ACTOR",
        next_action=None,
    )
    status_counts, next_action_counts = _workflow_board_counts(filtered)
    payload = _workflow_board_page_payload(items=filtered, limit=50, offset=0)
    page = DpmBulkReviewCampaignWorkflowBoardPage.model_validate(payload)

    assert [item.campaign_id for item in filtered] == [approval_required.campaign_id]
    assert status_counts == {"ATTENTION_FOR_ACTOR": 1}
    assert next_action_counts == {"RECORD_APPROVAL_DECISION": 1}
    assert page.count == 1
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


def test_campaign_assignment_plan_helpers_filter_and_count_rows() -> None:
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

    filtered = _filtered_assignment_plan_items(
        items=[ready, approval_required, unauthorized],
        include_closed=False,
        escalation_tier=None,
        next_action="REVIEW_ACTOR_ENTITLEMENT",
    )

    assert [item.campaign_id for item in filtered] == [unauthorized.campaign_id]
    assert _assignment_plan_counts([ready, approval_required, unauthorized], "escalation_tier") == {
        "PM": 1,
        "GOVERNANCE": 1,
        "OPS": 1,
    }
    assert _assignment_plan_counts([ready, approval_required, unauthorized], "sla_posture") == {
        "ON_TRACK": 1,
        "ATTENTION": 1,
        "BREACHED_OR_BLOCKED": 1,
    }


def test_campaign_assignment_plan_page_payload_hashes_filtered_rows() -> None:
    assignment_plan = build_bulk_review_campaign_assignment_plan_item(
        definition=_definition(approval_ref=None, approved_by=None, approved_at=None),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 16),
    )

    payload = _assignment_plan_page_payload(items=[assignment_plan], limit=25, offset=5)

    assert payload["product_name"] == "BulkReviewCampaignAssignmentPlan"
    assert payload["limit"] == 25
    assert payload["offset"] == 5
    assert payload["count"] == 1
    assert payload["escalation_tier_counts"] == {"GOVERNANCE": 1}
    assert payload["sla_posture_counts"] == {"ATTENTION": 1}
    assert str(payload["content_hash"]).startswith("sha256:")


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


def test_campaign_assignment_action_page_state_tracks_latest_action() -> None:
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=_definition(),
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
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

    actions = _sorted_assignment_actions(escalated)
    state = _assignment_action_page_state(actions)

    assert [action.action_ref for action in actions] == [
        "BRC-ASSIGN-2026-05-002",
        "BRC-ASSIGN-2026-05-001",
    ]
    assert state.latest_action_type == "ESCALATED"
    assert state.current_assigned_actor_ids == ["governance_ops"]
    assert state.current_escalation_tier == "GOVERNANCE"
    assert state.current_sla_posture == "ATTENTION"


def test_campaign_assignment_action_page_state_defaults_and_resolved_actions() -> None:
    empty_state = _assignment_action_page_state([])
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=_definition(),
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
    resolved_state = _assignment_action_page_state(_sorted_assignment_actions(resolved))

    assert empty_state.latest_action_type is None
    assert empty_state.current_assigned_actor_ids == []
    assert empty_state.current_escalation_tier == "NONE"
    assert empty_state.current_sla_posture == "ON_TRACK"
    assert resolved_state.latest_action_type == "RESOLVED"
    assert resolved_state.current_assigned_actor_ids == []
    assert resolved_state.current_escalation_tier == "NONE"


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


def test_campaign_workflow_mutations_enforce_command_actor_entitlements() -> None:
    definition = _definition(entitled_actor_ids=["pm_001"])

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"):
        record_bulk_review_campaign_definition_assignment_action(
            definition=definition,
            action_type="ASSIGNED",
            action_ref="BRC-ASSIGN-2026-05-001",
            recorded_by="ops",
            action_reason="Route ready campaign to assigned PM.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            correlation_id="corr-campaign-assignment-action-unentitled",
        )
    assert definition.assignment_actions == []

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"):
        open_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref="BRC-TASK-2026-05-001",
            task_type="ASSIGNMENT",
            opened_by="ops",
            task_reason="Campaign requires PM acknowledgement.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            correlation_id="corr-campaign-assignment-task-unentitled",
        )
    assert definition.assignment_tasks == []

    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="pm_001",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-entitled",
    )
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"):
        transition_bulk_review_campaign_definition_assignment_task(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
            transition_type="ACKNOWLEDGED",
            transition_ref="BRC-TASK-2026-05-001:ack",
            transitioned_by="ops",
            transition_reason="Unentitled acknowledgement.",
            correlation_id="corr-campaign-assignment-task-transition-unentitled",
        )
    assert len(opened.assignment_tasks[0].transitions) == 1

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=definition,
            control_action="SUBMITTED_FOR_REVIEW",
            control_ref="BRC-MC-2026-05-001",
            recorded_by="ops",
            submitter_actor_id="pm_001",
            control_outcome="PENDING",
            control_reason="Submit for review.",
            correlation_id="corr-campaign-maker-checker-unentitled",
        )
    assert definition.maker_checker_controls == []


def test_campaign_workflow_mutations_allow_absent_entitlement_list() -> None:
    definition = _definition(entitled_actor_ids=[])

    updated = record_bulk_review_campaign_definition_assignment_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-no-entitlements",
    )

    assert [action.recorded_by for action in updated.assignment_actions] == ["ops"]


def test_assignment_action_request_normalizes_actor_ids_and_text_fields() -> None:
    request = _assignment_action_request(
        action_type="ASSIGNED",
        action_ref=" BRC-ASSIGN-2026-05-001 ",
        recorded_by=" ops ",
        action_reason=" Route ready campaign. ",
        assigned_actor_ids=[" pm_002 ", "pm_001", "pm_001", " "],
        escalation_tier="PM",
        correlation_id=" corr-assignment-action ",
    )

    assert request.action_ref == "BRC-ASSIGN-2026-05-001"
    assert request.recorded_by == "ops"
    assert request.action_reason == "Route ready campaign."
    assert request.assigned_actor_ids == ["pm_001", "pm_002"]
    assert request.correlation_id == "corr-assignment-action"


def test_assignment_action_replay_helper_returns_definition_or_rejects_conflict() -> None:
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=_definition(),
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    existing_action = assigned.assignment_actions[0]

    assert _assignment_action_replay_result(definition=assigned, action=existing_action) is assigned
    conflicting_action = existing_action.model_copy(
        update={"content_hash": "sha256:conflicting-action"}
    )
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT",
    ):
        _assignment_action_replay_result(definition=assigned, action=conflicting_action)


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


def test_assignment_task_page_helpers_sort_filter_page_and_count_open_tasks() -> None:
    first_opened = open_bulk_review_campaign_definition_assignment_task(
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
    second_opened = open_bulk_review_campaign_definition_assignment_task(
        definition=first_opened,
        task_ref="BRC-TASK-2026-05-002",
        task_type="ESCALATION",
        opened_by="ops",
        task_reason="Campaign requires escalation review.",
        assigned_actor_ids=["ops_001"],
        escalation_tier="OPS",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-task-002",
    )
    older_open_task = second_opened.assignment_tasks[0].model_copy(
        update={"opened_at": datetime(2026, 5, 10, tzinfo=timezone.utc)}
    )
    newer_closed_task = second_opened.assignment_tasks[1].model_copy(
        update={
            "opened_at": datetime(2026, 5, 11, tzinfo=timezone.utc),
            "status": "RESOLVED",
        }
    )
    tasks = [older_open_task, newer_closed_task]

    sorted_tasks = _assignment_tasks_sorted_latest(tasks)

    assert [task.task_ref for task in sorted_tasks] == [
        "BRC-TASK-2026-05-002",
        "BRC-TASK-2026-05-001",
    ]
    assert _filtered_assignment_tasks(tasks=sorted_tasks, status_filter="OPEN") == [older_open_task]
    assert _filtered_assignment_tasks(tasks=sorted_tasks, status_filter=None) == sorted_tasks
    assert _assignment_task_page_slice(tasks=sorted_tasks, limit=1, offset=1) == [older_open_task]
    assert _open_assignment_task_count(tasks) == 1


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


def test_campaign_workflow_automation_helpers_filter_count_and_hash_rows() -> None:
    candidate = build_bulk_review_campaign_workflow_automation_item(
        definition=_definition(),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition().model_dump(mode="python"),
            "campaign_id": "campaign-holdings-retired-automation-helper-20260510",
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-automation-helper",
            "content_hash": "",
        }
    )
    closed = build_bulk_review_campaign_workflow_automation_item(
        definition=retired,
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=date(2026, 5, 10),
    )

    filtered = _filtered_workflow_automation_items(
        items=[candidate, closed],
        include_closed=True,
        automation_status=None,
        automation_action="NO_AUTOMATION_CLOSED",
    )
    status_counts, action_counts = _workflow_automation_counts(filtered)
    payload = _workflow_automation_page_payload(items=filtered, limit=50, offset=0)
    page = DpmBulkReviewCampaignWorkflowAutomationPage.model_validate(payload)

    assert [item.campaign_id for item in filtered] == [
        "campaign-holdings-retired-automation-helper-20260510"
    ]
    assert status_counts == {"CLOSED": 1}
    assert action_counts == {"NO_AUTOMATION_CLOSED": 1}
    assert page.count == 1
    assert page.capability_posture.content_hash == candidate.capability_posture.content_hash
    assert page.content_hash == hash_canonical_payload(
        strip_keys(page.model_dump(mode="json"), exclude={"content_hash"})
    )


def test_campaign_operating_pages_reject_inconsistent_summary_metadata() -> None:
    definition = _definition()
    active_on = date(2026, 5, 10)

    operating_queue = build_bulk_review_campaign_operating_queue_page(
        definitions=[definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=active_on,
        include_expired=False,
        limit=50,
        offset=0,
    )
    approval_inbox = build_bulk_review_campaign_approval_inbox_page(
        definitions=[definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=active_on,
        include_closed=False,
        inbox_status=None,
        limit=50,
        offset=0,
    )
    workflow_board = build_bulk_review_campaign_workflow_board_page(
        definitions=[definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=active_on,
        include_closed=False,
        board_status=None,
        next_action=None,
        limit=50,
        offset=0,
    )
    assignment_plan = build_bulk_review_campaign_assignment_plan_page(
        definitions=[definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=active_on,
        include_closed=False,
        escalation_tier=None,
        next_action=None,
        limit=50,
        offset=0,
    )
    automation = build_bulk_review_campaign_workflow_automation_page(
        definitions=[definition],
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        active_on=active_on,
        include_closed=False,
        automation_status=None,
        automation_action=None,
        limit=50,
        offset=0,
    )

    _assert_page_rejects(
        DpmBulkReviewCampaignOperatingQueuePage,
        operating_queue.model_dump(mode="json"),
        "count",
        2,
        "count must equal the returned item count",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignOperatingQueuePage,
        operating_queue.model_dump(mode="json"),
        "status_counts",
        {"ATTENTION_REQUIRED": 1},
        "status_counts must match the returned page items",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignApprovalInboxPage,
        approval_inbox.model_dump(mode="json"),
        "status_counts",
        {"APPROVAL_COMPLETE": -1},
        "status_counts values must be non-negative",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignWorkflowBoardPage,
        workflow_board.model_dump(mode="json"),
        "next_action_counts",
        {"RECORD_APPROVAL_DECISION": 1},
        "next_action_counts must match the returned page items",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignAssignmentPlanPage,
        assignment_plan.model_dump(mode="json"),
        "sla_posture_counts",
        {"ATTENTION": 1},
        "sla_posture_counts must match the returned page items",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignWorkflowAutomationPage,
        automation.model_dump(mode="json"),
        "automation_action_counts",
        {"NO_AUTOMATION_BLOCKED": 1},
        "automation_action_counts must match the returned page items",
    )


def _assert_page_rejects(
    page_model: type[BaseModel],
    payload: dict[str, object],
    field_name: str,
    invalid_value: object,
    match: str,
) -> None:
    invalid_payload = {**payload, field_name: invalid_value}
    with pytest.raises(ValidationError, match=match):
        page_model.model_validate(invalid_payload)


def test_campaign_audit_pages_reject_inconsistent_summary_metadata() -> None:
    definition = _definition()
    approved = record_bulk_review_campaign_definition_approval_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-DECISION-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Campaign approved for launch.",
        correlation_id="corr-campaign-approval-decision-001",
    )
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
    tasked = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    controlled = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="pm_001",
        control_reason="Submit campaign for checker review.",
        correlation_id="corr-campaign-maker-checker-001",
        control_outcome="PENDING",
        submitter_actor_id="pm_001",
    )
    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="wave_20260510_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-launch-001",
        idempotency_key="idem-campaign-launch-001",
    )

    approval_page = build_bulk_review_campaign_definition_approval_decision_page(
        definition=approved,
        limit=50,
        offset=0,
    )
    assignment_action_page = build_bulk_review_campaign_definition_assignment_action_page(
        definition=assigned,
        limit=50,
        offset=0,
    )
    assignment_task_page = build_bulk_review_campaign_definition_assignment_task_page(
        definition=tasked,
        limit=50,
        offset=0,
    )
    maker_checker_page = build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=controlled,
        limit=50,
        offset=0,
    )
    launch_history_page = build_bulk_review_campaign_definition_launch_history_page(
        definition=launched,
        limit=50,
        offset=0,
    )

    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
        approval_page.model_dump(mode="json"),
        "count",
        2,
        "count must equal the returned item count",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionAssignmentActionPage,
        assignment_action_page.model_dump(mode="json"),
        "count",
        2,
        "count must equal the returned item count",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
        assignment_task_page.model_dump(mode="json"),
        "status_counts",
        {"OPEN": 0},
        "status_counts must cover the returned page items",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
        assignment_task_page.model_dump(mode="json"),
        "open_task_count",
        2,
        "open_task_count must be covered by status_counts",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
        maker_checker_page.model_dump(mode="json"),
        "count",
        2,
        "count must equal the returned item count",
    )
    _assert_page_rejects(
        DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
        launch_history_page.model_dump(mode="json"),
        "total_count",
        0,
        "total_count must be greater than or equal to count",
    )


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


def test_validate_active_assignment_task_definition_rejects_inactive_definition() -> None:
    _validate_active_assignment_task_definition(_definition())

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTIVE_REQUIRED"):
        _validate_active_assignment_task_definition(
            _definition().model_copy(update={"status": "DRAFT"})
        )


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


def test_assignment_task_for_ref_returns_index_and_task_or_not_found() -> None:
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

    index, task = _assignment_task_for_ref(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
    )

    assert index == 0
    assert task.task_ref == "BRC-TASK-2026-05-001"
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND"):
        _assignment_task_for_ref(definition=opened, task_ref="missing-task")


def test_campaign_assignment_task_open_request_fields_are_normalized() -> None:
    fields = _open_task_request_fields(
        task_ref=" BRC-TASK-2026-05-001 ",
        opened_by=" ops ",
        task_reason=" Campaign requires PM acknowledgement. ",
        assigned_actor_ids=[" pm_002 ", "pm_001", "pm_001", " "],
        correlation_id=" corr-campaign-assignment-task-001 ",
    )

    assert fields.task_ref == "BRC-TASK-2026-05-001"
    assert fields.opened_by == "ops"
    assert fields.task_reason == "Campaign requires PM acknowledgement."
    assert fields.assigned_actor_ids == ["pm_001", "pm_002"]
    assert fields.correlation_id == "corr-campaign-assignment-task-001"


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        ({"task_ref": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_REQUIRED"),
        ({"opened_by": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTOR_REQUIRED"),
        ({"task_reason": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REASON_REQUIRED"),
        (
            {"assigned_actor_ids": [" "]},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED",
        ),
        (
            {"correlation_id": " "},
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CORRELATION_REQUIRED",
        ),
    ],
)
def test_campaign_assignment_task_open_request_fields_reject_missing_input(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    request = {
        "task_ref": "BRC-TASK-2026-05-001",
        "opened_by": "ops",
        "task_reason": "Campaign requires PM acknowledgement.",
        "assigned_actor_ids": ["pm_001"],
        "correlation_id": "corr-campaign-assignment-task-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        _open_task_request_fields(**request)


def test_replayed_open_task_definition_returns_definition_or_conflicts() -> None:
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
    existing_task = opened.assignment_tasks[0]

    assert _replayed_open_task_definition(definition=opened, task=existing_task) is opened
    assert (
        _replayed_open_task_definition(
            definition=_definition(),
            task=existing_task,
        )
        is None
    )

    conflicting_task = existing_task.model_copy(update={"content_hash": "sha256:conflict"})
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT"):
        _replayed_open_task_definition(definition=opened, task=conflicting_task)


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


def test_campaign_assignment_task_transition_request_fields_are_normalized() -> None:
    fields = _transition_request_fields(
        task_ref=" BRC-TASK-2026-05-001 ",
        transition_ref=" BRC-TASK-2026-05-001:ack ",
        transitioned_by=" pm_001 ",
        transition_reason=" Assigned PM acknowledged the task. ",
        correlation_id=" corr-campaign-assignment-task-transition-001 ",
    )

    assert fields.task_ref == "BRC-TASK-2026-05-001"
    assert fields.transition_ref == "BRC-TASK-2026-05-001:ack"
    assert fields.transitioned_by == "pm_001"
    assert fields.transition_reason == "Assigned PM acknowledged the task."
    assert fields.correlation_id == "corr-campaign-assignment-task-transition-001"


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        ({"task_ref": " "}, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_REQUIRED"),
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
def test_campaign_assignment_task_transition_request_fields_reject_missing_text(
    overrides: dict[str, str],
    reason_code: str,
) -> None:
    request = {
        "task_ref": "BRC-TASK-2026-05-001",
        "transition_ref": "BRC-TASK-2026-05-001:ack",
        "transitioned_by": "pm_001",
        "transition_reason": "Assigned PM acknowledged the task.",
        "correlation_id": "corr-campaign-assignment-task-transition-001",
    } | overrides

    with pytest.raises(ValueError, match=reason_code):
        _transition_request_fields(**request)


def test_definition_with_replaced_assignment_task_preserves_other_tasks() -> None:
    first_opened = open_bulk_review_campaign_definition_assignment_task(
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
    second_opened = open_bulk_review_campaign_definition_assignment_task(
        definition=first_opened,
        task_ref="BRC-TASK-2026-05-002",
        task_type="ESCALATION",
        opened_by="ops",
        task_reason="Campaign requires escalation review.",
        assigned_actor_ids=["ops_001"],
        escalation_tier="OPS",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-task-002",
    )
    replacement = second_opened.assignment_tasks[0].model_copy(
        update={"status": "ACKNOWLEDGED", "content_hash": "sha256:replacement"}
    )

    updated = _definition_with_replaced_assignment_task(
        definition=second_opened,
        task_index=0,
        task=replacement,
    )

    assert updated.assignment_tasks[0].status == "ACKNOWLEDGED"
    assert updated.assignment_tasks[1] == second_opened.assignment_tasks[1]
    assert updated.content_hash


def test_definition_with_appended_assignment_task_revalidates_content_hash() -> None:
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
    source_definition = _definition()

    updated = _definition_with_appended_assignment_task(
        definition=source_definition,
        task=opened.assignment_tasks[0],
    )

    assert updated.assignment_tasks == opened.assignment_tasks
    assert updated.content_hash
    assert updated.content_hash != source_definition.content_hash


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


def test_campaign_assignment_task_transition_field_helper_resolves_due_date_change() -> None:
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
    due_at = datetime(2026, 5, 12, 8, tzinfo=timezone.utc)

    fields = _transition_task_fields(
        task=opened.assignment_tasks[0],
        transition_type="DUE_DATE_CHANGED",
        assigned_actor_ids=None,
        escalation_tier=None,
        sla_posture="ATTENTION",
        due_at=due_at,
    )

    assert fields.next_status == "OPEN"
    assert fields.next_assignees == ["pm_001"]
    assert fields.next_tier == "PM"
    assert fields.next_sla == "ATTENTION"
    assert fields.next_due_at == due_at


def test_campaign_assignment_task_transition_assignee_helper_normalizes_actor_ids() -> None:
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

    assert _transition_next_assignees(
        task=opened.assignment_tasks[0],
        assigned_actor_ids=[" pm_002 ", "pm_001", "pm_002", ""],
    ) == ["pm_001", "pm_002"]
    assert _transition_next_assignees(
        task=opened.assignment_tasks[0],
        assigned_actor_ids=None,
    ) == ["pm_001"]


def test_campaign_assignment_task_index_returns_position_or_none() -> None:
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

    assert (
        _assignment_task_index(
            definition=opened,
            task_ref="BRC-TASK-2026-05-001",
        )
        == 0
    )
    assert (
        _assignment_task_index(
            definition=opened,
            task_ref="BRC-TASK-MISSING",
        )
        is None
    )


def test_campaign_assignment_task_transition_replay_helper_returns_definition_or_conflict() -> None:
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
        transition_ref="BRC-TASK-2026-05-001:acknowledged",
        transitioned_by="pm_001",
        transition_reason="PM acknowledged source-backed campaign task.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )
    task = acknowledged.assignment_tasks[0]

    assert (
        _assignment_task_transition(
            task=task,
            transition_ref="BRC-TASK-2026-05-001:acknowledged",
        )
        == task.transitions[-1]
    )
    assert (
        _replayed_transition_definition(
            definition=acknowledged,
            task=task,
            transition_ref="BRC-TASK-2026-05-001:acknowledged",
            transition_type="ACKNOWLEDGED",
            transitioned_by="pm_001",
            transition_reason="PM acknowledged source-backed campaign task.",
            correlation_id="corr-campaign-assignment-task-transition-001",
            assigned_actor_ids=None,
            escalation_tier=None,
            sla_posture=None,
            due_at=None,
            source_refs=[],
        )
        is acknowledged
    )
    assert (
        _replayed_transition_definition(
            definition=acknowledged,
            task=task,
            transition_ref="BRC-TASK-2026-05-001:missing",
            transition_type="ACKNOWLEDGED",
            transitioned_by="pm_001",
            transition_reason="PM acknowledged source-backed campaign task.",
            correlation_id="corr-campaign-assignment-task-transition-001",
            assigned_actor_ids=None,
            escalation_tier=None,
            sla_posture=None,
            due_at=None,
            source_refs=[],
        )
        is None
    )
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT",
    ):
        _replayed_transition_definition(
            definition=acknowledged,
            task=task,
            transition_ref="BRC-TASK-2026-05-001:acknowledged",
            transition_type="ACKNOWLEDGED",
            transitioned_by="pm_001",
            transition_reason="Different replay reason.",
            correlation_id="corr-campaign-assignment-task-transition-001",
            assigned_actor_ids=None,
            escalation_tier=None,
            sla_posture=None,
            due_at=None,
            source_refs=[],
        )


def test_campaign_assignment_task_transition_field_requirement_helper_rejects_missing_fields() -> (
    None
):
    assert _transition_requires_open_assignees(next_status="OPEN", next_assignees=[])
    assert not _transition_requires_open_assignees(next_status="RESOLVED", next_assignees=[])
    assert _transition_requires_actor_ids(transition_type="REASSIGNED", assigned_actor_ids=None)
    assert not _transition_requires_actor_ids(
        transition_type="ACKNOWLEDGED",
        assigned_actor_ids=None,
    )
    assert _transition_requires_due_at(transition_type="DUE_DATE_CHANGED", due_at=None)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED",
    ):
        _validate_transition_field_requirements(
            transition_type="REASSIGNED",
            next_status="OPEN",
            next_assignees=[],
            assigned_actor_ids=None,
            due_at=None,
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_DUE_AT_REQUIRED",
    ):
        _validate_transition_field_requirements(
            transition_type="DUE_DATE_CHANGED",
            next_status="OPEN",
            next_assignees=["pm_001"],
            assigned_actor_ids=None,
            due_at=None,
        )


def test_campaign_assignment_task_transition_validation_blocks_opened_and_closed() -> None:
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
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_OPENED_TRANSITION_FORBIDDEN",
    ):
        _validate_transition_allowed(
            task=opened.assignment_tasks[0],
            transition_type="OPENED",
        )
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CLOSED_TRANSITION_FORBIDDEN",
    ):
        _validate_transition_allowed(
            task=resolved.assignment_tasks[0],
            transition_type="STARTED",
        )


def test_campaign_assignment_transition_replay_helpers_project_comparison_fields() -> None:
    source_refs = [
        DpmWaveSourceRef(
            source_system="lotus-manage",
            source_type="CAMPAIGN_ASSIGNMENT_TASK",
            source_id="brc-task-source-ref",
        )
    ]
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
        source_refs=source_refs,
    )
    transition = acknowledged.assignment_tasks[0].transitions[-1]

    assert _required_transition_replay_fields(transition) == (
        "ACKNOWLEDGED",
        "pm_001",
        "Assigned PM acknowledged the task.",
        "corr-campaign-assignment-task-transition-001",
    )
    assert _source_ref_payloads(transition.source_refs) == _source_ref_payloads(source_refs)
    assert _optional_transition_replay_fields_match(
        transition=transition,
        assigned_actor_ids=None,
        escalation_tier=None,
        sla_posture=None,
        due_at=None,
    )
    assert not _optional_transition_replay_fields_match(
        transition=transition,
        assigned_actor_ids=["pm_002"],
        escalation_tier=None,
        sla_posture=None,
        due_at=None,
    )
    assert _transition_assignees_replay_match(
        transition=transition,
        assigned_actor_ids=[" pm_001 ", "pm_001"],
    )
    assert not _transition_assignees_replay_match(
        transition=transition,
        assigned_actor_ids=["pm_002"],
    )
    assert _transition_escalation_tier_replay_match(transition=transition, escalation_tier=None)
    assert not _transition_escalation_tier_replay_match(
        transition=transition, escalation_tier="OPS"
    )
    assert _transition_sla_posture_replay_match(transition=transition, sla_posture=None)
    assert not _transition_sla_posture_replay_match(transition=transition, sla_posture="ATTENTION")
    assert _transition_due_at_replay_match(transition=transition, due_at=None)
    assert not _transition_due_at_replay_match(
        transition=transition,
        due_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
    )


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
    assigned = record_bulk_review_campaign_definition_maker_checker_control(
        definition=submitted,
        control_action="REVIEWER_ASSIGNED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PENDING",
        control_reason="Independent reviewer assigned for campaign definition control.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    exception_open = record_bulk_review_campaign_definition_maker_checker_control(
        definition=assigned,
        control_action="CONTROL_EXCEPTION_RAISED",
        control_ref="BRC-MC-2026-05-003",
        recorded_by="ops",
        control_outcome="EXCEPTION_OPEN",
        control_reason="Control evidence requires remediation.",
        correlation_id="corr-campaign-maker-checker-control-003",
    )
    exception_resolved = record_bulk_review_campaign_definition_maker_checker_control(
        definition=exception_open,
        control_action="CONTROL_EXCEPTION_RESOLVED",
        control_ref="BRC-MC-2026-05-004",
        recorded_by="ops",
        control_outcome="EXCEPTION_RESOLVED",
        control_reason="Control evidence remediation accepted.",
        correlation_id="corr-campaign-maker-checker-control-004",
    )

    page = build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=exception_resolved,
        limit=50,
        offset=0,
    )

    assert page.count == 4
    assert page.latest_control_action == "CONTROL_EXCEPTION_RESOLVED"
    assert page.current_control_outcome == "EXCEPTION_RESOLVED"


def test_campaign_maker_checker_controls_reject_invalid_lifecycle_sequences() -> None:
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMISSION_REQUIRED",
    ):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=_definition(),
            control_action="REVIEW_COMPLETED",
            control_ref="BRC-MC-2026-05-001",
            recorded_by="ops",
            submitter_actor_id="pm_001",
            reviewer_actor_id="cio_ops_committee",
            required_reviewer_role="CIO_OPERATIONS_REVIEWER",
            control_outcome="PASSED",
            control_reason="Invalid review completion without submission.",
            correlation_id="corr-campaign-maker-checker-control-invalid-review",
        )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_OPEN_EXCEPTION_REQUIRED",
    ):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=_definition(),
            control_action="CONTROL_EXCEPTION_RESOLVED",
            control_ref="BRC-MC-2026-05-002",
            recorded_by="ops",
            control_outcome="EXCEPTION_RESOLVED",
            control_reason="Invalid exception resolution without open exception.",
            correlation_id="corr-campaign-maker-checker-control-invalid-resolution",
        )

    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=_definition(),
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-003",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-003",
    )
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTOR_SEPARATION_REQUIRED",
    ):
        record_bulk_review_campaign_definition_maker_checker_control(
            definition=submitted,
            control_action="REVIEWER_ASSIGNED",
            control_ref="BRC-MC-2026-05-004",
            recorded_by="ops",
            reviewer_actor_id="pm_001",
            required_reviewer_role="CIO_OPERATIONS_REVIEWER",
            control_outcome="PENDING",
            control_reason="Invalid same actor reviewer assignment.",
            correlation_id="corr-campaign-maker-checker-control-invalid-assignment",
        )


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
