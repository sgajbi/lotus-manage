"""Configurable PM operating quality models for RFC42-WTBD-008."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.outcomes import DpmOutcomeSourceRef

PmQualityIndicator = Literal[
    "OUTCOME_DISCIPLINE",
    "SOURCE_QUALITY",
    "EXCEPTION_DISCIPLINE",
    "EVIDENCE_COMPLETENESS",
]

PmQualityState = Literal[
    "DISABLED",
    "READY",
    "PENDING_REVIEW",
    "DEGRADED",
    "BREACHED",
    "BLOCKED",
]

PmQualityAccessPurpose = Literal[
    "PORTFOLIO_MANAGEMENT_REVIEW",
    "SUPERVISORY_CONTROL_REVIEW",
    "OPERATIONS_SUPPORT",
    "CLIENT_DEMO_EVIDENCE",
]


class DpmPmQualityWeight(BaseModel):
    """One configured scoring dimension for PM operating quality."""

    indicator: PmQualityIndicator = Field(
        description="Bounded indicator included in the bank-configured score policy.",
        examples=["OUTCOME_DISCIPLINE"],
    )
    weight: Decimal = Field(
        gt=0,
        le=100,
        description="Relative indicator weight. Weights are normalized by the score engine.",
        examples=["50"],
    )
    minimum_evidence_count: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Minimum source-backed signals required for this indicator.",
        examples=[1],
    )


class DpmPmOperatingQualityPolicy(BaseModel):
    """Bank-owned PM operating quality policy supplied to a score run."""

    policy_id: str = Field(description="Bank-owned policy identifier.", examples=["pmq_sg_dpm"])
    policy_version: str = Field(description="Policy version.", examples=["2026.05"])
    enabled: bool = Field(
        default=False,
        description="Explicit enablement switch. Disabled policies produce no PM score.",
        examples=[True],
    )
    as_of_date: str = Field(description="Policy business as-of date.", examples=["2026-05-12"])
    access_purpose: PmQualityAccessPurpose = Field(
        description="Permitted purpose for this score run.",
        examples=["SUPERVISORY_CONTROL_REVIEW"],
    )
    weights: list[DpmPmQualityWeight] = Field(
        default_factory=list,
        description="Configured scoring weights. Required when policy is enabled.",
    )
    ready_threshold: Decimal = Field(
        default=Decimal("80"),
        ge=0,
        le=100,
        description="Minimum score for READY posture.",
        examples=["80"],
    )
    watch_threshold: Decimal = Field(
        default=Decimal("60"),
        ge=0,
        le=100,
        description="Minimum score before BREACHED posture.",
        examples=["60"],
    )
    allowed_uses: list[str] = Field(
        default_factory=lambda: [
            "portfolio_management_review",
            "supervisory_control_review",
            "operations_support",
        ],
        description=(
            "Operator-visible allowed uses. Compensation, HR, conduct enforcement, and autonomous "
            "decisioning are rejected by the score engine."
        ),
    )

    @model_validator(mode="after")
    def validate_policy(self) -> "DpmPmOperatingQualityPolicy":
        if self.ready_threshold < self.watch_threshold:
            raise ValueError("ready_threshold must be greater than or equal to watch_threshold")
        if self.enabled and not self.weights:
            raise ValueError("enabled PM quality policies require at least one configured weight")
        indicators = [weight.indicator for weight in self.weights]
        if len(set(indicators)) != len(indicators):
            raise ValueError("PM quality policy indicators must be unique")
        forbidden = {"compensation", "hr", "conduct_enforcement", "autonomous_decisioning"}
        normalized_uses = {use.strip().lower() for use in self.allowed_uses}
        if normalized_uses & forbidden:
            raise ValueError("PM quality policy contains a prohibited use")
        return self


class DpmPmQualityEvidenceItem(BaseModel):
    """Source-owned signal supplied to a PM operating quality score run."""

    indicator: PmQualityIndicator = Field(description="Indicator represented by this signal.")
    evidence_state: PmQualityState = Field(
        description="Bounded source evidence posture.",
        examples=["READY"],
    )
    score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Source-supplied bounded score. Null requires a state-derived score.",
        examples=["92"],
    )
    source_system: str = Field(description="System that owns this signal.", examples=["lotus-risk"])
    source_type: str = Field(
        description="Source data product, artifact, or event type.",
        examples=["RollingRiskMetricsReport"],
    )
    source_id: str = Field(description="Source identifier.", examples=["risk_pm_001"])
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining this signal.",
        examples=[["SOURCE_READY"]],
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs supporting this signal.",
    )


class DpmPmQualityIndicatorResult(BaseModel):
    """Decomposed PM operating quality indicator result."""

    indicator: PmQualityIndicator = Field(description="Scored indicator.")
    score: Decimal | None = Field(description="Indicator score, null when unavailable.")
    weight: Decimal = Field(description="Policy weight applied to this indicator.")
    state: PmQualityState = Field(description="Indicator state.")
    evidence_count: int = Field(description="Number of source-backed signals used.")
    reason_codes: list[str] = Field(description="Bounded indicator reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(description="Source refs used by the indicator.")


class DpmPmOperatingQualityScoreRun(BaseModel):
    """Deterministic, explainable PM operating quality score run."""

    product_name: Literal["PmOperatingQualityScoreRun"] = Field(
        default="PmOperatingQualityScoreRun",
        description="Domain data product name emitted by lotus-manage.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    score_run_id: str = Field(description="Stable content-addressed score-run identifier.")
    pm_id: str = Field(description="Portfolio manager identifier.", examples=["pm_001"])
    book_id: str | None = Field(default=None, description="PM book identifier when available.")
    as_of_date: str = Field(description="Score-run business as-of date.", examples=["2026-05-12"])
    policy_id: str = Field(description="Policy identifier.")
    policy_version: str = Field(description="Policy version.")
    state: PmQualityState = Field(description="Score-run state.")
    score: Decimal | None = Field(description="Overall score, null when scoring is disabled.")
    indicator_results: list[DpmPmQualityIndicatorResult] = Field(
        description="Decomposed indicator results."
    )
    reason_codes: list[str] = Field(description="Bounded score-run reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(description="Source refs used by the run.")
    forbidden_uses: list[str] = Field(
        default_factory=lambda: [
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "autonomous_pm_ranking",
        ],
        description="Uses explicitly outside this product contract.",
    )
    content_hash: str = Field(description="Canonical score-run content hash.")
    generated_at: datetime = Field(description="UTC generation timestamp.")
    generated_by: str = Field(description="Actor or service that generated the score run.")
    correlation_id: str = Field(description="Correlation identifier.")
