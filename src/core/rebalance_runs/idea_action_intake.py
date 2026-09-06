from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.rebalance_runs.idea_action_intake_authority import (
    IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    IdeaActionIntakePrincipal,
)
from src.core.rebalance_runs.idea_management_action import (
    IdeaManagementAction,
    IdeaManagementActionEvent,
)
from src.core.rebalance_runs.models import DpmWorkflowActionType, DpmWorkflowStatus


class IdeaActionIntakeInvalidIdempotencyKeyError(Exception):
    """Raised when an Idea action-intake idempotency key is empty after normalization."""


class IdeaActionIntakeScopeError(Exception):
    """Raised when trusted local/dev scope does not authorize the requested portfolio."""


IdeaActionIntakeStatus = Literal["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
IdeaActionIntakeSupportabilityStatus = Literal["not_certified"]
IdeaActionIntentType = Literal["REVIEW_FOR_REBALANCE", "CREATE_MANAGEMENT_ACTION_DRAFT"]
IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS = [
    "production_idp_caller_scope_not_certified",
    "rebalance_execution_not_certified",
    "oms_execution_not_certified",
    "client_publication_authority_blocked",
]

IDEA_ACTION_INTAKE_REQUEST_EXAMPLE: dict[str, Any] = {
    "source_system": "lotus-idea",
    "source_product": "lotus-idea:IdeaCandidate:v1",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "idea_candidate_id": "idea_candidate_001",
    "conversion_intent_id": "conversion_intent_001",
    "intent_type": "REVIEW_FOR_REBALANCE",
    "source_refs": [
        {
            "source_system": "lotus-idea",
            "source_type": "IdeaCandidate",
            "source_id": "idea_candidate_001",
            "content_hash": "sha256:abc123",
        }
    ],
}

IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "intake_id": "iai_7a1d2b3c4d5e",
    "intake_status": "ACCEPTED",
    "supportability_status": "not_certified",
    "source_authority": "lotus-idea",
    "action_authority": "lotus-manage",
    "target_product": "lotus-manage:PortfolioActionRegister:v1",
    "route_existence_proven": True,
    "action_receipt_accepted": True,
    "idempotency_replay": False,
    "idempotency_key_hash": "sha256:71d5d5d1fbf0",
    "request_fingerprint": "sha256:a4e9afedc3cb",
    "trusted_scope": {
        "subject": "svc-lotus-idea",
        "role": "SERVICE",
        "tenant_id": "tenant-private-bank-sg",
        "legal_entity_code": "SGPB",
        "portfolio_ids": ["PB_SG_GLOBAL_BAL_001"],
        "correlation_id": "corr-idea-action-001",
        "service_identity": "lotus-idea",
        "capability": IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    },
    "outcome_reason_codes": ["idea_action_created_for_management_review"],
    "action_register_created": True,
    "management_action_id": "ima_70aac20f34d0a83fc85a",
    "management_action_status": "PENDING_REVIEW",
    "source_event_version": 1,
    "outcome_history_route": "/api/v1/rebalance/idea-action-intakes/iai_7a1d2b3c4d5e/outcomes",
    "outcome_history_contract_version": "lotus-manage.idea-action-outcome-history.v1",
    "rebalance_execution_authority_granted": False,
    "order_created": False,
    "client_publication_authorized": False,
    "certification_blockers": IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS,
    "evidence_refs": [
        "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "src/core/rebalance_runs/idea_management_action.py",
        "src/infrastructure/rebalance_runs/idea_management_actions_postgres.py",
    ],
    "received_at": "2026-09-02T01:00:00+00:00",
    "correlation_id": "corr-idea-action-001",
}

IDEA_ACTION_INTAKE_ERROR_EXAMPLE: dict[str, Any] = {
    "type": "about:blank",
    "title": "Validation Error",
    "status": 422,
    "detail": "Idea management action request failed semantic validation.",
    "reasonCode": "IDEA_ACTION_INTAKE_VALIDATION_FAILED",
    "correlationId": "corr-idea-action-001",
    "instance": "/api/v1/rebalance/idea-action-intake",
}


def normalize_idea_action_identifier(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("IDEA_ACTION_IDENTIFIER_REQUIRED")
    return normalized


class IdeaActionSourceRef(BaseModel):
    source_system: Literal["lotus-idea"]
    source_type: str = Field(min_length=1, max_length=160)
    source_id: str = Field(min_length=1, max_length=160)
    content_hash: str | None = Field(default=None, max_length=160)

    @field_validator("source_type", "source_id", "content_hash")
    @classmethod
    def _trim_source_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("IDEA_ACTION_SOURCE_REF_REQUIRED")
        return normalized


class IdeaActionIntakeRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_ACTION_INTAKE_REQUEST_EXAMPLE}}

    source_system: Literal["lotus-idea"]
    source_product: Literal["lotus-idea:IdeaCandidate:v1"]
    portfolio_id: str = Field(
        min_length=1,
        max_length=160,
        description=(
            "Authoritative portfolio scope carried by the Idea conversion intent. Manage "
            "validates it against trusted local/dev caller entitlement before persistence."
        ),
    )
    idea_candidate_id: str = Field(min_length=1, max_length=160)
    conversion_intent_id: str = Field(min_length=1, max_length=160)
    intent_type: IdeaActionIntentType
    source_refs: list[IdeaActionSourceRef] = Field(min_length=1, max_length=16)

    @field_validator("portfolio_id", "idea_candidate_id", "conversion_intent_id")
    @classmethod
    def _trim_required_identifier(cls, value: str) -> str:
        return normalize_idea_action_identifier(value)


class IdeaActionIntakeResponse(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE}}

    intake_id: str
    intake_status: IdeaActionIntakeStatus
    supportability_status: IdeaActionIntakeSupportabilityStatus
    source_authority: Literal["lotus-idea"]
    action_authority: Literal["lotus-manage"]
    target_product: Literal["lotus-manage:PortfolioActionRegister:v1"]
    route_existence_proven: bool
    action_receipt_accepted: bool
    idempotency_replay: bool
    idempotency_key_hash: str
    request_fingerprint: str
    trusted_scope: dict[str, Any]
    outcome_reason_codes: list[str]
    action_register_created: bool
    management_action_id: str | None = None
    management_action_status: DpmWorkflowStatus | None = None
    source_event_version: int | None = Field(default=None, ge=1)
    outcome_history_route: str | None = None
    outcome_history_contract_version: str | None = None
    rebalance_execution_authority_granted: Literal[False]
    order_created: Literal[False]
    client_publication_authorized: Literal[False]
    certification_blockers: list[str]
    evidence_refs: list[str]
    received_at: str
    correlation_id: str


class IdeaManagementActionDecisionRequest(BaseModel):
    workflow_action: DpmWorkflowActionType
    expected_source_event_version: int = Field(ge=1)
    reason_code: str = Field(min_length=1, max_length=120)

    @field_validator("reason_code")
    @classmethod
    def _trim_reason_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("IDEA_MANAGEMENT_ACTION_REASON_CODE_REQUIRED")
        return normalized


class IdeaManagementActionOutcomeHistoryResponse(BaseModel):
    contract_version: Literal["lotus-manage.idea-action-outcome-history.v1"]
    source_authority: Literal["lotus-manage"]
    intake_id: str
    management_action_id: str
    portfolio_id: str
    idea_candidate_id: str
    conversion_intent_id: str
    request_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{12}$")
    status: DpmWorkflowStatus
    source_event_version: int = Field(ge=1)
    events: tuple[IdeaManagementActionEvent, ...]
    rebalance_execution_proven: Literal[False]
    order_execution_proven: Literal[False]
    client_publication_proven: Literal[False]


def assert_idea_action_portfolio_scope(
    request: IdeaActionIntakeRequest,
    *,
    principal: IdeaActionIntakePrincipal,
) -> None:
    if not principal.can_access_portfolio(request.portfolio_id):
        raise IdeaActionIntakeScopeError("IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN")


def idea_action_request_fingerprint(request: IdeaActionIntakeRequest) -> str:
    canonical_payload = json.dumps(
        {
            **request.model_dump(mode="json", exclude_none=False),
            "source_refs": _canonical_source_refs(request.source_refs),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{sha256(canonical_payload.encode()).hexdigest()[:12]}"


def idea_action_intake_id(
    request: IdeaActionIntakeRequest,
    *,
    principal: IdeaActionIntakePrincipal,
) -> str:
    identity = "|".join(
        (
            principal.tenant_id,
            principal.legal_entity_code,
            request.portfolio_id,
            request.idea_candidate_id,
            request.conversion_intent_id,
            request.intent_type,
            idea_action_request_fingerprint(request),
        )
    )
    return f"iai_{sha256(identity.encode()).hexdigest()[:20]}"


def idea_action_idempotency_scope_hash(
    *,
    idempotency_key: str,
    principal: IdeaActionIntakePrincipal,
    portfolio_id: str,
) -> str:
    key_hash = safe_idea_action_idempotency_key_hash(idempotency_key)
    canonical_scope = "|".join(
        (
            key_hash,
            principal.tenant_id,
            principal.legal_entity_code,
            portfolio_id,
            principal.service_identity,
        )
    )
    return f"sha256:{sha256(canonical_scope.encode()).hexdigest()[:24]}"


def safe_idea_action_idempotency_key_hash(idempotency_key: str) -> str:
    normalized = idempotency_key.strip()
    if not normalized:
        raise IdeaActionIntakeInvalidIdempotencyKeyError(
            "IDEA_ACTION_INTAKE_IDEMPOTENCY_KEY_REQUIRED"
        )
    return f"sha256:{sha256(normalized.encode()).hexdigest()[:12]}"


def idea_action_trusted_scope(
    *,
    principal: IdeaActionIntakePrincipal,
    correlation_id: str,
    capability: str = IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
) -> dict[str, Any]:
    metadata = principal.audit_metadata(capability=capability)
    metadata["correlation_id"] = correlation_id
    return metadata


def idea_management_action_history(
    action: IdeaManagementAction,
) -> IdeaManagementActionOutcomeHistoryResponse:
    return IdeaManagementActionOutcomeHistoryResponse(
        contract_version="lotus-manage.idea-action-outcome-history.v1",
        source_authority="lotus-manage",
        intake_id=action.intake_id,
        management_action_id=action.action_id,
        portfolio_id=action.portfolio_id,
        idea_candidate_id=action.idea_candidate_id,
        conversion_intent_id=action.conversion_intent_id,
        request_fingerprint=action.request_fingerprint,
        status=action.status,
        source_event_version=action.source_event_version,
        events=action.events,
        rebalance_execution_proven=False,
        order_execution_proven=False,
        client_publication_proven=False,
    )


def idea_action_received_at(value: datetime | None = None) -> datetime:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("IDEA_ACTION_INTAKE_TIMEZONE_REQUIRED")
    return timestamp.astimezone(timezone.utc)


def _canonical_source_refs(source_refs: list[IdeaActionSourceRef]) -> list[dict[str, Any]]:
    return sorted(
        (source_ref.model_dump(mode="json", exclude_none=False) for source_ref in source_refs),
        key=lambda item: (
            item["source_system"],
            item["source_type"],
            item["source_id"],
            item.get("content_hash") or "",
        ),
    )


__all__ = [
    "IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS",
    "IDEA_ACTION_INTAKE_ERROR_EXAMPLE",
    "IDEA_ACTION_INTAKE_REQUEST_EXAMPLE",
    "IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE",
    "IdeaActionIntakeInvalidIdempotencyKeyError",
    "IdeaActionIntakeRequest",
    "IdeaActionIntakeResponse",
    "IdeaActionIntakeScopeError",
    "IdeaManagementActionDecisionRequest",
    "IdeaManagementActionOutcomeHistoryResponse",
    "assert_idea_action_portfolio_scope",
    "idea_action_idempotency_scope_hash",
    "idea_action_intake_id",
    "idea_action_received_at",
    "idea_action_request_fingerprint",
    "idea_action_trusted_scope",
    "idea_management_action_history",
    "safe_idea_action_idempotency_key_hash",
]
