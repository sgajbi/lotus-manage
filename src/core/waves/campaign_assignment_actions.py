from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.waves.campaign_actor_entitlements import validate_campaign_command_actor_entitlement
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
)
from src.core.waves.models import DpmWaveSourceRef
from src.core.waves.campaign_page_validation import validate_page_count

CampaignAssignmentActionType = Literal[
    "ASSIGNED",
    "REASSIGNED",
    "ESCALATED",
    "DEESCALATED",
    "RESOLVED",
]
CampaignAssignmentEscalationTier = Literal["NONE", "PM", "OPS", "GOVERNANCE"]
CampaignAssignmentSlaPosture = Literal["ON_TRACK", "ATTENTION", "BREACHED_OR_BLOCKED"]


class _AssignmentActionRequest(BaseModel):
    action_ref: str
    recorded_by: str
    action_reason: str
    assigned_actor_ids: list[str]
    correlation_id: str


@dataclass(frozen=True)
class _AssignmentActionPageState:
    latest_action_type: CampaignAssignmentActionType | None
    current_assigned_actor_ids: list[str]
    current_escalation_tier: CampaignAssignmentEscalationTier
    current_sla_posture: CampaignAssignmentSlaPosture


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
    count: int = Field(ge=0, description="Number of assignment actions returned.")
    limit: int = Field(ge=1, description="Requested page size.")
    offset: int = Field(ge=0, description="Requested page offset.")

    @model_validator(mode="after")
    def validate_page_metadata(self) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
        validate_page_count(count=self.count, item_count=len(self.assignment_actions))
        return self


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
    _validate_active_assignment_action_definition(definition)
    request = _assignment_action_request(
        action_type=action_type,
        action_ref=action_ref,
        recorded_by=recorded_by,
        action_reason=action_reason,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        correlation_id=correlation_id,
    )
    validate_campaign_command_actor_entitlement(
        definition=definition,
        actor_id=request.recorded_by,
    )

    action = _build_action(
        definition=definition,
        action_type=action_type,
        action_ref=request.action_ref,
        recorded_by=request.recorded_by,
        action_reason=request.action_reason,
        assigned_actor_ids=request.assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        correlation_id=request.correlation_id,
        source_refs=source_refs or [],
    )
    replay = _assignment_action_replay_result(definition=definition, action=action)
    if replay is not None:
        return replay

    updated = definition.model_copy(
        update={
            "assignment_actions": [*definition.assignment_actions, action],
            "content_hash": "",
        }
    )
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def _validate_active_assignment_action_definition(
    definition: DpmBulkReviewCampaignDefinition,
) -> None:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTIVE_REQUIRED")


def _assignment_action_request(
    *,
    action_type: CampaignAssignmentActionType,
    action_ref: str,
    recorded_by: str,
    action_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    correlation_id: str,
) -> _AssignmentActionRequest:
    normalized_ref = _required_text(
        action_ref,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_REQUIRED",
    )
    normalized_recorded_by = _required_text(
        recorded_by,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTOR_REQUIRED",
    )
    normalized_reason = _required_text(
        action_reason,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REASON_REQUIRED",
    )
    normalized_correlation = _required_text(
        correlation_id,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_CORRELATION_REQUIRED",
    )
    normalized_actor_ids = _normalize_actor_ids(assigned_actor_ids)
    if action_type != "RESOLVED" and not normalized_actor_ids:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_ACTORS_REQUIRED")
    if action_type == "RESOLVED" and escalation_tier != "NONE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_RESOLVED_TIER_INVALID")

    return _AssignmentActionRequest(
        action_ref=normalized_ref,
        recorded_by=normalized_recorded_by,
        action_reason=normalized_reason,
        assigned_actor_ids=normalized_actor_ids,
        correlation_id=normalized_correlation,
    )


def _assignment_action_replay_result(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    action: DpmBulkReviewCampaignDefinitionAssignmentAction,
) -> DpmBulkReviewCampaignDefinition | None:
    existing_refs = {existing.action_ref: existing for existing in definition.assignment_actions}
    existing = existing_refs.get(action.action_ref)
    if existing is None:
        return None
    if existing.content_hash == action.content_hash:
        return definition
    raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT")


def build_bulk_review_campaign_definition_assignment_action_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    limit: int = 50,
    offset: int = 0,
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    actions = _sorted_assignment_actions(definition)
    page = actions[offset : offset + limit]
    state = _assignment_action_page_state(actions)
    return DpmBulkReviewCampaignDefinitionAssignmentActionPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        assignment_actions=page,
        latest_action_type=state.latest_action_type,
        current_assigned_actor_ids=state.current_assigned_actor_ids,
        current_escalation_tier=state.current_escalation_tier,
        current_sla_posture=state.current_sla_posture,
        count=len(page),
        limit=limit,
        offset=offset,
    )


def _sorted_assignment_actions(
    definition: DpmBulkReviewCampaignDefinition,
) -> list[DpmBulkReviewCampaignDefinitionAssignmentAction]:
    return sorted(
        definition.assignment_actions,
        key=lambda action: action.recorded_at,
        reverse=True,
    )


def _assignment_action_page_state(
    actions: list[DpmBulkReviewCampaignDefinitionAssignmentAction],
) -> _AssignmentActionPageState:
    latest = actions[0] if actions else None
    if latest is None:
        return _AssignmentActionPageState(
            latest_action_type=None,
            current_assigned_actor_ids=[],
            current_escalation_tier="NONE",
            current_sla_posture="ON_TRACK",
        )
    return _AssignmentActionPageState(
        latest_action_type=latest.action_type,
        current_assigned_actor_ids=[]
        if latest.action_type == "RESOLVED"
        else latest.assigned_actor_ids,
        current_escalation_tier=latest.escalation_tier,
        current_sla_posture=latest.sla_posture,
    )


def _required_text(value: str, reason_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(reason_code)
    return normalized


def _normalize_actor_ids(actor_ids: list[str]) -> list[str]:
    return sorted({actor.strip() for actor in actor_ids if actor.strip()})


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
