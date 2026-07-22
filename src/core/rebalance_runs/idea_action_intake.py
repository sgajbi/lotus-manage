from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.rebalance_runs.idea_action_intake_authority import (
    IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    IdeaActionIntakePrincipal,
)


class IdeaActionIntakeIdempotencyConflictError(Exception):
    """Raised when an Idea action-intake idempotency key is reused for a different request."""


IdeaActionIntakeStatus = Literal["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
IdeaActionIntakeSupportabilityStatus = Literal["not_certified"]
IdeaActionIntentType = Literal["REVIEW_FOR_REBALANCE", "CREATE_MANAGEMENT_ACTION_DRAFT"]
IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS = [
    "rebalance_execution_authority_remains_lotus_manage",
    "action_register_persistence_not_certified",
    "oms_execution_not_certified",
    "client_publication_authority_blocked",
]

IDEA_ACTION_INTAKE_REQUEST_EXAMPLE: dict[str, Any] = {
    "source_system": "lotus-idea",
    "source_product": "lotus-idea:IdeaCandidate:v1",
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
        "correlation_id": "corr-idea-action-001",
        "service_identity": "lotus-idea",
        "capability": IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    },
    "outcome_reason_codes": ["idea_action_intake_receipt_accepted"],
    "action_register_created": False,
    "rebalance_execution_authority_granted": False,
    "order_created": False,
    "client_publication_authorized": False,
    "certification_blockers": IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS,
    "evidence_refs": [
        "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "src/api/routers/rebalance_runs_idea_action_intake_routes.py",
        "src/core/rebalance_runs/idea_action_intake.py",
    ],
    "received_at": "2026-06-21T10:10:00+00:00",
    "correlation_id": "corr-idea-action-001",
}

IDEA_ACTION_INTAKE_ERROR_EXAMPLE: dict[str, Any] = {
    "detail": "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
}


class IdeaActionSourceRef(BaseModel):
    source_system: Literal["lotus-idea"] = Field(
        description="Source system that owns the referenced idea evidence.",
        examples=["lotus-idea"],
    )
    source_type: str = Field(
        min_length=1,
        description="Source-owned evidence type or product name.",
        examples=["IdeaCandidate"],
    )
    source_id: str = Field(
        min_length=1,
        description="Source-owned identifier; no portfolio, account, or client identifier required.",
        examples=["idea_candidate_001"],
    )
    content_hash: str | None = Field(
        default=None,
        max_length=160,
        description="Optional source-owned content hash for replay and lineage checks.",
        examples=["sha256:abc123"],
    )

    @field_validator("source_type", "source_id", "content_hash")
    @classmethod
    def _trim_source_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("IDEA_ACTION_SOURCE_REF_REQUIRED")
        return trimmed


class IdeaActionIntakeRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_ACTION_INTAKE_REQUEST_EXAMPLE}}

    source_system: Literal["lotus-idea"] = Field(
        description="Producer system submitting the reviewed opportunity handoff.",
        examples=["lotus-idea"],
    )
    source_product: Literal["lotus-idea:IdeaCandidate:v1"] = Field(
        description="Source product represented by the handoff.",
        examples=["lotus-idea:IdeaCandidate:v1"],
    )
    idea_candidate_id: str = Field(
        min_length=1,
        max_length=160,
        description="lotus-idea candidate identifier; Manage does not infer portfolio facts from it.",
        examples=["idea_candidate_001"],
    )
    conversion_intent_id: str = Field(
        min_length=1,
        max_length=160,
        description="lotus-idea conversion intent identifier used for idempotent handoff tracking.",
        examples=["conversion_intent_001"],
    )
    intent_type: IdeaActionIntentType = Field(
        description=(
            "Requested management-side intake posture. This route records only the handoff "
            "foundation and does not create an action register row or execution order."
        ),
        examples=["REVIEW_FOR_REBALANCE"],
    )
    source_refs: list[IdeaActionSourceRef] = Field(
        min_length=1,
        max_length=16,
        description="Source-safe idea evidence references supplied by lotus-idea.",
    )

    @field_validator("idea_candidate_id", "conversion_intent_id")
    @classmethod
    def _trim_required_identifier(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("IDEA_ACTION_IDENTIFIER_REQUIRED")
        return trimmed


class IdeaActionIntakeResponse(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE}}

    intake_id: str = Field(
        description="Deterministic source-safe intake identifier derived from source handoff fields.",
        examples=["iai_7a1d2b3c4d5e"],
    )
    intake_status: IdeaActionIntakeStatus = Field(
        description="Bounded action-intake receipt status; not a management action or execution status.",
        examples=["ACCEPTED"],
    )
    supportability_status: IdeaActionIntakeSupportabilityStatus = Field(
        description="Certification posture for this action-intake receipt.",
        examples=["not_certified"],
    )
    source_authority: Literal["lotus-idea"] = Field(
        description="Source authority for candidate and conversion intent evidence.",
        examples=["lotus-idea"],
    )
    action_authority: Literal["lotus-manage"] = Field(
        description="Management action authority retained by lotus-manage.",
        examples=["lotus-manage"],
    )
    target_product: Literal["lotus-manage:PortfolioActionRegister:v1"] = Field(
        description="Manage-owned product that future certified realization may update.",
        examples=["lotus-manage:PortfolioActionRegister:v1"],
    )
    route_existence_proven: bool = Field(
        description="True because this route exists and is covered by contract tests.",
        examples=[True],
    )
    action_receipt_accepted: bool = Field(
        description=(
            "True only when Manage accepted the handoff into its bounded action-intake receipt "
            "layer. This is not action-register persistence."
        ),
        examples=[True],
    )
    idempotency_replay: bool = Field(
        description="True when the response is a safe replay for the same idempotency key/request.",
        examples=[False],
    )
    idempotency_key_hash: str = Field(
        description="Hashed idempotency key reference; raw idempotency keys are not echoed.",
        examples=["sha256:71d5d5d1fbf0"],
    )
    request_fingerprint: str = Field(
        description="Source-safe request fingerprint used for idempotency conflict detection.",
        examples=["sha256:a4e9afedc3cb"],
    )
    trusted_scope: dict[str, Any] = Field(
        description=(
            "Bounded trusted principal scope derived from local/dev headers. Production IdP "
            "integration remains external to this route until available."
        ),
    )
    outcome_reason_codes: list[str] = Field(
        description="Machine-readable outcome reasons for accepted, replayed, or rejected intake.",
        examples=[["idea_action_intake_receipt_accepted"]],
    )
    action_register_created: bool = Field(
        description="False until a later certified management action realization slice persists one.",
        examples=[False],
    )
    rebalance_execution_authority_granted: bool = Field(
        description="False; this route does not approve, create, route, or execute rebalance orders.",
        examples=[False],
    )
    order_created: bool = Field(
        description="False; no order, OMS instruction, fill, or settlement evidence is created.",
        examples=[False],
    )
    client_publication_authorized: bool = Field(
        description="False; this route does not authorize client communication or publication.",
        examples=[False],
    )
    certification_blockers: list[str] = Field(
        description="Remaining blockers before this route can support certified realization.",
        examples=[IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS],
    )
    evidence_refs: list[str] = Field(
        description="Implementation and contract evidence references for the action-intake receipt.",
    )
    received_at: str = Field(
        description="UTC timestamp when the handoff envelope was acknowledged.",
        examples=["2026-06-21T10:10:00+00:00"],
    )
    correlation_id: str = Field(
        description="Caller or generated correlation id for source-safe operational tracing.",
        examples=["corr-idea-action-001"],
    )


def acknowledge_idea_action_intake(
    request: IdeaActionIntakeRequest,
    *,
    correlation_id: str,
    idempotency_key: str = "domain-determinism-only",
    principal: IdeaActionIntakePrincipal | None = None,
    received_at: datetime | None = None,
) -> IdeaActionIntakeResponse:
    timestamp = received_at or datetime.now(timezone.utc)
    source_refs_fingerprint = _source_refs_fingerprint(request.source_refs)
    request_fingerprint = _request_fingerprint(
        request,
        source_refs_fingerprint=source_refs_fingerprint,
    )
    intake_id = _intake_id(
        idea_candidate_id=request.idea_candidate_id,
        conversion_intent_id=request.conversion_intent_id,
        intent_type=request.intent_type,
        source_refs_fingerprint=source_refs_fingerprint,
    )
    accepted = request.intent_type == "REVIEW_FOR_REBALANCE"
    return IdeaActionIntakeResponse(
        intake_id=intake_id,
        intake_status="ACCEPTED" if accepted else "REJECTED",
        supportability_status="not_certified",
        source_authority="lotus-idea",
        action_authority="lotus-manage",
        target_product="lotus-manage:PortfolioActionRegister:v1",
        route_existence_proven=True,
        action_receipt_accepted=accepted,
        idempotency_replay=False,
        idempotency_key_hash=_safe_key_hash(idempotency_key),
        request_fingerprint=request_fingerprint,
        trusted_scope=_trusted_scope(principal=principal, correlation_id=correlation_id),
        outcome_reason_codes=_outcome_reason_codes(request),
        action_register_created=False,
        rebalance_execution_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        certification_blockers=list(IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS),
        evidence_refs=[
            "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
            "src/api/routers/rebalance_runs_idea_action_intake_routes.py",
            "src/core/rebalance_runs/idea_action_intake.py",
        ],
        received_at=timestamp.isoformat(),
        correlation_id=correlation_id,
    )


def process_idea_action_intake(
    request: IdeaActionIntakeRequest,
    *,
    correlation_id: str,
    idempotency_key: str,
    principal: IdeaActionIntakePrincipal,
    received_at: datetime | None = None,
) -> IdeaActionIntakeResponse:
    response = acknowledge_idea_action_intake(
        request,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        principal=principal,
        received_at=received_at,
    )
    return _IDEMPOTENCY_REGISTRY.record(
        idempotency_key=idempotency_key,
        request_fingerprint=response.request_fingerprint,
        response=response,
    )


def reset_idea_action_intake_idempotency_for_tests() -> None:
    _IDEMPOTENCY_REGISTRY.reset()


class _IdeaActionIntakeIdempotencyRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, tuple[str, IdeaActionIntakeResponse]] = {}

    def record(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        response: IdeaActionIntakeResponse,
    ) -> IdeaActionIntakeResponse:
        idempotency_key_hash = _safe_key_hash(idempotency_key)
        with self._lock:
            existing = self._records.get(idempotency_key_hash)
            if existing is None:
                self._records[idempotency_key_hash] = (request_fingerprint, response)
                return response
            existing_fingerprint, existing_response = existing
            if existing_fingerprint != request_fingerprint:
                raise IdeaActionIntakeIdempotencyConflictError(
                    "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"
                )
            return existing_response.model_copy(
                update={
                    "intake_status": "ACCEPTED_REPLAYED"
                    if existing_response.action_receipt_accepted
                    else "REJECTED",
                    "idempotency_replay": True,
                    "correlation_id": response.correlation_id,
                    "trusted_scope": response.trusted_scope,
                    "received_at": response.received_at,
                    "outcome_reason_codes": _replay_reason_codes(existing_response),
                }
            )

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


_IDEMPOTENCY_REGISTRY = _IdeaActionIntakeIdempotencyRegistry()


def _source_refs_fingerprint(source_refs: list[IdeaActionSourceRef]) -> str:
    canonical_refs = sorted(
        (source_ref.model_dump(mode="json", exclude_none=False) for source_ref in source_refs),
        key=lambda item: (
            item["source_system"],
            item["source_type"],
            item["source_id"],
            item.get("content_hash") or "",
        ),
    )
    canonical_payload = json.dumps(canonical_refs, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_payload.encode()).hexdigest()


def _request_fingerprint(
    request: IdeaActionIntakeRequest,
    *,
    source_refs_fingerprint: str,
) -> str:
    canonical_payload = json.dumps(
        {
            "source_system": request.source_system,
            "source_product": request.source_product,
            "idea_candidate_id": request.idea_candidate_id,
            "conversion_intent_id": request.conversion_intent_id,
            "intent_type": request.intent_type,
            "source_refs_fingerprint": source_refs_fingerprint,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{sha256(canonical_payload.encode()).hexdigest()[:12]}"


def _safe_key_hash(idempotency_key: str) -> str:
    normalized = idempotency_key.strip()
    return f"sha256:{sha256(normalized.encode()).hexdigest()[:12]}"


def _trusted_scope(
    *,
    principal: IdeaActionIntakePrincipal | None,
    correlation_id: str,
) -> dict[str, Any]:
    if principal is None:
        return {
            "subject": "domain-only",
            "role": "DOMAIN_TEST",
            "tenant_id": "domain-only",
            "legal_entity_code": "DOMAIN",
            "correlation_id": correlation_id,
            "service_identity": "domain-only",
            "capability": IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
        }
    metadata = principal.audit_metadata(capability=IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY)
    metadata["correlation_id"] = correlation_id
    return metadata


def _outcome_reason_codes(request: IdeaActionIntakeRequest) -> list[str]:
    if request.intent_type == "REVIEW_FOR_REBALANCE":
        return ["idea_action_intake_receipt_accepted"]
    return [
        "action_register_persistence_not_certified",
        "idea_action_intake_receipt_rejected_no_action_created",
    ]


def _replay_reason_codes(response: IdeaActionIntakeResponse) -> list[str]:
    if response.action_receipt_accepted:
        return ["idea_action_intake_receipt_replayed"]
    return ["idea_action_intake_rejection_replayed"]


def _intake_id(
    *,
    idea_candidate_id: str,
    conversion_intent_id: str,
    intent_type: str,
    source_refs_fingerprint: str,
) -> str:
    digest = sha256(
        (
            f"{idea_candidate_id}|{conversion_intent_id}|{intent_type}|{source_refs_fingerprint}"
        ).encode()
    ).hexdigest()
    return f"iai_{digest[:12]}"
