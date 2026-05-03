"""Domain models for RFC-0040 pre-trade proof packs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ProofPackSourceType = Literal["REBALANCE_RUN", "SELECTED_ALTERNATIVE"]
ProofPackSectionState = Literal[
    "READY",
    "PENDING_REVIEW",
    "DEGRADED",
    "BLOCKED",
    "NOT_APPLICABLE",
]
ProofPackStatus = Literal["READY", "PENDING_REVIEW", "DEGRADED", "BLOCKED"]
ProofPackSectionType = Literal[
    "decision_summary",
    "mandate_context",
    "source_readiness",
    "before_state",
    "target_state",
    "selected_alternative",
    "trade_intents",
    "after_state",
    "drift_impact",
    "risk_impact",
    "performance_context",
    "tax_impact",
    "turnover_and_cost",
    "liquidity_and_cash",
    "fx_funding_plan",
    "currency_overlay_evidence",
    "scenario_and_regime_evidence",
    "eligibility_and_restrictions",
    "sustainability_controls",
    "rule_results",
    "approval_requirements",
    "operations_handoff",
    "decision_timeline",
    "lineage",
    "supportability",
    "reporting_refs",
    "ai_refs",
]


class DpmProofPackEvidenceRef(BaseModel):
    ref_type: str = Field(description="Evidence reference type.")
    ref_id: str = Field(description="Evidence reference identifier.")
    source_system: str = Field(description="System that owns the referenced evidence.")
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
    )


class DpmProofPackSourceRef(BaseModel):
    source_system: str = Field(description="Source system that owns this evidence.")
    source_type: str = Field(description="Source data or artifact type.")
    source_id: str = Field(description="Source identifier.")
    supportability_state: str | None = Field(
        default=None,
        description="Source supportability state when available.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
    )


class DpmProofPackSection(BaseModel):
    section_id: str = Field(description="Stable proof-pack section identifier.")
    section_type: ProofPackSectionType = Field(description="RFC-0040 section type.")
    state: ProofPackSectionState = Field(description="Section supportability state.")
    title: str = Field(description="Business title for the section.")
    summary: str = Field(description="Short business-readable section summary.")
    facts: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded source-backed facts for the section.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded source-backed metrics for the section.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining section state.",
    )
    evidence_refs: list[DpmProofPackEvidenceRef] = Field(
        default_factory=list,
        description="Evidence artifacts referenced by this section.",
    )
    source_refs: list[DpmProofPackSourceRef] = Field(
        default_factory=list,
        description="Source records referenced by this section.",
    )
    source_supportability: dict[str, Any] = Field(
        default_factory=dict,
        description="Source supportability detail for this section.",
    )
    redaction_policy: str = Field(
        default="NO_RAW_PAYLOADS",
        description="Redaction posture applied to section facts and metrics.",
    )
    generated_at: str = Field(description="UTC timestamp when this section was generated.")
    content_hash: str = Field(description="Canonical section content hash.")


class DpmProofPackDecisionSummary(BaseModel):
    decision_type: str = Field(description="Decision type represented by the proof pack.")
    recommended_action: str = Field(description="Recommended portfolio action.")
    selected_alternative_type: str | None = Field(
        default=None,
        description="Selected construction method when available.",
    )
    business_rationale: str = Field(description="Actor or system rationale for the decision.")
    expected_benefit: str = Field(description="Expected business benefit.")
    main_tradeoffs: list[str] = Field(description="Main accepted trade-offs.")
    top_risks: list[str] = Field(description="Top visible risk or supportability concerns.")
    approval_state: str = Field(description="Approval state or required review posture.")
    operations_state: str = Field(description="Operations handoff posture.")


class DpmProofPackDecisionTimelineEvent(BaseModel):
    event_id: str = Field(description="Stable event identifier.")
    event_type: str = Field(description="Decision timeline event type.")
    event_time: str = Field(description="UTC event timestamp.")
    actor: str = Field(description="Actor or service responsible for the event.")
    source_system: str = Field(description="Source system that emitted the event.")
    status: str = Field(description="Event status.")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes for this event.",
    )
    artifact_refs: list[DpmProofPackEvidenceRef] = Field(
        default_factory=list,
        description="Artifacts linked to this event.",
    )


class DpmProofPackDecisionTimeline(BaseModel):
    events: list[DpmProofPackDecisionTimelineEvent] = Field(
        description="Ordered decision timeline events."
    )


class DpmProofPackSupportability(BaseModel):
    status: ProofPackStatus = Field(description="Aggregate proof-pack status.")
    section_state_counts: dict[str, int] = Field(
        description="Section count by supportability state."
    )
    ready_section_count: int = Field(description="Count of READY sections.")
    degraded_section_count: int = Field(description="Count of DEGRADED sections.")
    blocked_section_count: int = Field(description="Count of BLOCKED sections.")
    pending_review_section_count: int = Field(description="Count of PENDING_REVIEW sections.")
    reason_codes: list[str] = Field(description="Aggregate reason codes across sections.")
    section_hashes: dict[str, str] = Field(description="Content hash by section id.")


class DpmPreTradeProofPack(BaseModel):
    proof_pack_id: str = Field(description="Stable pre-trade proof-pack identifier.")
    proof_pack_version: str = Field(description="Proof-pack contract version.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(default=None, description="Mandate identifier when available.")
    source_type: ProofPackSourceType = Field(description="Source used to generate the proof pack.")
    rebalance_run_id: str | None = Field(default=None, description="Source rebalance run id.")
    alternative_set_id: str | None = Field(
        default=None,
        description="Source construction alternative set id.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected construction alternative id.",
    )
    as_of_date: str = Field(description="Business as-of date for the proof pack.")
    status: ProofPackStatus = Field(description="Aggregate proof-pack status.")
    decision_summary: DpmProofPackDecisionSummary = Field(description="Business decision summary.")
    sections: list[DpmProofPackSection] = Field(description="RFC-0040 evidence sections.")
    approval_requirements: DpmProofPackSection = Field(description="Approval requirements section.")
    operations_handoff: DpmProofPackSection = Field(description="Operations handoff section.")
    decision_timeline: DpmProofPackDecisionTimeline = Field(
        description="Ordered decision timeline."
    )
    lineage: DpmProofPackSection = Field(description="Source lineage section.")
    supportability: DpmProofPackSupportability = Field(
        description="Aggregate proof-pack supportability posture."
    )
    content_hash: str = Field(description="Canonical proof-pack content hash.")
    source_hashes: dict[str, str] = Field(description="Canonical source hashes.")
    markdown_summary_ref: DpmProofPackEvidenceRef | None = Field(
        default=None,
        description="Markdown summary reference when generated.",
    )
    report_input_ref: DpmProofPackEvidenceRef | None = Field(
        default=None,
        description="Report input reference when generated.",
    )
    ai_evidence_ref: DpmProofPackEvidenceRef | None = Field(
        default=None,
        description="AI evidence input reference when generated.",
    )
    created_at: datetime = Field(description="UTC proof-pack creation timestamp.")
    created_by: str = Field(description="Human or service actor that generated the proof pack.")
    correlation_id: str = Field(description="Correlation identifier for the proof-pack request.")
