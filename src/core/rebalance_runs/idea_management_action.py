from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.core.rebalance_runs.models import DpmWorkflowActionType, DpmWorkflowStatus
from src.core.rebalance_runs.workflow import resolve_workflow_transition


IdeaManagementActionEventType = Literal[
    "INTAKE_ACCEPTED",
    "APPROVE",
    "REJECT",
    "REQUEST_CHANGES",
]


class IdeaManagementActionConflictError(Exception):
    """Raised when a management action mutation conflicts with durable state."""


class IdeaManagementActionNotFoundError(Exception):
    """Raised when a scoped management action cannot be found."""


class IdeaManagementActionEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=80)
    action_id: str = Field(min_length=1, max_length=80)
    source_event_version: int = Field(ge=1)
    event_type: IdeaManagementActionEventType
    previous_status: DpmWorkflowStatus | None
    status: DpmWorkflowStatus
    occurred_at: datetime
    actor_id: str = Field(min_length=1, max_length=160)
    actor_role: str = Field(min_length=1, max_length=80)
    reason_code: str = Field(min_length=1, max_length=120)
    correlation_id: str = Field(min_length=1, max_length=128)
    causation_id: str = Field(min_length=1, max_length=160)

    @field_validator(
        "event_id",
        "action_id",
        "actor_id",
        "actor_role",
        "reason_code",
        "correlation_id",
        "causation_id",
    )
    @classmethod
    def _trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("IDEA_MANAGEMENT_ACTION_EVENT_FIELD_REQUIRED")
        return normalized


class IdeaManagementAction(BaseModel):
    action_id: str = Field(min_length=1, max_length=80)
    intake_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=160)
    legal_entity_code: str = Field(min_length=1, max_length=80)
    portfolio_id: str = Field(min_length=1, max_length=160)
    idea_candidate_id: str = Field(min_length=1, max_length=160)
    conversion_intent_id: str = Field(min_length=1, max_length=160)
    source_product: Literal["lotus-idea:IdeaCandidate:v1"]
    source_refs: tuple[dict[str, str | None], ...] = Field(min_length=1, max_length=16)
    request_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{12}$")
    idempotency_scope_hash: str = Field(pattern=r"^sha256:[0-9a-f]{24}$")
    status: DpmWorkflowStatus
    source_event_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    correlation_id: str = Field(min_length=1, max_length=128)
    causation_id: str = Field(min_length=1, max_length=160)
    events: tuple[IdeaManagementActionEvent, ...] = Field(min_length=1)

    @field_validator(
        "action_id",
        "intake_id",
        "tenant_id",
        "legal_entity_code",
        "portfolio_id",
        "idea_candidate_id",
        "conversion_intent_id",
        "correlation_id",
        "causation_id",
    )
    @classmethod
    def _trim_action_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("IDEA_MANAGEMENT_ACTION_FIELD_REQUIRED")
        return normalized


def create_idea_management_action(
    *,
    intake_id: str,
    tenant_id: str,
    legal_entity_code: str,
    portfolio_id: str,
    idea_candidate_id: str,
    conversion_intent_id: str,
    source_refs: tuple[dict[str, str | None], ...],
    request_fingerprint: str,
    idempotency_scope_hash: str,
    actor_id: str,
    actor_role: str,
    correlation_id: str,
    created_at: datetime | None = None,
) -> IdeaManagementAction:
    timestamp = _utc(created_at or datetime.now(timezone.utc))
    action_id = _management_action_id(
        tenant_id=tenant_id,
        legal_entity_code=legal_entity_code,
        portfolio_id=portfolio_id,
        conversion_intent_id=conversion_intent_id,
    )
    event = IdeaManagementActionEvent(
        event_id=_event_id(action_id=action_id, source_event_version=1, event_type="INTAKE_ACCEPTED"),
        action_id=action_id,
        source_event_version=1,
        event_type="INTAKE_ACCEPTED",
        previous_status=None,
        status="PENDING_REVIEW",
        occurred_at=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        reason_code="idea_conversion_intent_accepted_for_management_review",
        correlation_id=correlation_id,
        causation_id=conversion_intent_id,
    )
    return IdeaManagementAction(
        action_id=action_id,
        intake_id=intake_id,
        tenant_id=tenant_id,
        legal_entity_code=legal_entity_code,
        portfolio_id=portfolio_id,
        idea_candidate_id=idea_candidate_id,
        conversion_intent_id=conversion_intent_id,
        source_product="lotus-idea:IdeaCandidate:v1",
        source_refs=source_refs,
        request_fingerprint=request_fingerprint,
        idempotency_scope_hash=idempotency_scope_hash,
        status="PENDING_REVIEW",
        source_event_version=1,
        created_at=timestamp,
        updated_at=timestamp,
        correlation_id=correlation_id,
        causation_id=conversion_intent_id,
        events=(event,),
    )


def record_idea_management_review_decision(
    action: IdeaManagementAction,
    *,
    workflow_action: DpmWorkflowActionType,
    expected_source_event_version: int,
    actor_id: str,
    actor_role: str,
    reason_code: str,
    correlation_id: str,
    decided_at: datetime | None = None,
) -> IdeaManagementAction:
    if expected_source_event_version != action.source_event_version:
        raise IdeaManagementActionConflictError(
            "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT"
        )
    next_status = resolve_workflow_transition(
        current_status=action.status,
        action=workflow_action,
    )
    if next_status is None:
        raise IdeaManagementActionConflictError(
            "IDEA_MANAGEMENT_ACTION_INVALID_WORKFLOW_TRANSITION"
        )
    next_version = action.source_event_version + 1
    timestamp = _utc(decided_at or datetime.now(timezone.utc))
    event = IdeaManagementActionEvent(
        event_id=_event_id(
            action_id=action.action_id,
            source_event_version=next_version,
            event_type=workflow_action,
        ),
        action_id=action.action_id,
        source_event_version=next_version,
        event_type=workflow_action,
        previous_status=action.status,
        status=next_status,
        occurred_at=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        reason_code=reason_code,
        correlation_id=correlation_id,
        causation_id=action.events[-1].event_id,
    )
    return action.model_copy(
        update={
            "status": next_status,
            "source_event_version": next_version,
            "updated_at": timestamp,
            "correlation_id": correlation_id,
            "causation_id": event.causation_id,
            "events": (*action.events, event),
        }
    )


def _management_action_id(
    *,
    tenant_id: str,
    legal_entity_code: str,
    portfolio_id: str,
    conversion_intent_id: str,
) -> str:
    identity = "|".join((tenant_id, legal_entity_code, portfolio_id, conversion_intent_id))
    return f"ima_{sha256(identity.encode()).hexdigest()[:20]}"


def _event_id(
    *,
    action_id: str,
    source_event_version: int,
    event_type: IdeaManagementActionEventType,
) -> str:
    identity = f"{action_id}|{source_event_version}|{event_type}"
    return f"imae_{sha256(identity.encode()).hexdigest()[:20]}"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("IDEA_MANAGEMENT_ACTION_TIMEZONE_REQUIRED")
    return value.astimezone(timezone.utc)


__all__ = [
    "IdeaManagementAction",
    "IdeaManagementActionConflictError",
    "IdeaManagementActionEvent",
    "IdeaManagementActionEventType",
    "IdeaManagementActionNotFoundError",
    "create_idea_management_action",
    "record_idea_management_review_decision",
]
