from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field


IdeaActionIntakeStatus = Literal["ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"]
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
    "intake_status": "ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED",
    "supportability_status": "not_certified",
    "source_authority": "lotus-idea",
    "action_authority": "lotus-manage",
    "target_product": "lotus-manage:PortfolioActionRegister:v1",
    "route_existence_proven": True,
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
        description="Optional source-owned content hash for replay and lineage checks.",
        examples=["sha256:abc123"],
    )


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
        description="lotus-idea candidate identifier; Manage does not infer portfolio facts from it.",
        examples=["idea_candidate_001"],
    )
    conversion_intent_id: str = Field(
        min_length=1,
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
        description="Source-safe idea evidence references supplied by lotus-idea.",
    )


class IdeaActionIntakeResponse(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE}}

    intake_id: str = Field(
        description="Deterministic source-safe intake identifier derived from source handoff fields.",
        examples=["iai_7a1d2b3c4d5e"],
    )
    intake_status: IdeaActionIntakeStatus = Field(
        description="Bounded route-foundation status; not a management action or execution status.",
        examples=["ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"],
    )
    supportability_status: IdeaActionIntakeSupportabilityStatus = Field(
        description="Certification posture for this route foundation.",
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
        description="Implementation and contract evidence references for the route foundation.",
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
    received_at: datetime | None = None,
) -> IdeaActionIntakeResponse:
    timestamp = received_at or datetime.now(timezone.utc)
    intake_id = _intake_id(
        idea_candidate_id=request.idea_candidate_id,
        conversion_intent_id=request.conversion_intent_id,
        intent_type=request.intent_type,
    )
    return IdeaActionIntakeResponse(
        intake_id=intake_id,
        intake_status="ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED",
        supportability_status="not_certified",
        source_authority="lotus-idea",
        action_authority="lotus-manage",
        target_product="lotus-manage:PortfolioActionRegister:v1",
        route_existence_proven=True,
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


def _intake_id(*, idea_candidate_id: str, conversion_intent_id: str, intent_type: str) -> str:
    digest = sha256(
        f"{idea_candidate_id}|{conversion_intent_id}|{intent_type}".encode()
    ).hexdigest()
    return f"iai_{digest[:12]}"
