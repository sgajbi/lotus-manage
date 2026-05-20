from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_workflow_board import (
    CampaignWorkflowNextAction,
    DpmBulkReviewCampaignWorkflowBoardItem,
    build_bulk_review_campaign_workflow_board_item,
)
from src.core.waves.campaign_operating_boundaries import (
    CAMPAIGN_ASSIGNMENT_PLAN_OPERATING_BOUNDARIES,
)


CampaignAssignmentEscalationTier = Literal["NONE", "PM", "OPS", "GOVERNANCE"]
CampaignAssignmentSlaPosture = Literal["ON_TRACK", "ATTENTION", "BREACHED_OR_BLOCKED"]


class DpmBulkReviewCampaignAssignmentPlanItem(BaseModel):
    """Read-only assignment and escalation plan for one bulk-review campaign definition."""

    product_name: Literal["BulkReviewCampaignAssignmentPlanItem"] = (
        "BulkReviewCampaignAssignmentPlanItem"
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
    assigned_actor_ids: list[str] = Field(
        description=(
            "Actor ids derived from campaign entitlement evidence, or the queried actor when no "
            "explicit entitlement list exists. This is routing evidence only."
        )
    )
    next_action: CampaignWorkflowNextAction = Field(
        description="Operator action inherited from the campaign workflow board."
    )
    escalation_tier: CampaignAssignmentEscalationTier = Field(
        description="Read-only escalation tier derived from board posture and reason codes."
    )
    sla_posture: CampaignAssignmentSlaPosture = Field(
        description="Operational SLA posture for triage; this does not create a task or mutate state."
    )
    escalation_reason_codes: list[str] = Field(
        description="Reason codes explaining the assignment or escalation posture."
    )
    workflow_board: DpmBulkReviewCampaignWorkflowBoardItem = Field(
        description="Source workflow-board row used to derive the assignment plan."
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(CAMPAIGN_ASSIGNMENT_PLAN_OPERATING_BOUNDARIES),
        description="Unsupported downstream claims the assignment plan must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the assignment-plan row.")


class DpmBulkReviewCampaignAssignmentPlanPage(BaseModel):
    """Read-only assignment and escalation plan over persisted campaign definitions."""

    product_name: Literal["BulkReviewCampaignAssignmentPlan"] = "BulkReviewCampaignAssignmentPlan"
    product_version: Literal["v1"] = "v1"
    items: list[DpmBulkReviewCampaignAssignmentPlanItem]
    limit: int
    offset: int
    count: int
    escalation_tier_counts: dict[str, int] = Field(
        description="Assignment-plan row counts by escalation tier for the returned page."
    )
    sla_posture_counts: dict[str, int] = Field(
        description="Assignment-plan row counts by SLA posture for the returned page."
    )
    content_hash: str = Field(description="Canonical hash over the assignment-plan page.")


def build_bulk_review_campaign_assignment_plan_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
) -> DpmBulkReviewCampaignAssignmentPlanItem:
    """Derive one read-only assignment/escalation plan row from workflow-board posture."""

    board = build_bulk_review_campaign_workflow_board_item(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
    )
    escalation_tier, sla_posture, reason_codes = _classify_assignment_plan(board)
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignAssignmentPlanItem",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "display_name": definition.display_name,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "assigned_actor_ids": board.assigned_actor_ids,
        "next_action": board.next_action,
        "escalation_tier": escalation_tier,
        "sla_posture": sla_posture,
        "escalation_reason_codes": reason_codes,
        "workflow_board": board.model_dump(mode="json"),
        "operating_boundaries": list(CAMPAIGN_ASSIGNMENT_PLAN_OPERATING_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignAssignmentPlanItem.model_validate(payload)


def build_bulk_review_campaign_assignment_plan_page(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
    include_closed: bool,
    escalation_tier: CampaignAssignmentEscalationTier | None,
    next_action: CampaignWorkflowNextAction | None,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignAssignmentPlanPage:
    items = [
        build_bulk_review_campaign_assignment_plan_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]
    if not include_closed:
        items = [item for item in items if item.workflow_board.board_status != "CLOSED"]
    if escalation_tier is not None:
        items = [item for item in items if item.escalation_tier == escalation_tier]
    if next_action is not None:
        items = [item for item in items if item.next_action == next_action]

    escalation_tier_counts: dict[str, int] = {}
    sla_posture_counts: dict[str, int] = {}
    for item in items:
        escalation_tier_counts[item.escalation_tier] = (
            escalation_tier_counts.get(item.escalation_tier, 0) + 1
        )
        sla_posture_counts[item.sla_posture] = sla_posture_counts.get(item.sla_posture, 0) + 1

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignAssignmentPlan",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "escalation_tier_counts": escalation_tier_counts,
        "sla_posture_counts": sla_posture_counts,
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignAssignmentPlanPage.model_validate(payload)


def _classify_assignment_plan(
    board: DpmBulkReviewCampaignWorkflowBoardItem,
) -> tuple[
    CampaignAssignmentEscalationTier,
    CampaignAssignmentSlaPosture,
    list[str],
]:
    if board.board_status == "CLOSED":
        return "NONE", "ON_TRACK", ["CAMPAIGN_DEFINITION_CLOSED"]
    if board.next_action == "LAUNCH_CAMPAIGN":
        return "PM", "ON_TRACK", ["CAMPAIGN_READY_FOR_ASSIGNED_ACTOR"]
    if board.next_action == "REVIEW_ACTOR_ENTITLEMENT":
        return "OPS", "BREACHED_OR_BLOCKED", board.board_reason_codes
    if board.next_action in {
        "RECORD_APPROVAL_DECISION",
        "REMEDIATE_APPROVAL_EVIDENCE",
        "REFRESH_EXPIRY_OR_AS_OF_DATE",
    }:
        return "GOVERNANCE", "ATTENTION", board.board_reason_codes
    return "OPS", "ATTENTION", board.board_reason_codes


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
