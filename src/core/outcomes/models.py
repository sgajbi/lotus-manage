"""Domain models for RFC-0042 post-trade outcome reviews."""

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
    realized: DpmOutcomeMetricValue = Field(description="Realized value from post-trade source truth.")
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

    portfolio_id: str = Field(description="Portfolio identifier.", examples=["PB_SG_GLOBAL_BAL_001"])
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
