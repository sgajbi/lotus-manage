from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_approval_inbox import (
    DpmBulkReviewCampaignApprovalInboxItem,
    build_bulk_review_campaign_approval_inbox_item,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_operating_queue import (
    DpmBulkReviewCampaignOperatingQueueItem,
    build_bulk_review_campaign_operating_queue_item,
)
from src.core.waves.campaign_operating_boundaries import (
    CAMPAIGN_WORKFLOW_BOARD_OPERATING_BOUNDARIES,
)


CampaignWorkflowBoardStatus = Literal[
    "READY_FOR_ACTOR",
    "ATTENTION_FOR_ACTOR",
    "CLOSED",
]

CampaignWorkflowNextAction = Literal[
    "LAUNCH_CAMPAIGN",
    "RECORD_APPROVAL_DECISION",
    "REMEDIATE_APPROVAL_EVIDENCE",
    "REFRESH_EXPIRY_OR_AS_OF_DATE",
    "REVIEW_ACTOR_ENTITLEMENT",
    "REVIEW_CAMPAIGN_ATTENTION",
    "NO_ACTION_CLOSED",
]


class DpmBulkReviewCampaignWorkflowBoardItem(BaseModel):
    """Cross-actor campaign workflow row for one persisted bulk-review campaign definition."""

    product_name: Literal["BulkReviewCampaignWorkflowBoardItem"] = (
        "BulkReviewCampaignWorkflowBoardItem"
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
    board_status: CampaignWorkflowBoardStatus = Field(
        description="Bounded cross-actor workflow posture for this campaign definition."
    )
    next_action: CampaignWorkflowNextAction = Field(
        description="Suggested operator action derived from existing queue and approval posture."
    )
    board_reason_codes: list[str] = Field(
        description="Bounded reason codes explaining the workflow-board posture."
    )
    assigned_actor_ids: list[str] = Field(
        description=(
            "Actor ids from campaign entitlement evidence, or the queried actor when no explicit "
            "entitlement list exists. This is routing evidence only, not authorization mutation."
        )
    )
    operating_queue: DpmBulkReviewCampaignOperatingQueueItem = Field(
        description="Existing launch/attention/closed operating queue posture."
    )
    approval_inbox: DpmBulkReviewCampaignApprovalInboxItem = Field(
        description="Existing read-only approval attention posture."
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(CAMPAIGN_WORKFLOW_BOARD_OPERATING_BOUNDARIES),
        description="Unsupported downstream claims the workflow board must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the workflow-board row.")


class DpmBulkReviewCampaignWorkflowBoardPage(BaseModel):
    """Bounded cross-actor workflow board over persisted campaign definitions."""

    product_name: Literal["BulkReviewCampaignWorkflowBoard"] = "BulkReviewCampaignWorkflowBoard"
    product_version: Literal["v1"] = "v1"
    items: list[DpmBulkReviewCampaignWorkflowBoardItem]
    limit: int
    offset: int
    count: int
    status_counts: dict[str, int] = Field(
        description="Workflow-board row counts by board status for the returned page."
    )
    next_action_counts: dict[str, int] = Field(
        description="Workflow-board row counts by derived next action for the returned page."
    )
    content_hash: str = Field(description="Canonical hash over the workflow-board page.")


def build_bulk_review_campaign_workflow_board_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
) -> DpmBulkReviewCampaignWorkflowBoardItem:
    """Compose campaign queue and approval posture into one cross-actor board row."""

    operating_queue = build_bulk_review_campaign_operating_queue_item(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
    )
    approval_inbox = build_bulk_review_campaign_approval_inbox_item(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
    )
    board_status, next_action, reason_codes = _classify_workflow_board_posture(
        operating_queue=operating_queue,
        approval_inbox=approval_inbox,
    )
    assigned_actor_ids = _assigned_actor_ids(definition=definition, actor_id=actor_id)
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignWorkflowBoardItem",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "display_name": definition.display_name,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "board_status": board_status,
        "next_action": next_action,
        "board_reason_codes": reason_codes,
        "assigned_actor_ids": assigned_actor_ids,
        "operating_queue": operating_queue.model_dump(mode="json"),
        "approval_inbox": approval_inbox.model_dump(mode="json"),
        "operating_boundaries": list(CAMPAIGN_WORKFLOW_BOARD_OPERATING_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignWorkflowBoardItem.model_validate(payload)


def build_bulk_review_campaign_workflow_board_page(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
    include_closed: bool,
    board_status: CampaignWorkflowBoardStatus | None,
    next_action: CampaignWorkflowNextAction | None,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignWorkflowBoardPage:
    items = [
        build_bulk_review_campaign_workflow_board_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]
    if not include_closed:
        items = [item for item in items if item.board_status != "CLOSED"]
    if board_status is not None:
        items = [item for item in items if item.board_status == board_status]
    if next_action is not None:
        items = [item for item in items if item.next_action == next_action]

    status_counts: dict[str, int] = {}
    next_action_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.board_status] = status_counts.get(item.board_status, 0) + 1
        next_action_counts[item.next_action] = next_action_counts.get(item.next_action, 0) + 1

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignWorkflowBoard",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "status_counts": status_counts,
        "next_action_counts": next_action_counts,
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignWorkflowBoardPage.model_validate(payload)


def _classify_workflow_board_posture(
    *,
    operating_queue: DpmBulkReviewCampaignOperatingQueueItem,
    approval_inbox: DpmBulkReviewCampaignApprovalInboxItem,
) -> tuple[CampaignWorkflowBoardStatus, CampaignWorkflowNextAction, list[str]]:
    if operating_queue.queue_status == "CLOSED" or approval_inbox.inbox_status == "CLOSED":
        return "CLOSED", "NO_ACTION_CLOSED", ["CAMPAIGN_DEFINITION_CLOSED"]
    if approval_inbox.inbox_status == "ENTITLEMENT_ATTENTION":
        return (
            "ATTENTION_FOR_ACTOR",
            "REVIEW_ACTOR_ENTITLEMENT",
            approval_inbox.inbox_reason_codes,
        )
    if approval_inbox.inbox_status == "APPROVAL_REQUIRED":
        return (
            "ATTENTION_FOR_ACTOR",
            "RECORD_APPROVAL_DECISION",
            approval_inbox.inbox_reason_codes,
        )
    if approval_inbox.inbox_status == "APPROVAL_INCOMPLETE":
        return (
            "ATTENTION_FOR_ACTOR",
            "REMEDIATE_APPROVAL_EVIDENCE",
            approval_inbox.inbox_reason_codes,
        )
    if approval_inbox.inbox_status == "EXPIRY_ATTENTION":
        return (
            "ATTENTION_FOR_ACTOR",
            "REFRESH_EXPIRY_OR_AS_OF_DATE",
            approval_inbox.inbox_reason_codes,
        )
    if operating_queue.queue_status == "READY_TO_LAUNCH":
        return (
            "READY_FOR_ACTOR",
            "LAUNCH_CAMPAIGN",
            operating_queue.queue_reason_codes,
        )
    return (
        "ATTENTION_FOR_ACTOR",
        "REVIEW_CAMPAIGN_ATTENTION",
        operating_queue.queue_reason_codes,
    )


def _assigned_actor_ids(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    actor_id: str | None,
) -> list[str]:
    if definition.governance and definition.governance.entitled_actor_ids:
        return sorted(set(definition.governance.entitled_actor_ids))
    if actor_id:
        return [actor_id]
    return []


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
