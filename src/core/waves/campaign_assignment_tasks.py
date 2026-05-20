from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
)
from src.core.waves.models import DpmWaveSourceRef

CampaignAssignmentTaskType = Literal[
    "ASSIGNMENT",
    "APPROVAL_REMEDIATION",
    "ENTITLEMENT_REVIEW",
    "EXPIRY_REVIEW",
    "ESCALATION",
]
CampaignAssignmentTaskStatus = Literal[
    "OPEN",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "BLOCKED",
    "RESOLVED",
    "CANCELLED",
]
CampaignAssignmentTaskTransitionType = Literal[
    "OPENED",
    "ACKNOWLEDGED",
    "STARTED",
    "BLOCKED",
    "UNBLOCKED",
    "RESOLVED",
    "CANCELLED",
    "REASSIGNED",
    "ESCALATED",
    "DUE_DATE_CHANGED",
]
CampaignAssignmentEscalationTier = Literal["NONE", "PM", "OPS", "GOVERNANCE"]
CampaignAssignmentSlaPosture = Literal["ON_TRACK", "ATTENTION", "BREACHED_OR_BLOCKED"]

_CLOSED_STATUSES = {"RESOLVED", "CANCELLED"}
_STATUS_TRANSITIONS: dict[
    CampaignAssignmentTaskTransitionType, tuple[set[str], CampaignAssignmentTaskStatus]
] = {
    "ACKNOWLEDGED": ({"OPEN"}, "ACKNOWLEDGED"),
    "STARTED": ({"OPEN", "ACKNOWLEDGED", "BLOCKED"}, "IN_PROGRESS"),
    "BLOCKED": ({"OPEN", "ACKNOWLEDGED", "IN_PROGRESS"}, "BLOCKED"),
    "UNBLOCKED": ({"BLOCKED"}, "IN_PROGRESS"),
    "RESOLVED": ({"OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "BLOCKED"}, "RESOLVED"),
    "CANCELLED": ({"OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "BLOCKED"}, "CANCELLED"),
}


class DpmBulkReviewCampaignDefinitionAssignmentTaskPage(BaseModel):
    product_name: Literal["BulkReviewCampaignDefinitionAssignmentTaskPage"] = (
        "BulkReviewCampaignDefinitionAssignmentTaskPage"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(description="Campaign definition identifier.")
    campaign_version: str = Field(description="Campaign definition version.")
    assignment_tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask] = Field(
        description="Bounded page of controlled assignment and escalation tasks."
    )
    status_counts: dict[str, int] = Field(description="Task count by current status.")
    escalation_tier_counts: dict[str, int] = Field(description="Task count by escalation tier.")
    sla_posture_counts: dict[str, int] = Field(description="Task count by SLA posture.")
    open_task_count: int = Field(description="Number of non-closed tasks in the definition.")
    count: int = Field(description="Number of tasks returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


def open_bulk_review_campaign_definition_assignment_task(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task_ref: str,
    task_type: CampaignAssignmentTaskType,
    opened_by: str,
    task_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    sla_posture: CampaignAssignmentSlaPosture,
    correlation_id: str,
    due_at: datetime | None = None,
    source_refs: list[DpmWaveSourceRef] | None = None,
) -> DpmBulkReviewCampaignDefinition:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTIVE_REQUIRED")
    normalized_ref = _required_text(task_ref, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_REQUIRED")
    normalized_opened_by = _required_text(
        opened_by, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTOR_REQUIRED"
    )
    normalized_reason = _required_text(
        task_reason, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REASON_REQUIRED"
    )
    normalized_correlation = _required_text(
        correlation_id, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CORRELATION_REQUIRED"
    )
    normalized_actor_ids = _normalize_actor_ids(assigned_actor_ids)
    if not normalized_actor_ids:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED")

    task = _build_task(
        definition=definition,
        task_ref=normalized_ref,
        task_type=task_type,
        opened_by=normalized_opened_by,
        task_reason=normalized_reason,
        assigned_actor_ids=normalized_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        due_at=due_at,
        correlation_id=normalized_correlation,
        source_refs=source_refs or [],
    )
    existing_by_ref = {existing.task_ref: existing for existing in definition.assignment_tasks}
    existing = existing_by_ref.get(task.task_ref)
    if existing is not None:
        if existing.content_hash == task.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT")

    updated = definition.model_copy(
        update={
            "assignment_tasks": [*definition.assignment_tasks, task],
            "content_hash": "",
        }
    )
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def transition_bulk_review_campaign_definition_assignment_task(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task_ref: str,
    transition_type: CampaignAssignmentTaskTransitionType,
    transition_ref: str,
    transitioned_by: str,
    transition_reason: str,
    correlation_id: str,
    assigned_actor_ids: list[str] | None = None,
    escalation_tier: CampaignAssignmentEscalationTier | None = None,
    sla_posture: CampaignAssignmentSlaPosture | None = None,
    due_at: datetime | None = None,
    source_refs: list[DpmWaveSourceRef] | None = None,
) -> DpmBulkReviewCampaignDefinition:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ACTIVE_REQUIRED")
    normalized_ref = _required_text(task_ref, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_REQUIRED")
    normalized_transition_ref = _required_text(
        transition_ref, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_REQUIRED"
    )
    normalized_transitioned_by = _required_text(
        transitioned_by, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_ACTOR_REQUIRED"
    )
    normalized_reason = _required_text(
        transition_reason, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REASON_REQUIRED"
    )
    normalized_correlation = _required_text(
        correlation_id, "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_CORRELATION_REQUIRED"
    )

    task_index = next(
        (
            index
            for index, candidate in enumerate(definition.assignment_tasks)
            if candidate.task_ref == normalized_ref
        ),
        None,
    )
    if task_index is None:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND")
    task = definition.assignment_tasks[task_index]
    existing_by_ref = {transition.transition_ref: transition for transition in task.transitions}
    existing = existing_by_ref.get(normalized_transition_ref)
    if existing is not None:
        if _transition_matches_request(
            transition=existing,
            transition_type=transition_type,
            transitioned_by=normalized_transitioned_by,
            transition_reason=normalized_reason,
            correlation_id=normalized_correlation,
            assigned_actor_ids=assigned_actor_ids,
            escalation_tier=escalation_tier,
            sla_posture=sla_posture,
            due_at=due_at,
            source_refs=source_refs or [],
        ):
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT")
    replacement = _transitioned_task(
        task=task,
        transition_type=transition_type,
        transition_ref=normalized_transition_ref,
        transitioned_by=normalized_transitioned_by,
        transition_reason=normalized_reason,
        correlation_id=normalized_correlation,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        due_at=due_at,
        source_refs=source_refs or [],
    )

    tasks = list(definition.assignment_tasks)
    tasks[task_index] = replacement
    updated = definition.model_copy(update={"assignment_tasks": tasks, "content_hash": ""})
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def build_bulk_review_campaign_definition_assignment_task_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    status_filter: CampaignAssignmentTaskStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    tasks = sorted(
        definition.assignment_tasks,
        key=lambda task: task.opened_at,
        reverse=True,
    )
    if status_filter is not None:
        tasks = [task for task in tasks if task.status == status_filter]
    page = tasks[offset : offset + limit]
    return DpmBulkReviewCampaignDefinitionAssignmentTaskPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        assignment_tasks=page,
        status_counts=_count_by(definition.assignment_tasks, "status"),
        escalation_tier_counts=_count_by(definition.assignment_tasks, "escalation_tier"),
        sla_posture_counts=_count_by(definition.assignment_tasks, "sla_posture"),
        open_task_count=sum(
            1 for task in definition.assignment_tasks if task.status not in _CLOSED_STATUSES
        ),
        count=len(page),
        limit=limit,
        offset=offset,
    )


def _build_task(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task_ref: str,
    task_type: CampaignAssignmentTaskType,
    opened_by: str,
    task_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    sla_posture: CampaignAssignmentSlaPosture,
    due_at: datetime | None,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionAssignmentTask:
    opened_at = datetime.now(timezone.utc)
    task_id = _task_id(definition=definition, task_ref=task_ref)
    transition = _build_transition(
        definition=definition,
        task_id=task_id,
        transition_type="OPENED",
        transition_ref=f"{task_ref}:opened",
        transitioned_by=opened_by,
        from_status=None,
        to_status="OPEN",
        transition_reason=task_reason,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        due_at=due_at,
        correlation_id=correlation_id,
        source_refs=source_refs,
    )
    task = DpmBulkReviewCampaignDefinitionAssignmentTask(
        task_id=task_id,
        task_ref=task_ref,
        task_type=task_type,
        status="OPEN",
        opened_at=opened_at,
        opened_by=opened_by,
        task_reason=task_reason,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        due_at=due_at,
        correlation_id=correlation_id,
        source_refs=source_refs,
        transitions=[transition],
        content_hash="",
    )
    return task.model_copy(update={"content_hash": _task_hash(task)})


def _transitioned_task(
    *,
    task: DpmBulkReviewCampaignDefinitionAssignmentTask,
    transition_type: CampaignAssignmentTaskTransitionType,
    transition_ref: str,
    transitioned_by: str,
    transition_reason: str,
    correlation_id: str,
    assigned_actor_ids: list[str] | None,
    escalation_tier: CampaignAssignmentEscalationTier | None,
    sla_posture: CampaignAssignmentSlaPosture | None,
    due_at: datetime | None,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionAssignmentTask:
    if transition_type == "OPENED":
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_OPENED_TRANSITION_FORBIDDEN")
    if task.status in _CLOSED_STATUSES:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_CLOSED_TRANSITION_FORBIDDEN")
    next_status = _next_status(task.status, transition_type)
    next_assignees = (
        _normalize_actor_ids(assigned_actor_ids)
        if assigned_actor_ids is not None
        else task.assigned_actor_ids
    )
    next_tier = escalation_tier or task.escalation_tier
    next_sla = sla_posture or task.sla_posture
    next_due_at = due_at if due_at is not None else task.due_at
    if next_status not in _CLOSED_STATUSES and not next_assignees:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED")
    if transition_type in {"REASSIGNED", "ESCALATED"} and assigned_actor_ids is None:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_ASSIGNEES_REQUIRED")
    if transition_type == "DUE_DATE_CHANGED" and due_at is None:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_DUE_AT_REQUIRED")
    transition = _build_transition(
        definition=None,
        task_id=task.task_id,
        transition_type=transition_type,
        transition_ref=transition_ref,
        transitioned_by=transitioned_by,
        from_status=task.status,
        to_status=next_status,
        transition_reason=transition_reason,
        assigned_actor_ids=next_assignees,
        escalation_tier=next_tier,
        sla_posture=next_sla,
        due_at=next_due_at,
        correlation_id=correlation_id,
        source_refs=source_refs,
    )
    updated = task.model_copy(
        update={
            "status": next_status,
            "assigned_actor_ids": next_assignees,
            "escalation_tier": next_tier,
            "sla_posture": next_sla,
            "due_at": next_due_at,
            "transitions": [*task.transitions, transition],
            "content_hash": "",
        }
    )
    return updated.model_copy(update={"content_hash": _task_hash(updated)})


def _next_status(
    status: CampaignAssignmentTaskStatus,
    transition_type: CampaignAssignmentTaskTransitionType,
) -> CampaignAssignmentTaskStatus:
    if transition_type in {"REASSIGNED", "ESCALATED", "DUE_DATE_CHANGED"}:
        return status
    allowed, next_status = _STATUS_TRANSITIONS[transition_type]
    if status not in allowed:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_INVALID")
    return next_status


def _build_transition(
    *,
    definition: DpmBulkReviewCampaignDefinition | None,
    task_id: str,
    transition_type: CampaignAssignmentTaskTransitionType,
    transition_ref: str,
    transitioned_by: str,
    from_status: CampaignAssignmentTaskStatus | None,
    to_status: CampaignAssignmentTaskStatus,
    transition_reason: str,
    assigned_actor_ids: list[str],
    escalation_tier: CampaignAssignmentEscalationTier,
    sla_posture: CampaignAssignmentSlaPosture,
    due_at: datetime | None,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskTransition:
    transition_id_seed = "|".join(
        [
            definition.campaign_id if definition else task_id,
            definition.campaign_version if definition else "",
            task_id,
            transition_ref,
            transition_type,
        ]
    )
    transition_id = (
        "brc_assignment_task_transition_"
        + hashlib.sha256(transition_id_seed.encode("utf-8")).hexdigest()[:16]
    )
    payload = {
        "task_id": task_id,
        "transition_id": transition_id,
        "transition_type": transition_type,
        "transition_ref": transition_ref,
        "transitioned_by": transitioned_by,
        "from_status": from_status,
        "to_status": to_status,
        "transition_reason": transition_reason,
        "assigned_actor_ids": assigned_actor_ids,
        "escalation_tier": escalation_tier,
        "sla_posture": sla_posture,
        "due_at": due_at.isoformat() if due_at else None,
        "correlation_id": correlation_id,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }
    content_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return DpmBulkReviewCampaignDefinitionAssignmentTaskTransition(
        transition_id=transition_id,
        transition_type=transition_type,
        transition_ref=transition_ref,
        transitioned_by=transitioned_by,
        from_status=from_status,
        to_status=to_status,
        transition_reason=transition_reason,
        assigned_actor_ids=assigned_actor_ids,
        escalation_tier=escalation_tier,
        sla_posture=sla_posture,
        due_at=due_at,
        correlation_id=correlation_id,
        source_refs=source_refs,
        content_hash=content_hash,
    )


def _task_id(*, definition: DpmBulkReviewCampaignDefinition, task_ref: str) -> str:
    seed = "|".join([definition.campaign_id, definition.campaign_version, task_ref])
    return "brc_assignment_task_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _task_hash(task: DpmBulkReviewCampaignDefinitionAssignmentTask) -> str:
    payload = task.model_dump(mode="json")
    payload["content_hash"] = ""
    payload["opened_at"] = ""
    for transition in payload["transitions"]:
        transition["transitioned_at"] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_actor_ids(actor_ids: list[str] | None) -> list[str]:
    return sorted({actor.strip() for actor in actor_ids or [] if actor.strip()})


def _required_text(value: str, reason_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(reason_code)
    return normalized


def _count_by(
    tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask],
    field_name: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        key = str(getattr(task, field_name))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _transition_matches_request(
    *,
    transition: DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
    transition_type: CampaignAssignmentTaskTransitionType,
    transitioned_by: str,
    transition_reason: str,
    correlation_id: str,
    assigned_actor_ids: list[str] | None,
    escalation_tier: CampaignAssignmentEscalationTier | None,
    sla_posture: CampaignAssignmentSlaPosture | None,
    due_at: datetime | None,
    source_refs: list[DpmWaveSourceRef],
) -> bool:
    if transition.transition_type != transition_type:
        return False
    if transition.transitioned_by != transitioned_by:
        return False
    if transition.transition_reason != transition_reason:
        return False
    if transition.correlation_id != correlation_id:
        return False
    if assigned_actor_ids is not None and transition.assigned_actor_ids != _normalize_actor_ids(
        assigned_actor_ids
    ):
        return False
    if escalation_tier is not None and transition.escalation_tier != escalation_tier:
        return False
    if sla_posture is not None and transition.sla_posture != sla_posture:
        return False
    if due_at is not None and transition.due_at != due_at:
        return False
    return [ref.model_dump(mode="json") for ref in transition.source_refs] == [
        ref.model_dump(mode="json") for ref in source_refs
    ]
