"""Domain models for RFC-0039 construction alternatives."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import Money


class ConstructionObjectiveTerm(BaseModel):
    term: ConstructionTraceTerm = Field(description="Bounded objective term identifier.")
    value: Decimal = Field(description="Objective value as a deterministic decimal.")
    unit: str = Field(description="Measurement unit for the value.")
    direction: str = Field(description="Whether lower, higher, or target-matching is preferred.")
    description: str = Field(description="Business explanation of the objective term.")


class ConstructionConstraintTrace(BaseModel):
    constraint: ConstructionTraceTerm = Field(description="Bounded constraint identifier.")
    status: ConstructionMethodStatus = Field(description="Constraint-level supportability status.")
    source_family: ConstructionSourceFamily = Field(
        description="Source family that owns or supports the constraint."
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining constraint handling.",
    )
    description: str = Field(description="Business explanation of the constraint.")


class ConstructionComparisonMetrics(BaseModel):
    drift_before: Decimal = Field(description="Absolute active-weight drift before construction.")
    drift_after: Decimal = Field(description="Absolute active-weight drift after construction.")
    drift_reduction: Decimal = Field(description="Drift_before minus drift_after.")
    turnover_weight: Decimal = Field(description="Security-trade turnover as weight of portfolio.")
    trade_count: int = Field(description="Number of security trade intents.")
    estimated_transaction_cost: Money | None = Field(
        default=None,
        description="Estimated local construction cost when available.",
    )
    cash_weight_after: Decimal | None = Field(
        default=None,
        description="Cash weight after applying the alternative when available.",
    )


class ConstructionAlternative(BaseModel):
    alternative_id: str = Field(description="Stable identifier within the alternative set.")
    method: ConstructionMethod = Field(description="Construction method used for this alternative.")
    method_status: ConstructionMethodStatus = Field(
        description="Method-level readiness and supportability posture."
    )
    summary: str = Field(description="Short business summary for the portfolio manager.")
    rebalance_run_id: str | None = Field(
        default=None,
        description="Source rebalance run id when this alternative wraps a simulation result.",
    )
    objective_trace: list[ConstructionObjectiveTerm] = Field(
        description="Bounded objective terms used for comparison."
    )
    constraint_trace: list[ConstructionConstraintTrace] = Field(
        description="Bounded constraints and supportability posture."
    )
    comparison_metrics: ConstructionComparisonMetrics = Field(
        description="Normalized metrics comparable across alternatives."
    )
    intent_ids: list[str] = Field(
        default_factory=list,
        description="Trade/FX intent identifiers referenced by this alternative.",
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded diagnostic summary, not raw request or source payloads.",
    )


class ConstructionAlternativeSet(BaseModel):
    alternative_set_id: str = Field(description="Stable construction alternative set identifier.")
    portfolio_id: str = Field(description="Portfolio for which alternatives were generated.")
    as_of: str = Field(description="Business as-of date or timestamp used for construction.")
    status: ConstructionMethodStatus = Field(description="Aggregate alternative set status.")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the alternative set was generated.",
    )
    alternatives: list[ConstructionAlternative] = Field(
        description="Comparable construction alternatives."
    )
    request_hash: str | None = Field(
        default=None,
        description="Canonical request hash used for idempotent replay and audit lookup.",
    )
    input_mode: Literal["stateless", "stateful"] = Field(
        default="stateless",
        description="Input mode used to generate the alternative set.",
    )
    source_supportability_state: str | None = Field(
        default=None,
        description="Upstream source-data supportability state when generated from lotus-core.",
    )


class ConstructionEnrichmentSummary(BaseModel):
    tax_status: ConstructionMethodStatus = Field(description="Tax enrichment posture.")
    turnover_status: ConstructionMethodStatus = Field(description="Turnover enrichment posture.")
    liquidity_status: ConstructionMethodStatus = Field(description="Liquidity enrichment posture.")
    cost_status: ConstructionMethodStatus = Field(description="Transaction-cost posture.")
    fx_status: ConstructionMethodStatus = Field(description="FX source posture.")
    risk_status: ConstructionMethodStatus = Field(
        default=ConstructionMethodStatus.DEGRADED,
        description="Risk-authoritative enrichment posture.",
    )
    performance_status: ConstructionMethodStatus = Field(
        default=ConstructionMethodStatus.DEGRADED,
        description="Performance-authoritative enrichment posture.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining degraded or blocked enrichment.",
    )


class AuthoritativeRiskContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Risk-service supportability status for the enrichment."
    )
    source_system: str = Field(description="Risk authority that produced the enrichment.")
    tracking_error: Decimal | None = Field(
        default=None,
        description="Risk-authoritative tracking error when provided.",
    )
    concentration_breaches: int | None = Field(
        default=None,
        description="Risk-authoritative concentration-breach count when provided.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Risk-authoritative bounded reason codes.",
    )


class AuthoritativePerformanceContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Performance-service supportability status for the enrichment."
    )
    source_system: str = Field(description="Performance authority that produced the enrichment.")
    benchmark_id: str | None = Field(
        default=None,
        description="Performance-authoritative benchmark identifier when provided.",
    )
    active_return: Decimal | None = Field(
        default=None,
        description="Performance-authoritative active return when provided.",
    )
    underperformance_flag: bool | None = Field(
        default=None,
        description="Performance-authoritative attention flag when provided.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Performance-authoritative bounded reason codes.",
    )


class ConstructionSolverPosture(BaseModel):
    solver_required: bool = Field(description="Whether the requested method requires a solver.")
    solver_available: bool = Field(description="Whether solver dependencies are available.")
    solver_engine: str | None = Field(
        default=None,
        description="Solver engine family when available.",
    )
    reason_code: str = Field(description="Bounded solver supportability reason code.")


class ConstructionMethodDefinition(BaseModel):
    method: ConstructionMethod = Field(description="Construction method identifier.")
    display_name: str = Field(description="Business display name for the method.")
    first_wave: bool = Field(description="Whether the method is in the RFC-0039 first wave.")
    requires_solver: bool = Field(description="Whether the method requires solver dependencies.")
    required_source_families: list[ConstructionSourceFamily] = Field(
        description="Mandatory source families for method readiness."
    )
    fallback_method: ConstructionMethod | None = Field(
        default=None,
        description="Fallback method when the requested method cannot run.",
    )
    support_promotion_gate: str = Field(
        description="Evidence gate required before supported-feature promotion.",
    )


class ConstructionMethodPlan(BaseModel):
    requested_method: ConstructionMethod = Field(
        description="Method requested by caller or engine."
    )
    effective_method: ConstructionMethod = Field(description="Method that should actually run.")
    method_status: ConstructionMethodStatus = Field(description="Planning-time method status.")
    fallback_method: ConstructionMethod | None = Field(
        default=None,
        description="Fallback method selected by the registry.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded planning and fallback reason codes.",
    )
    required_source_families: list[ConstructionSourceFamily] = Field(
        description="Mandatory source families for the effective method."
    )
    solver_posture: ConstructionSolverPosture = Field(
        description="Solver supportability posture for the method plan."
    )


class ConstructionAlternativeSelection(BaseModel):
    selection_id: str = Field(description="Stable selection decision identifier.")
    alternative_set_id: str = Field(description="Alternative set that contains the selection.")
    alternative_id: str = Field(description="Selected alternative identifier.")
    selected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the selection was recorded.",
    )
    actor_id: str = Field(description="Human or service actor that made the selection.")
    reason_code: str = Field(description="Bounded reason code explaining the selection.")
    comment: str | None = Field(
        default=None,
        description="Optional business comment captured with the selection.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional request correlation identifier associated with the selection.",
    )
