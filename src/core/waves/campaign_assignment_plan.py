from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_workflow_board import (
    CampaignWorkflowNextAction,
    DpmBulkReviewCampaignWorkflowBoardItem,
    build_bulk_review_campaign_workflow_board_item,
)
from src.core.waves.campaign_operating_boundaries import (
    CAMPAIGN_ASSIGNMENT_PLAN_OPERATING_BOUNDARIES,
)
from src.core.waves.campaign_page_validation import (
    page_items,
    validate_count_map,
    validate_page_count,
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
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    count: int = Field(ge=0)
    escalation_tier_counts: dict[str, int] = Field(
        description="Assignment-plan row counts by escalation tier for the returned page."
    )
    sla_posture_counts: dict[str, int] = Field(
        description="Assignment-plan row counts by SLA posture for the returned page."
    )
    content_hash: str = Field(description="Canonical hash over the assignment-plan page.")

    @model_validator(mode="after")
    def validate_page_metadata(self) -> DpmBulkReviewCampaignAssignmentPlanPage:
        validate_page_count(count=self.count, item_count=len(self.items))
        validate_count_map(
            counts=self.escalation_tier_counts,
            observed_values=(item.escalation_tier for item in self.items),
            field_name="escalation_tier_counts",
        )
        validate_count_map(
            counts=self.sla_posture_counts,
            observed_values=(item.sla_posture for item in self.items),
            field_name="sla_posture_counts",
        )
        return self


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
    items = _filtered_assignment_plan_items(
        items=_assignment_plan_items(
            definitions=definitions,
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        ),
        include_closed=include_closed,
        escalation_tier=escalation_tier,
        next_action=next_action,
    )
    page = page_items(items, limit=limit, offset=offset)
    payload = _assignment_plan_page_payload(
        items=page,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignAssignmentPlanPage.model_validate(payload)


def _assignment_plan_items(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
) -> list[DpmBulkReviewCampaignAssignmentPlanItem]:
    return [
        build_bulk_review_campaign_assignment_plan_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]


def _filtered_assignment_plan_items(
    *,
    items: list[DpmBulkReviewCampaignAssignmentPlanItem],
    include_closed: bool,
    escalation_tier: CampaignAssignmentEscalationTier | None,
    next_action: CampaignWorkflowNextAction | None,
) -> list[DpmBulkReviewCampaignAssignmentPlanItem]:
    return [
        item
        for item in items
        if _assignment_plan_item_matches(
            item=item,
            include_closed=include_closed,
            escalation_tier=escalation_tier,
            next_action=next_action,
        )
    ]


def _assignment_plan_item_matches(
    *,
    item: DpmBulkReviewCampaignAssignmentPlanItem,
    include_closed: bool,
    escalation_tier: CampaignAssignmentEscalationTier | None,
    next_action: CampaignWorkflowNextAction | None,
) -> bool:
    return all(
        (
            _assignment_plan_closed_filter_matches(item=item, include_closed=include_closed),
            _assignment_plan_escalation_filter_matches(
                item=item,
                escalation_tier=escalation_tier,
            ),
            _assignment_plan_next_action_filter_matches(item=item, next_action=next_action),
        )
    )


def _assignment_plan_closed_filter_matches(
    *,
    item: DpmBulkReviewCampaignAssignmentPlanItem,
    include_closed: bool,
) -> bool:
    if include_closed:
        return True
    return item.workflow_board.board_status != "CLOSED"


def _assignment_plan_escalation_filter_matches(
    *,
    item: DpmBulkReviewCampaignAssignmentPlanItem,
    escalation_tier: CampaignAssignmentEscalationTier | None,
) -> bool:
    if escalation_tier is None:
        return True
    return item.escalation_tier == escalation_tier


def _assignment_plan_next_action_filter_matches(
    *,
    item: DpmBulkReviewCampaignAssignmentPlanItem,
    next_action: CampaignWorkflowNextAction | None,
) -> bool:
    if next_action is None:
        return True
    return item.next_action == next_action


def _assignment_plan_counts(
    items: list[DpmBulkReviewCampaignAssignmentPlanItem],
    field_name: Literal["escalation_tier", "sla_posture"],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, field_name)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _assignment_plan_page_payload(
    *,
    items: list[DpmBulkReviewCampaignAssignmentPlanItem],
    limit: int,
    offset: int,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignAssignmentPlan",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "escalation_tier_counts": _assignment_plan_counts(items, "escalation_tier"),
        "sla_posture_counts": _assignment_plan_counts(items, "sla_posture"),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


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
