from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
)
from src.core.waves.models import DpmWaveSourceRef

CampaignAssignmentActionType = Literal[
    "ASSIGNED",
    "REASSIGNED",
    "ESCALATED",
    "DEESCALATED",
    "RESOLVED",
]
CampaignAssignmentEscalationTier = Literal["NONE", "PM", "OPS", "GOVERNANCE"]
CampaignAssignmentSlaPosture = Literal["ON_TRACK", "ATTENTION", "BREACHED_OR_BLOCKED"]


class DpmBulkReviewCampaignDefinitionAssignmentActionPage(BaseModel):
    product_name: Literal["BulkReviewCampaignDefinitionAssignmentActionPage"] = (
        "BulkReviewCampaignDefinitionAssignmentActionPage"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(description="Campaign definition identifier.")
    campaign_version: str = Field(description="Campaign definition version.")
    assignment_actions: list[DpmBulkReviewCampaignDefinitionAssignmentAction] = Field(
        description="Bounded page of append-only assignment and escalation actions."
    )
    latest_action_type: CampaignAssignmentActionType | None = Field(
        description="Most recent assignment action type in the returned definition."
    )
    current_assigned_actor_ids: list[str] = Field(
        description="Current assigned actors derived from the latest non-resolved action."
    )
    current_escalation_tier: CampaignAssignmentEscalationTier = Field(
        description="Current escalation tier derived from the latest action."
    )
    current_sla_posture: CampaignAssignmentSlaPosture = Field(
        description="Current SLA posture derived from the latest action."
    )
    count: int = Field(description="Number of assignment actions returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


def record_bulk_review_campaign_definition_assignment_action(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    action_type: CampaignAssignmentActionType,
    action_ref: str,
    recorded_by: str,
    action_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    sla_posture: CampaignAssignmentSlaPosture,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef] | None = None,
) -> DpmBulkReviewCampaignDefinition:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTIVE_REQUIRED")
    if not action_ref.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_REQUIRED")
    if not recorded_by.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTOR_REQUIRED")
    if not action_reason.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REASON_REQUIRED")
    if not correlation_id.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_CORRELATION_REQUIRED")
    normalized_actor_ids = sorted({actor.strip() for actor in assigned_actor_ids if actor.strip()})
    if action_type != "RESOLVED" and not normalized_actor_ids:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTORS_REQUIRED")
    if action_type == "RESOLVED" and escalation_tier != "NONE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_RESOLVED_TIER_INVALID")

    action = _build_action(
        definition=definition,
        action_type=action_type,
        action_ref=action_ref.strip(),
        recorded_by=recorded_by.strip(),
        action_reason=action_reason.strip(),
        assigned_actor_ids=normalized_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        correlation_id=correlation_id.strip(),
        source_refs=source_refs or [],
    )
    existing_refs = {existing.action_ref: existing for existing in definition.assignment_actions}
    existing = existing_refs.get(action.action_ref)
    if existing is not None:
        if existing.content_hash == action.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT")

    updated = definition.model_copy(
        update={
            "assignment_actions": [*definition.assignment_actions, action],
            "content_hash": "",
        }
    )
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def build_bulk_review_campaign_definition_assignment_action_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    limit: int = 50,
    offset: int = 0,
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    actions = sorted(
        definition.assignment_actions,
        key=lambda action: action.recorded_at,
        reverse=True,
    )
    page = actions[offset : offset + limit]
    latest = actions[0] if actions else None
    return DpmBulkReviewCampaignDefinitionAssignmentActionPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        assignment_actions=page,
        latest_action_type=latest.action_type if latest else None,
        current_assigned_actor_ids=[]
        if latest is None or latest.action_type == "RESOLVED"
        else latest.assigned_actor_ids,
        current_escalation_tier=latest.escalation_tier if latest else "NONE",
        current_sla_posture=latest.sla_posture if latest else "ON_TRACK",
        count=len(page),
        limit=limit,
        offset=offset,
    )


def _build_action(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    action_type: CampaignAssignmentActionType,
    action_ref: str,
    recorded_by: str,
    action_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    sla_posture: CampaignAssignmentSlaPosture,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionAssignmentAction:
    recorded_at = datetime.now(timezone.utc)
    action_id_seed = "|".join(
        [
            definition.campaign_id,
            definition.campaign_version,
            action_ref,
            action_type,
        ]
    )
    action_id = (
        "brc_assignment_action_" + hashlib.sha256(action_id_seed.encode("utf-8")).hexdigest()[:16]
    )
    payload = {
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "action_id": action_id,
        "action_type": action_type,
        "action_ref": action_ref,
        "recorded_by": recorded_by,
        "action_reason": action_reason,
        "assigned_actor_ids": assigned_actor_ids,
        "escalation_tier": escalation_tier,
        "sla_posture": sla_posture,
        "correlation_id": correlation_id,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }
    content_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return DpmBulkReviewCampaignDefinitionAssignmentAction(
        action_id=action_id,
        action_type=action_type,
        action_ref=action_ref,
        recorded_at=recorded_at,
        recorded_by=recorded_by,
        action_reason=action_reason,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        correlation_id=correlation_id,
        source_refs=source_refs,
        content_hash=content_hash,
    )
