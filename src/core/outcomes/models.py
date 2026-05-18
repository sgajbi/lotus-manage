"""Domain models for RFC-0042 post-trade outcome reviews."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

OutcomeDimension = Literal[
    "DRIFT_REDUCTION",
    "RISK_REDUCTION",
    "PERFORMANCE",
    "COST",
    "TAX",
    "EXECUTION_QUALITY",
    "FX_RESIDUAL",
    "CASH_RESIDUAL",
    "RULE_OUTCOME",
]

OutcomeDimensionState = Literal[
    "READY",
    "PENDING_REVIEW",
    "BREACHED",
    "DEGRADED",
    "BLOCKED",
    "NOT_SUPPORTED",
]

OutcomeReviewState = OutcomeDimensionState

OutcomeComparisonDirection = Literal[
    "LOWER_IS_BETTER",
    "HIGHER_IS_BETTER",
    "TARGET_VALUE",
]

OutcomeEventType = Literal[
    "OUTCOME_REVIEW_CREATED",
    "OUTCOME_REVIEW_SOURCE_REFRESHED",
    "OUTCOME_REVIEW_DEGRADED",
    "OUTCOME_REVIEW_BLOCKED",
    "OUTCOME_REVIEW_READY",
    "OUTCOME_REVIEW_PM_EXPLANATION_ADDED",
    "OUTCOME_REVIEW_REPORT_INPUT_CREATED",
    "OUTCOME_REVIEW_AI_EVIDENCE_INPUT_CREATED",
]


class DpmOutcomeSourceRef(BaseModel):
    """Source-owner reference carried into an outcome review."""

    source_system: str = Field(
        description="System that owns this source evidence.",
        examples=["lotus-performance"],
    )
    source_type: str = Field(
        description="Source data product, artifact, or event type.",
        examples=["PERFORMANCE_WINDOW_RETURN"],
    )
    source_id: str = Field(description="Source identifier.", examples=["perf_PB_SG_20260505"])
    source_version: str | None = Field(
        default=None,
        description="Source contract or data product version when available.",
        examples=["1.0.0"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
        examples=["sha256:outcome-source-example"],
    )


class DpmOutcomeSourceFreshness(BaseModel):
    """Freshness posture for a source-owned outcome value."""

    observed_at: str | None = Field(
        default=None,
        description="UTC timestamp when the source value was observed.",
        examples=["2026-05-05T01:15:00Z"],
    )
    as_of_date: str | None = Field(
        default=None,
        description="Business as-of date for the source value.",
        examples=["2026-05-05"],
    )
    freshness_state: Literal["CURRENT", "STALE", "UNKNOWN"] = Field(
        default="UNKNOWN",
        description="Bounded freshness state.",
        examples=["CURRENT"],
    )


class DpmOutcomeSupportability(BaseModel):
    """Supportability posture for a dimension or source value."""

    state: OutcomeDimensionState = Field(
        description="Bounded supportability state.",
        examples=["READY"],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining the supportability state.",
        examples=[["SOURCE_READY"]],
    )
    required_source: bool = Field(
        default=True,
        description="Whether this source is mandatory for the dimension to be evaluated.",
        examples=[True],
    )
    explanation: str | None = Field(
        default=None,
        description="Operator-safe explanation without raw upstream payloads.",
        examples=["Performance source is current for the requested review window."],
    )


class DpmOutcomeExternalExecutionBoundaryEvidence(BaseModel):
    """Fail-closed external execution boundary for outcome-review consumers."""

    boundary_id: Literal["DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"] = Field(
        default="DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY",
        description="Stable unsupported external execution boundary identifier.",
    )
    supportability_state: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Fail-closed supportability state for external execution evidence.",
    )
    source_system: Literal["lotus-manage"] = Field(
        default="lotus-manage",
        description="System preserving the unsupported outcome-review boundary evidence.",
    )
    source_product_name: Literal["DpmPostTradeOutcomeReview"] = Field(
        default="DpmPostTradeOutcomeReview",
        description="Manage-owned source product that consumes but does not own execution truth.",
    )
    source_product_version: Literal["v1"] = Field(
        default="v1",
        description="Boundary evidence product version.",
    )
    source_product_present: bool = Field(
        description=(
            "Whether source lineage includes Core ExternalOrderExecutionAcknowledgement posture."
        ),
        examples=[True],
    )
    execution_quality_dimension_state: OutcomeDimensionState | None = Field(
        default=None,
        description="Current outcome-review EXECUTION_QUALITY dimension state when present.",
        examples=["BLOCKED"],
    )
    execution_acknowledgement_count_projected: int | None = Field(
        default=None,
        description=(
            "Acknowledgement-count posture preserved from source reason codes when available; "
            "zero means no certified acknowledgements are projected."
        ),
        examples=[0],
    )
    reason_code: str = Field(
        description="Bounded reason code for the external execution outcome boundary.",
        examples=["OUTCOME_EXTERNAL_EXECUTION_EVIDENCE_NOT_CERTIFIED"],
    )
    blocked_capabilities: list[str] = Field(
        description="External execution capabilities blocked from outcome-review promotion.",
        examples=[["best_execution", "oms_acknowledgement", "fills", "settlement"]],
    )
    required_owner: str = Field(
        description="Future owner required before execution evidence can be promoted.",
        examples=["future execution/OMS owner"],
    )
    required_source_product: str = Field(
        description="Source product required before Manage can consume execution acknowledgement truth.",
        examples=["ExternalOrderExecutionAcknowledgement:v1"],
    )
    summary: str = Field(description="Operator-facing no-claim outcome boundary summary.")
    content_hash: str = Field(description="Canonical hash of the boundary evidence payload.")


class DpmOutcomeClientCommunicationBoundaryEvidence(BaseModel):
    """Fail-closed client-communication boundary for outcome-review consumers."""

    boundary_id: Literal["DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY"] = Field(
        default="DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY",
        description="Stable unsupported client-communication boundary identifier.",
    )
    supportability_state: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Fail-closed supportability state for client communication evidence.",
    )
    source_system: Literal["lotus-manage"] = Field(
        default="lotus-manage",
        description="System preserving the unsupported outcome-review communication boundary.",
    )
    source_product_name: Literal["DpmPostTradeOutcomeReview"] = Field(
        default="DpmPostTradeOutcomeReview",
        description=(
            "Manage-owned source product that may support internal review but does not own "
            "client-contact truth."
        ),
    )
    source_product_version: Literal["v1"] = Field(
        default="v1",
        description="Boundary evidence product version.",
    )
    client_communication_projected: Literal[False] = Field(
        default=False,
        description="Outcome-review evidence never projects client communication delivery.",
    )
    client_approval_projected: Literal[False] = Field(
        default=False,
        description="Outcome-review evidence never projects client approval.",
    )
    reason_code: str = Field(
        description="Bounded reason code for the client communication outcome boundary.",
        examples=["OUTCOME_CLIENT_COMMUNICATION_NOT_SUPPORTED"],
    )
    blocked_capabilities: list[str] = Field(
        description="Client communication capabilities blocked from outcome-review promotion.",
        examples=[["client_contact", "message_generation", "delivery_confirmation"]],
    )
    required_owner: str = Field(
        description="Future owner required before client communication evidence can be promoted.",
        examples=["future client-communication owner"],
    )
    required_source_product: str = Field(
        description="Source product required before Manage can consume client communication truth.",
        examples=["ClientCommunicationRecord:v1"],
    )
    summary: str = Field(description="Operator-facing no-claim client communication summary.")
    content_hash: str = Field(description="Canonical hash of the boundary evidence payload.")


class DpmOutcomeMetricValue(BaseModel):
    """Expected or realized value supplied by a source owner."""

    value: Decimal | None = Field(
        default=None,
        description="Comparable numeric value. Null means the value was not available.",
        examples=["0.0125"],
    )
    unit: str = Field(description="Value unit.", examples=["ratio"])
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs supporting this value.",
    )
    source_freshness: DpmOutcomeSourceFreshness = Field(
        default_factory=DpmOutcomeSourceFreshness,
        description="Freshness posture for this value.",
    )
    supportability: DpmOutcomeSupportability = Field(
        default_factory=lambda: DpmOutcomeSupportability(state="READY"),
        description="Supportability posture for this value.",
    )


class DpmOutcomeTolerance(BaseModel):
    """Soft and hard tolerance used by the deterministic comparator."""

    soft: Decimal = Field(
        ge=0,
        description="Variance threshold that moves a complete source result to pending review.",
        examples=["0.0025"],
    )
    hard: Decimal = Field(
        ge=0,
        description="Variance threshold that moves a complete source result to breached.",
        examples=["0.0100"],
    )

    @model_validator(mode="after")
    def hard_must_be_at_least_soft(self) -> "DpmOutcomeTolerance":
        if self.hard < self.soft:
            msg = "hard tolerance must be greater than or equal to soft tolerance"
            raise ValueError(msg)
        return self


class DpmOutcomeDimensionInput(BaseModel):
    """Pure input for one expected-versus-realized dimension comparison."""

    dimension: OutcomeDimension = Field(
        description="Outcome dimension being compared.",
        examples=["DRIFT_REDUCTION"],
    )
    expected: DpmOutcomeMetricValue = Field(description="Expected value from pre-trade evidence.")
    realized: DpmOutcomeMetricValue = Field(
        description="Realized value from post-trade source truth."
    )
    tolerance: DpmOutcomeTolerance = Field(description="Soft and hard tolerance.")
    materiality: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Business materiality threshold for explanation and reporting.",
        examples=["0.0050"],
    )
    direction: OutcomeComparisonDirection = Field(
        description="How expected and realized values should be compared.",
        examples=["LOWER_IS_BETTER"],
    )


class DpmOutcomeDimensionResult(BaseModel):
    """Deterministic result for one outcome dimension."""

    dimension: OutcomeDimension = Field(description="Outcome dimension.")
    state: OutcomeDimensionState = Field(description="Dimension state after comparison.")
    reason_code: str = Field(description="Primary bounded reason code.")
    expected: Decimal | None = Field(default=None, description="Expected numeric value.")
    realized: Decimal | None = Field(default=None, description="Realized numeric value.")
    variance: Decimal | None = Field(
        default=None,
        description="Realized minus expected variance when both values are available.",
    )
    tolerance: DpmOutcomeTolerance = Field(description="Tolerance applied by the comparator.")
    materiality: Decimal = Field(description="Materiality threshold supplied for the dimension.")
    explanation: str = Field(description="Operator-safe deterministic explanation.")
    source_refs: list[DpmOutcomeSourceRef] = Field(description="Source refs used by the result.")
    source_freshness: list[DpmOutcomeSourceFreshness] = Field(
        description="Freshness posture for compared values.",
    )
    supportability: DpmOutcomeSupportability = Field(
        description="Rolled-up supportability for the dimension.",
    )
    calculation_trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded calculation trace without raw upstream payloads.",
    )


class DpmOutcomeReviewComparison(BaseModel):
    """Pure comparison output across one or more dimensions."""

    state: OutcomeReviewState = Field(description="Overall outcome-review state.")
    dimension_results: list[DpmOutcomeDimensionResult] = Field(
        description="Dimension-level comparison results.",
    )
    overall_outcome: str = Field(
        description="Business-readable deterministic outcome summary.",
        examples=["READY_WITHIN_TOLERANCE"],
    )
    variance_summary: dict[str, Decimal | None] = Field(
        default_factory=dict,
        description="Variance by dimension.",
    )
    supportability: DpmOutcomeSupportability = Field(
        description="Rolled-up supportability across dimensions.",
    )


class DpmExpectedOutcomeSnapshot(BaseModel):
    """Expected outcome snapshot assembled from pre-trade manage artifacts."""

    portfolio_id: str = Field(
        description="Portfolio identifier.", examples=["PB_SG_GLOBAL_BAL_001"]
    )
    mandate_id: str | None = Field(
        default=None,
        description="Mandate identifier when available.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    rebalance_run_id: str | None = Field(
        default=None,
        description="RFC-0036/0039 rebalance run identifier when available.",
        examples=["rr_001"],
    )
    alternative_set_id: str = Field(
        description="RFC-0039 construction alternative set identifier.",
        examples=["cas_001"],
    )
    selected_alternative_id: str = Field(
        description="Selected RFC-0039 alternative identifier.",
        examples=["alt_min_turnover"],
    )
    proof_pack_id: str = Field(description="RFC-0040 proof-pack identifier.", examples=["dpp_001"])
    wave_id: str | None = Field(
        default=None,
        description="RFC-0041 wave identifier when the expected snapshot is wave-linked.",
        examples=["dwv_001"],
    )
    wave_item_id: str | None = Field(
        default=None,
        description="RFC-0041 wave item identifier when available.",
        examples=["dwi_001"],
    )
    operations_handoff_ref_id: str | None = Field(
        default=None,
        description="RFC-0041 internal operations handoff ref when available.",
        examples=["dwh_001"],
    )
    expected_values: dict[OutcomeDimension, DpmOutcomeMetricValue] = Field(
        description="Expected comparable values by outcome dimension. No value is defaulted.",
    )
    supportability: DpmOutcomeSupportability = Field(
        description="Expected snapshot supportability rolled up from manage artifacts.",
    )
    source_lineage: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs preserved from construction, proof-pack, wave, and handoff evidence.",
    )
    source_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Canonical source hashes carried from the proof pack.",
    )
    section_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="RFC-0040 proof-pack section hashes.",
    )
    calculation_trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded trace explaining how the expected snapshot was assembled.",
    )


class DpmOutcomeReviewWindow(BaseModel):
    """Review window used to request and reconcile post-trade source evidence."""

    start_at: str = Field(
        description="Inclusive UTC review-window start.", examples=["2026-05-05T01:00:00Z"]
    )
    end_at: str = Field(
        description="Exclusive UTC review-window end.", examples=["2026-05-06T01:00:00Z"]
    )
    as_of_date: str = Field(
        description="Business as-of date for the review.", examples=["2026-05-06"]
    )
    timezone: str = Field(
        default="UTC", description="Window timezone.", examples=["Asia/Singapore"]
    )


class DpmRealizedSourceSnapshot(BaseModel):
    """Source-owner realized value or explicit degraded-source posture."""

    dimension: OutcomeDimension = Field(description="Outcome dimension supplied by the source.")
    source_system: str = Field(
        description="Source owner that produced the realized evidence.",
        examples=["lotus-core"],
    )
    source_type: str = Field(
        description="Source-owner contract or data product type.",
        examples=["POST_TRADE_HOLDINGS_DRIFT"],
    )
    source_id: str = Field(
        description="Source-owner evidence identifier.", examples=["core_drift_001"]
    )
    value: Decimal | None = Field(
        default=None,
        description="Realized value from source truth, or null when unavailable.",
        examples=["0.0375"],
    )
    unit: str = Field(description="Value unit.", examples=["ratio"])
    source_state: OutcomeDimensionState = Field(
        description="Source supportability state for this dimension.",
        examples=["READY"],
    )
    quality: Literal[
        "COMPLETE",
        "MISSING",
        "STALE",
        "UNAVAILABLE",
        "PARTIAL",
        "MALFORMED",
        "CONFLICTING",
        "NOT_SUPPORTED",
    ] = Field(description="Specific source-quality posture.", examples=["COMPLETE"])
    observed_at: str | None = Field(
        default=None,
        description="UTC timestamp when the source value was observed.",
        examples=["2026-05-06T01:10:00Z"],
    )
    as_of_date: str | None = Field(
        default=None,
        description="Business as-of date for the source value.",
        examples=["2026-05-06"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
        examples=["sha256:realized-source"],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Source-owner reason codes.",
        examples=[["SOURCE_READY"]],
    )


class DpmRealizedOutcomeSnapshot(BaseModel):
    """Realized outcome snapshot assembled from source-owner evidence."""

    portfolio_id: str = Field(
        description="Portfolio identifier.", examples=["PB_SG_GLOBAL_BAL_001"]
    )
    review_window: DpmOutcomeReviewWindow = Field(
        description="Review window for realized evidence."
    )
    realized_values: dict[OutcomeDimension, DpmOutcomeMetricValue] = Field(
        description="Realized values or explicit missing/not-supported postures by dimension.",
    )
    supportability: DpmOutcomeSupportability = Field(
        description="Realized snapshot supportability rolled up from source evidence.",
    )
    source_lineage: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source-owner refs used by the realized snapshot.",
    )
    source_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Canonical source hashes by source identifier.",
    )
    quality_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Counts by realized source quality posture.",
    )


class DpmOutcomeEvent(BaseModel):
    """Append-only event suitable for future portfolio memory."""

    event_id: str = Field(description="Stable event identifier.")
    event_type: OutcomeEventType = Field(description="Outcome review event type.")
    event_time: str = Field(description="UTC event timestamp.")
    actor: str = Field(description="Actor or service responsible for the event.")
    outcome_review_id: str = Field(description="Outcome review identifier.")
    state: OutcomeReviewState = Field(description="Review state at event time.")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes for the event.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs linked to the event.",
    )


class DpmOutcomeRetentionMetadata(BaseModel):
    """Retention metadata for an immutable outcome review."""

    outcome_review_id: str = Field(description="Outcome review identifier.")
    retention_policy: str = Field(description="Retention policy applied to the outcome review.")
    retention_expires_at: str | None = Field(
        default=None,
        description="UTC retention expiry timestamp when configured.",
    )
    legal_hold_state: Literal["NONE", "ACTIVE"] = Field(
        default="NONE",
        description="Legal hold posture for retention enforcement.",
    )


class DpmPostTradeOutcomeReview(BaseModel):
    """Immutable RFC-0042 post-trade outcome review."""

    outcome_review_id: str = Field(description="Stable outcome review identifier.")
    outcome_review_version: str = Field(
        default="1.0.0",
        description="Outcome-review contract version.",
    )
    state: OutcomeReviewState = Field(description="Overall outcome-review state.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(default=None, description="Mandate identifier when available.")
    rebalance_run_id: str | None = Field(default=None, description="Rebalance run identifier.")
    alternative_set_id: str = Field(description="RFC-0039 alternative set identifier.")
    selected_alternative_id: str = Field(description="RFC-0039 selected alternative identifier.")
    proof_pack_id: str = Field(description="RFC-0040 proof-pack identifier.")
    wave_id: str | None = Field(default=None, description="RFC-0041 wave identifier.")
    wave_item_id: str | None = Field(default=None, description="RFC-0041 wave item identifier.")
    operations_handoff_ref_id: str | None = Field(
        default=None,
        description="RFC-0041 internal operations handoff ref.",
    )
    execution_evidence_ref: DpmOutcomeSourceRef | None = Field(
        default=None,
        description="Execution-owner evidence ref when certified evidence exists.",
    )
    review_window: DpmOutcomeReviewWindow = Field(description="Post-trade review window.")
    expected_snapshot: DpmExpectedOutcomeSnapshot = Field(
        description="Expected pre-trade snapshot."
    )
    realized_snapshot: DpmRealizedOutcomeSnapshot = Field(
        description="Realized source-owner snapshot."
    )
    dimension_results: list[DpmOutcomeDimensionResult] = Field(
        description="Dimension comparison results.",
    )
    overall_outcome: str = Field(description="Deterministic overall outcome summary.")
    variance_summary: dict[str, Decimal | None] = Field(
        description="Variance by outcome dimension."
    )
    supportability: DpmOutcomeSupportability = Field(description="Review supportability roll-up.")
    source_lineage: list[DpmOutcomeSourceRef] = Field(
        description="Combined expected and realized source refs.",
    )
    source_hashes: dict[str, str] = Field(description="Source hashes used by the review.")
    section_hashes: dict[str, str] = Field(
        description="Proof-pack section hashes used by the review.",
    )
    events: list[DpmOutcomeEvent] = Field(
        default_factory=list,
        description="Append-only events included when the review was created.",
    )
    report_input_ref: DpmOutcomeSourceRef | None = Field(
        default=None,
        description="Outcome report input ref when produced.",
    )
    ai_evidence_ref: DpmOutcomeSourceRef | None = Field(
        default=None,
        description="Outcome AI evidence input ref when produced.",
    )
    retention_policy: str = Field(
        default="DPM_OUTCOME_REVIEW_7Y",
        description="Retention policy.",
    )
    legal_hold_state: Literal["NONE", "ACTIVE"] = Field(
        default="NONE",
        description="Legal hold state.",
    )
    content_hash: str = Field(description="Canonical immutable review content hash.")
    created_at: datetime = Field(description="UTC creation timestamp.")
    created_by: str = Field(description="Actor or service that created the review.")
    correlation_id: str = Field(description="Correlation identifier.")
    idempotency_key: str | None = Field(default=None, description="Create idempotency key.")
