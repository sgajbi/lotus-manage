"""Domain models for RFC-0039 construction alternatives."""

from __future__ import annotations

from datetime import date, datetime, timezone
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
    source_product_name: str | None = Field(
        default=None,
        description="Source-owned risk product name when the authority exposes one.",
    )
    source_product_version: str | None = Field(
        default=None,
        description="Source-owned risk product version when available.",
    )
    source_id: str | None = Field(
        default=None,
        description="Source-owned risk evidence identifier or request fingerprint.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical source-owned evidence hash when available.",
    )
    tracking_error: Decimal | None = Field(
        default=None,
        description="Risk-authoritative tracking error when provided.",
    )
    concentration_breaches: int | None = Field(
        default=None,
        description="Risk-authoritative concentration-breach count when provided.",
    )
    concentration_hhi_delta: Decimal | None = Field(
        default=None,
        description="Risk-authoritative proposed-minus-current HHI concentration delta.",
    )
    top_position_weight_proposed: Decimal | None = Field(
        default=None,
        description="Risk-authoritative proposed top-position weight.",
    )
    issuer_coverage_status: str | None = Field(
        default=None,
        description="Risk-authoritative issuer enrichment coverage status.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Risk-authoritative bounded reason codes.",
    )


class AuthoritativeTransactionCostPoint(BaseModel):
    security_id: str = Field(description="Security represented by the observed cost point.")
    transaction_type: str = Field(description="Observed transaction type.")
    currency: str = Field(description="Currency of observed notional and cost values.")
    observation_count: int = Field(description="Number of source transactions represented.")
    total_notional: Decimal = Field(description="Total absolute observed notional.")
    total_cost: Decimal = Field(description="Total observed booked cost.")
    average_cost_bps: Decimal = Field(
        description="Observed average cost in basis points; not a predictive execution quote."
    )
    min_cost_bps: Decimal = Field(description="Minimum observed transaction cost in bps.")
    max_cost_bps: Decimal = Field(description="Maximum observed transaction cost in bps.")
    first_observed_date: date = Field(description="Earliest represented transaction date.")
    last_observed_date: date = Field(description="Latest represented transaction date.")
    sample_transaction_ids: list[str] = Field(
        default_factory=list,
        description="Bounded sample of source transaction identifiers.",
    )


class AuthoritativeTransactionCostContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Source-owner supportability status for observed transaction-cost evidence."
    )
    source_system: str = Field(description="Source system that owns the cost evidence.")
    source_product_name: str = Field(
        default="TransactionCostCurve",
        description="Source-owned transaction-cost product name.",
    )
    source_product_version: str = Field(
        default="v1",
        description="Source-owned transaction-cost product version.",
    )
    source_id: str | None = Field(
        default=None,
        description="Source-owned evidence identifier or request fingerprint.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical source-owned evidence hash when available.",
    )
    as_of_date: date = Field(description="Business date used to resolve the source product.")
    window_start_date: date = Field(description="Inclusive evidence-window start date.")
    window_end_date: date = Field(description="Inclusive evidence-window end date.")
    returned_curve_point_count: int = Field(
        description="Number of observed cost-curve points returned by the source owner."
    )
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without qualifying cost evidence.",
    )
    curve_points: list[AuthoritativeTransactionCostPoint] = Field(
        default_factory=list,
        description="Bounded observed cost-curve points from the source owner.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Source-owner bounded reason codes.",
    )


class AuthoritativeClientRestrictionRule(BaseModel):
    restriction_scope: str = Field(description="Source-owned restriction scope.")
    restriction_code: str = Field(description="Bounded source-owned restriction code.")
    restriction_status: str = Field(description="Source-owned restriction lifecycle status.")
    restriction_source: str = Field(description="Source channel that captured the restriction.")
    applies_to_buy: bool = Field(description="Whether the restriction applies to buy actions.")
    applies_to_sell: bool = Field(description="Whether the restriction applies to sell actions.")
    instrument_ids: list[str] = Field(default_factory=list)
    asset_classes: list[str] = Field(default_factory=list)
    issuer_ids: list[str] = Field(default_factory=list)
    country_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Restriction effective start date.")
    effective_to: date | None = Field(default=None, description="Restriction effective end date.")
    restriction_version: int = Field(description="Selected restriction profile version.")
    source_record_id: str | None = Field(default=None, description="Source record id for replay.")


class AuthoritativeClientRestrictionContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Source-owner supportability status for client restriction evidence."
    )
    source_system: str = Field(description="Source system that owns restriction evidence.")
    source_product_name: str = Field(default="ClientRestrictionProfile")
    source_product_version: str = Field(default="v1")
    source_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    portfolio_id: str = Field(description="Portfolio identifier used to resolve the profile.")
    client_id: str = Field(description="Client identifier bound to the profile.")
    mandate_id: str | None = Field(default=None)
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    restriction_count: int = Field(ge=0)
    missing_data_families: list[str] = Field(default_factory=list)
    restrictions: list[AuthoritativeClientRestrictionRule] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class AuthoritativeSustainabilityPreference(BaseModel):
    preference_framework: str = Field(description="Source-owned sustainability framework.")
    preference_code: str = Field(description="Bounded sustainability preference code.")
    preference_status: str = Field(description="Source-owned preference lifecycle status.")
    preference_source: str = Field(description="Source channel that captured the preference.")
    minimum_allocation: Decimal | None = Field(default=None)
    maximum_allocation: Decimal | None = Field(default=None)
    applies_to_asset_classes: list[str] = Field(default_factory=list)
    exclusion_codes: list[str] = Field(default_factory=list)
    positive_tilt_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Preference effective start date.")
    effective_to: date | None = Field(default=None, description="Preference effective end date.")
    preference_version: int = Field(description="Selected preference profile version.")
    source_record_id: str | None = Field(default=None, description="Source record id for replay.")


class AuthoritativeSustainabilityPreferenceContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Source-owner supportability status for sustainability preference evidence."
    )
    source_system: str = Field(description="Source system that owns sustainability preferences.")
    source_product_name: str = Field(default="SustainabilityPreferenceProfile")
    source_product_version: str = Field(default="v1")
    source_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    portfolio_id: str = Field(description="Portfolio identifier used to resolve the profile.")
    client_id: str = Field(description="Client identifier bound to the profile.")
    mandate_id: str | None = Field(default=None)
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    preference_count: int = Field(ge=0)
    missing_data_families: list[str] = Field(default_factory=list)
    preferences: list[AuthoritativeSustainabilityPreference] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class AuthoritativeLiquidityCashflowProjection(BaseModel):
    source_product_name: str = Field(
        description="Source-owned cashflow projection data product name.",
        examples=["PortfolioCashflowProjection"],
    )
    source_product_version: str = Field(
        description="Source-owned cashflow projection data product version.",
        examples=["v1"],
    )
    source_system: str = Field(
        description="Authoritative source system that produced the cashflow projection.",
        examples=["lotus-core"],
    )
    total_net_cashflow: Money = Field(
        description="Source-owned total projected net cashflow over the projection window."
    )
    projection_start: date | None = Field(
        default=None,
        description="Inclusive projection-window start date when supplied by the source product.",
        examples=["2026-05-03"],
    )
    projection_end: date | None = Field(
        default=None,
        description="Inclusive projection-window end date when supplied by the source product.",
        examples=["2026-06-03"],
    )
    include_projected: bool = Field(
        description=(
            "Whether the source product included projected future rows in total_net_cashflow."
        ),
        examples=[True],
    )
    latest_evidence_timestamp: datetime | None = Field(
        default=None,
        description="Latest source evidence timestamp represented in the projection.",
    )
    source_batch_fingerprint: str | None = Field(
        default=None,
        description="Source-owned deterministic fingerprint for the projection batch.",
        examples=["cashflow-projection:PB_SG_GLOBAL_BAL_001:2026-05-03"],
    )
    data_quality_status: ConstructionMethodStatus = Field(
        default=ConstructionMethodStatus.READY,
        description="Source-owner data quality posture for this projection.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Source-owner bounded reason codes for cashflow projection posture.",
    )


class AuthoritativeLiquidityContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Liquidity and settlement supportability status for the alternative."
    )
    source_system: str = Field(description="Authority or policy source for liquidity evidence.")
    policy_id: str = Field(description="Liquidity policy identifier applied to this construction.")
    minimum_cash_weight: Decimal = Field(
        description="Minimum post-trade cash weight required by policy."
    )
    allowed_liquidity_tiers: list[str] = Field(
        default_factory=list,
        description="Instrument liquidity tiers eligible for buy-side construction.",
    )
    cashflow_projection: AuthoritativeLiquidityCashflowProjection | None = Field(
        default=None,
        description=(
            "Optional lotus-core PortfolioCashflowProjection:v1 evidence used to evaluate "
            "future cash pressure against the liquidity policy. Absence preserves the "
            "settlement/current-cash-only liquidity behavior."
        ),
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Liquidity-authoritative bounded reason codes.",
    )


class AuthoritativeCurrencyOverlayContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Currency-overlay policy supportability status."
    )
    source_system: str = Field(description="Authority or policy source for currency evidence.")
    policy_id: str = Field(description="Currency-overlay or hedge-policy identifier.")
    hedge_ratio_min: Decimal = Field(description="Minimum target hedge ratio.")
    hedge_ratio_max: Decimal = Field(description="Maximum target hedge ratio.")
    eligible_currencies: list[str] = Field(
        default_factory=list,
        description="Currencies eligible for overlay treatment.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Currency-overlay bounded reason codes.",
    )


class AuthoritativeRegimeStressContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Scenario-pack supportability status for regime stress construction."
    )
    source_system: str = Field(description="Risk or CIO scenario-pack authority.")
    scenario_pack_id: str = Field(description="Scenario pack identifier used for construction.")
    worst_case_loss_pct: Decimal = Field(
        description="Worst expected loss across scenario pack as a portfolio ratio."
    )
    maximum_allowed_loss_pct: Decimal = Field(
        description="Maximum permitted scenario loss ratio for the mandate."
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Regime/stress bounded reason codes.",
    )


class ConstructionAuthorityContext(BaseModel):
    risk_context: AuthoritativeRiskContext | None = Field(
        default=None,
        description="Optional lotus-risk authoritative concentration/risk context.",
    )
    performance_context: "AuthoritativePerformanceContext | None" = Field(
        default=None,
        description="Optional lotus-performance authoritative benchmark/performance context.",
    )
    transaction_cost_context: AuthoritativeTransactionCostContext | None = Field(
        default=None,
        description="Optional lotus-core TransactionCostCurve:v1 observed transaction-cost context.",
    )
    client_restriction_context: AuthoritativeClientRestrictionContext | None = Field(
        default=None,
        description="Optional lotus-core ClientRestrictionProfile:v1 restriction context.",
    )
    sustainability_preference_context: AuthoritativeSustainabilityPreferenceContext | None = Field(
        default=None,
        description=(
            "Optional lotus-core SustainabilityPreferenceProfile:v1 sustainability preference "
            "context."
        ),
    )
    liquidity_context: AuthoritativeLiquidityContext | None = Field(
        default=None,
        description="Optional liquidity and settlement authority context.",
    )
    currency_overlay_context: AuthoritativeCurrencyOverlayContext | None = Field(
        default=None,
        description="Optional currency-overlay and hedge-policy authority context.",
    )
    regime_stress_context: AuthoritativeRegimeStressContext | None = Field(
        default=None,
        description="Optional risk/CIO scenario-pack context.",
    )


class AuthoritativePerformanceContext(BaseModel):
    supportability_status: ConstructionMethodStatus = Field(
        description="Performance-service supportability status for the enrichment."
    )
    source_system: str = Field(description="Performance authority that produced the enrichment.")
    source_product_name: str | None = Field(
        default=None,
        description="Source-owned performance product name when the authority exposes one.",
    )
    source_product_version: str | None = Field(
        default=None,
        description="Source-owned performance product version when available.",
    )
    source_id: str | None = Field(
        default=None,
        description="Source-owned performance evidence identifier or calculation fingerprint.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical source-owned evidence hash when available.",
    )
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
