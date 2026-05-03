from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.core.dpm_source_context import (
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
)


class MandateHealthState(str, Enum):
    READY = "READY"
    PENDING_REVIEW = "PENDING_REVIEW"
    BLOCKED = "BLOCKED"


class MandateHealthDimension(str, Enum):
    SOURCE_READINESS = "SOURCE_READINESS"
    ALLOCATION_DRIFT = "ALLOCATION_DRIFT"
    RISK_DRIFT = "RISK_DRIFT"
    CASH_LIQUIDITY = "CASH_LIQUIDITY"
    TAX_TURNOVER = "TAX_TURNOVER"
    ELIGIBILITY_RESTRICTIONS = "ELIGIBILITY_RESTRICTIONS"
    PERFORMANCE_ATTENTION = "PERFORMANCE_ATTENTION"
    WORKFLOW_READINESS = "WORKFLOW_READINESS"
    REVIEW_CADENCE = "REVIEW_CADENCE"
    MODEL_FRESHNESS = "MODEL_FRESHNESS"


class MandateRecommendedAction(str, Enum):
    NONE = "NONE"
    SIMULATE_REBALANCE = "SIMULATE_REBALANCE"
    REVIEW_MANDATE = "REVIEW_MANDATE"
    FIX_SOURCE_DATA = "FIX_SOURCE_DATA"
    REVIEW_RESTRICTION = "REVIEW_RESTRICTION"
    REVIEW_WORKFLOW = "REVIEW_WORKFLOW"


class MonitoringSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


DIMENSION_WEIGHTS: dict[MandateHealthDimension, int] = {
    MandateHealthDimension.SOURCE_READINESS: 15,
    MandateHealthDimension.ALLOCATION_DRIFT: 18,
    MandateHealthDimension.RISK_DRIFT: 12,
    MandateHealthDimension.CASH_LIQUIDITY: 10,
    MandateHealthDimension.TAX_TURNOVER: 10,
    MandateHealthDimension.ELIGIBILITY_RESTRICTIONS: 10,
    MandateHealthDimension.PERFORMANCE_ATTENTION: 8,
    MandateHealthDimension.WORKFLOW_READINESS: 7,
    MandateHealthDimension.REVIEW_CADENCE: 5,
    MandateHealthDimension.MODEL_FRESHNESS: 5,
}


def _bounded_ratio(value: Decimal, *, field_name: str) -> Decimal:
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def _score_from_penalty(penalty: Decimal) -> int:
    bounded_penalty = min(max(penalty, Decimal("0")), Decimal("100"))
    return int((Decimal("100") - bounded_penalty).quantize(Decimal("1"), ROUND_HALF_UP))


class DpmMandateConstraintSet(BaseModel):
    cash_band_min_weight: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    cash_band_max_weight: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    single_position_max_weight: Optional[Decimal] = Field(default=None)
    issuer_max_weight: Optional[Decimal] = Field(default=None)
    sector_max_weight: Optional[Decimal] = Field(default=None)
    region_max_weight: Optional[Decimal] = Field(default=None)
    currency_max_weight: Optional[Decimal] = Field(default=None)
    turnover_budget: Optional[Decimal] = Field(default=None)
    tax_budget_base: Optional[Decimal] = Field(default=None)
    max_tracking_error: Optional[Decimal] = Field(default=None)
    max_active_share: Optional[Decimal] = Field(default=None)
    minimum_trade_notional: Optional[Decimal] = Field(default=None, ge=0)
    allowed_product_types: list[str] = Field(default_factory=list)
    restricted_instruments: list[str] = Field(default_factory=list)
    restricted_issuers: list[str] = Field(default_factory=list)
    restricted_sectors: list[str] = Field(default_factory=list)
    sustainability_exclusions: list[str] = Field(default_factory=list)

    @field_validator(
        "single_position_max_weight",
        "issuer_max_weight",
        "sector_max_weight",
        "region_max_weight",
        "currency_max_weight",
        "turnover_budget",
        "max_tracking_error",
        "max_active_share",
    )
    @classmethod
    def validate_optional_ratio(
        cls,
        value: Optional[Decimal],
        info: ValidationInfo,
    ) -> Optional[Decimal]:
        if value is None:
            return value
        return _bounded_ratio(value, field_name=info.field_name or "ratio")

    @model_validator(mode="after")
    def validate_cash_band(self) -> "DpmMandateConstraintSet":
        if self.cash_band_min_weight > self.cash_band_max_weight:
            raise ValueError("cash_band_min_weight must not exceed cash_band_max_weight")
        return self


class DpmMandatePreferences(BaseModel):
    sustainability_strategy: Optional[str] = Field(default=None)
    income_priority: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(default=None)
    bespoke_notes: list[str] = Field(default_factory=list)


class DpmMandateReviewPolicy(BaseModel):
    review_frequency: str = Field(default="QUARTERLY")
    last_review_date: Optional[date] = Field(default=None)
    next_review_due_date: Optional[date] = Field(default=None)


class DpmSourceProductLineage(BaseModel):
    product_name: str
    product_version: str
    source_system: str = Field(default="lotus-core")
    source_record_id: Optional[str] = Field(default=None)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    lineage: dict[str, str] = Field(default_factory=dict)


class DpmMandateDigitalTwin(BaseModel):
    mandate_id: str
    portfolio_id: str
    mandate_version: str
    as_of_date: date
    source_system: str = Field(default="lotus-core")
    base_currency: str
    reference_currency: str
    risk_profile: str
    investment_objective: str
    time_horizon: str
    model_portfolio_id: str
    model_portfolio_version: Optional[str] = Field(default=None)
    benchmark_id: Optional[str] = Field(default=None)
    constraints: DpmMandateConstraintSet
    preferences: DpmMandatePreferences = Field(default_factory=DpmMandatePreferences)
    review_policy: DpmMandateReviewPolicy
    source_lineage: list[DpmSourceProductLineage] = Field(default_factory=list)
    field_gap_codes: list[str] = Field(default_factory=list)


class DpmMandateHealthReason(BaseModel):
    dimension: MandateHealthDimension
    reason_code: str
    severity: MonitoringSeverity
    message: str
    recommended_action: MandateRecommendedAction


class DpmMandateDimensionScore(BaseModel):
    dimension: MandateHealthDimension
    weight: int
    score: int = Field(ge=0, le=100)
    state: MandateHealthState
    reason_code: str
    measured_value: Optional[Decimal | str | int] = Field(default=None)
    threshold_value: Optional[Decimal | str | int] = Field(default=None)
    evidence_refs: list[str] = Field(default_factory=list)


class DpmMandateHealthInput(BaseModel):
    twin: DpmMandateDigitalTwin
    current_weights: dict[str, Decimal] = Field(default_factory=dict)
    target_weights: dict[str, Decimal] = Field(default_factory=dict)
    cash_weight: Decimal = Field(default=Decimal("0"), ge=0)
    source_readiness_state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = "READY"
    missing_source_families: list[str] = Field(default_factory=list)
    degraded_source_families: list[str] = Field(default_factory=list)
    stale_source_families: list[str] = Field(default_factory=list)
    restricted_held_instruments: list[str] = Field(default_factory=list)
    tax_lot_missing_security_ids: list[str] = Field(default_factory=list)
    turnover_budget_used: Optional[Decimal] = Field(default=None)
    tax_budget_used_base: Optional[Decimal] = Field(default=None)
    tracking_error: Optional[Decimal] = Field(default=None)
    performance_under_review: bool = False
    workflow_blocked: bool = False
    approval_required: bool = False
    model_effective_to: Optional[date] = Field(default=None)


class DpmMandateHealthSnapshot(BaseModel):
    health_snapshot_id: str
    mandate_id: str
    portfolio_id: str
    as_of_date: date
    calculated_at: datetime
    health_score: int = Field(ge=0, le=100)
    health_state: MandateHealthState
    dimension_scores: list[DpmMandateDimensionScore]
    top_reasons: list[DpmMandateHealthReason]
    recommended_action: MandateRecommendedAction
    source_readiness_state: str
    evidence_refs: list[str] = Field(default_factory=list)


class DpmMonitoringException(BaseModel):
    exception_id: str
    mandate_id: str
    portfolio_id: str
    detected_at: datetime
    as_of_date: date
    dimension: MandateHealthDimension
    severity: MonitoringSeverity
    reason_code: str
    state: Literal["ACTIVE", "RESOLVED"] = "ACTIVE"
    recommended_action: MandateRecommendedAction
    measured_value: Optional[Decimal | str | int] = None
    threshold_value: Optional[Decimal | str | int] = None
    source_lineage: list[DpmSourceProductLineage] = Field(default_factory=list)
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None


class DpmMonitoringRun(BaseModel):
    monitoring_run_id: str = Field(
        description="Stable monitoring run identifier.",
        examples=["dmr_20260503_083000"],
    )
    as_of_date: date = Field(
        description="Business date used to evaluate mandate health.",
        examples=["2026-05-03"],
    )
    requested_at: datetime = Field(
        description="UTC timestamp when monitoring was requested.",
        examples=["2026-05-03T08:30:00Z"],
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when monitoring completed.",
        examples=["2026-05-03T08:30:02Z"],
    )
    status: Literal["SUCCEEDED", "FAILED"] = Field(
        description="Monitoring run terminal status.",
        examples=["SUCCEEDED"],
    )
    mandate_ids: list[str] = Field(
        default_factory=list,
        description="Mandate ids included in the monitoring run.",
        examples=[["MANDATE_PB_SG_GLOBAL_BAL_001"]],
    )
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="Caller-supplied monitoring filters used for audit and replay.",
        examples=[{"tenant_id": "default"}],
    )
    total_mandates: int = Field(
        ge=0,
        description="Number of mandates evaluated by this monitoring run.",
        examples=[1],
    )
    health_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of evaluated mandates by health state.",
        examples=[{"READY": 0, "PENDING_REVIEW": 1, "BLOCKED": 0}],
    )
    exception_count: int = Field(
        ge=0,
        description="Number of monitoring exceptions generated or refreshed.",
        examples=[1],
    )
    source_readiness_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of evaluated mandates by source-readiness state.",
        examples=[{"READY": 1}],
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Bounded failure reason when the monitoring run failed.",
        examples=["MANDATE_NOT_FOUND"],
    )


class DpmCommandCenterAttentionBucket(BaseModel):
    dimension: MandateHealthDimension = Field(
        description="Mandate health dimension driving the attention bucket.",
        examples=["SOURCE_READINESS"],
    )
    severity: MonitoringSeverity = Field(
        description="Highest monitoring severity represented by this bucket.",
        examples=["CRITICAL"],
    )
    recommended_action: MandateRecommendedAction = Field(
        description="Primary action expected from PM, supervision, operations, or data ownership.",
        examples=["FIX_SOURCE_DATA"],
    )
    exception_count: int = Field(
        ge=0,
        description="Number of active exceptions in this bucket.",
        examples=[3],
    )
    top_reason_codes: list[str] = Field(
        default_factory=list,
        description="Most frequent bounded reason codes represented by this bucket.",
        examples=[["SOURCE_READINESS_BLOCKED"]],
    )


class DpmCommandCenterRecommendedAction(BaseModel):
    recommended_action: MandateRecommendedAction = Field(
        description="Action recommended for the PM book.",
        examples=["SIMULATE_REBALANCE"],
    )
    exception_count: int = Field(
        ge=0,
        description="Number of active exceptions supporting this recommended action.",
        examples=[2],
    )
    highest_severity: MonitoringSeverity = Field(
        description="Highest severity among exceptions supporting this action.",
        examples=["WARNING"],
    )


class DpmCommandCenterSupportability(BaseModel):
    data_completeness_state: Literal["COMPLETE", "PARTIAL", "EMPTY"] = Field(
        description="Whether command-center data is complete, partial, or empty for the query.",
        examples=["PARTIAL"],
    )
    generated_at: datetime = Field(
        description="UTC timestamp when the command-center response was generated.",
        examples=["2026-05-03T08:30:00Z"],
    )
    source_run_id: Optional[str] = Field(
        default=None,
        description="Monitoring run id used as the primary source for book-level aggregation.",
        examples=["dmr_20260503_083000"],
    )
    partial_readiness_reasons: list[str] = Field(
        default_factory=list,
        description="Explicit reasons explaining partial or empty command-center readiness.",
        examples=[["PM_BOOK_DISCOVERY_NOT_YET_SOURCED"]],
    )


class DpmCommandCenterSummary(BaseModel):
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant filter used for the command-center summary.",
        examples=["default"],
    )
    portfolio_manager_id: Optional[str] = Field(
        default=None,
        description="Portfolio-manager filter used for the command-center summary.",
        examples=["PM_SG_DPM_001"],
    )
    book_id: Optional[str] = Field(
        default=None,
        description="PM book filter used for the command-center summary.",
        examples=["BOOK_SG_BALANCED_DPM"],
    )
    as_of_date: Optional[date] = Field(
        default=None,
        description="Business date represented by the command-center summary.",
        examples=["2026-05-03"],
    )
    selected_health_state: Optional[MandateHealthState] = Field(
        default=None,
        description="Optional health-state filter applied to the displayed distribution.",
        examples=["PENDING_REVIEW"],
    )
    evaluated_mandates: int = Field(
        ge=0,
        description="Number of mandates represented by the selected monitoring run.",
        examples=[42],
    )
    monitored_mandate_ids: list[str] = Field(
        default_factory=list,
        description="Mandate ids represented by the selected monitoring run.",
        examples=[["MANDATE_PB_SG_GLOBAL_BAL_001"]],
    )
    health_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Mandate count by health state for the selected run.",
        examples=[{"READY": 25, "PENDING_REVIEW": 14, "BLOCKED": 3}],
    )
    source_readiness_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Mandate count by source-readiness state for the selected run.",
        examples=[{"READY": 39, "PARTIAL": 3}],
    )
    active_exception_count: int = Field(
        ge=0,
        description="Number of active monitoring exceptions represented by the command center.",
        examples=[5],
    )
    attention_buckets: list[DpmCommandCenterAttentionBucket] = Field(
        default_factory=list,
        description="Aggregated active exception buckets ordered by severity and exception count.",
    )
    recommended_actions: list[DpmCommandCenterRecommendedAction] = Field(
        default_factory=list,
        description="Aggregated action queue ordered by severity and exception count.",
    )
    latest_monitoring_run: Optional[DpmMonitoringRun] = Field(
        default=None,
        description="Latest monitoring run selected for this command-center summary.",
    )
    supportability: DpmCommandCenterSupportability = Field(
        description="Supportability block explaining response completeness and evidence source.",
    )


def compile_mandate_digital_twin_from_core(
    *,
    mandate: DpmCoreMandateBindingResponse,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    as_of_date: date,
    reference_currency: Optional[str] = None,
) -> DpmMandateDigitalTwin:
    """Compile the minimum viable mandate twin from current RFC-087 core products."""

    field_gaps = [
        "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED",
        "CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED",
        "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED",
        "PORTFOLIO_CASHFLOW_FORECAST_NOT_YET_SOURCED",
    ]
    cash_reserve_weight = mandate.rebalance_bands.cash_reserve_weight or Decimal("0")
    constraints = DpmMandateConstraintSet(
        cash_band_min_weight=cash_reserve_weight,
        cash_band_max_weight=max(cash_reserve_weight, Decimal("0.10")),
        turnover_budget=Decimal("0.15"),
    )
    return DpmMandateDigitalTwin(
        mandate_id=mandate.mandate_id,
        portfolio_id=mandate.portfolio_id,
        mandate_version=str(mandate.binding_version),
        as_of_date=as_of_date,
        base_currency=model_targets.base_currency,
        reference_currency=reference_currency or model_targets.base_currency,
        risk_profile=mandate.risk_profile.upper(),
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon=mandate.investment_horizon.upper(),
        model_portfolio_id=mandate.model_portfolio_id,
        model_portfolio_version=model_targets.model_portfolio_version,
        constraints=constraints,
        review_policy=DpmMandateReviewPolicy(review_frequency=mandate.rebalance_frequency.upper()),
        source_lineage=[
            _lineage_from_core_product(
                product_name=mandate.product_name,
                product_version=mandate.product_version,
                lineage=mandate.lineage,
                data_quality_status=mandate.data_quality_status,
                latest_evidence_timestamp=mandate.latest_evidence_timestamp,
            ),
            _lineage_from_core_product(
                product_name=model_targets.product_name,
                product_version=model_targets.product_version,
                lineage=model_targets.lineage,
                data_quality_status=model_targets.data_quality_status,
                latest_evidence_timestamp=model_targets.latest_evidence_timestamp,
            ),
        ],
        field_gap_codes=field_gaps,
    )


def build_health_input_from_core_sources(
    *,
    twin: DpmMandateDigitalTwin,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    market_data_coverage: Optional[DpmCoreMarketDataCoverageWindowResponse] = None,
) -> DpmMandateHealthInput:
    missing_sources: list[str] = []
    degraded_sources: list[str] = []
    stale_sources: list[str] = []
    readiness_state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = "READY"
    if market_data_coverage is not None:
        readiness_state = market_data_coverage.supportability.state
        missing_sources.extend(market_data_coverage.supportability.missing_instrument_ids)
        missing_sources.extend(market_data_coverage.supportability.missing_currency_pairs)
        stale_sources.extend(market_data_coverage.supportability.stale_instrument_ids)
        stale_sources.extend(market_data_coverage.supportability.stale_currency_pairs)
        if readiness_state == "DEGRADED":
            degraded_sources.append("MARKET_DATA_COVERAGE")

    return DpmMandateHealthInput(
        twin=twin,
        target_weights={
            target.instrument_id: target.target_weight for target in model_targets.targets
        },
        source_readiness_state=readiness_state,
        missing_source_families=missing_sources,
        degraded_source_families=degraded_sources,
        stale_source_families=stale_sources,
        model_effective_to=model_targets.effective_to,
    )


def calculate_mandate_health(input_: DpmMandateHealthInput) -> DpmMandateHealthSnapshot:
    dimension_scores = [
        _score_source_readiness(input_),
        _score_allocation_drift(input_),
        _score_risk_drift(input_),
        _score_cash_liquidity(input_),
        _score_tax_turnover(input_),
        _score_eligibility_restrictions(input_),
        _score_performance_attention(input_),
        _score_workflow_readiness(input_),
        _score_review_cadence(input_),
        _score_model_freshness(input_),
    ]
    weighted = sum(
        Decimal(score.score) * Decimal(score.weight) for score in dimension_scores
    ) / Decimal("100")
    hard_block = any(score.state == MandateHealthState.BLOCKED for score in dimension_scores)
    pending = any(score.state == MandateHealthState.PENDING_REVIEW for score in dimension_scores)
    health_state = (
        MandateHealthState.BLOCKED
        if hard_block
        else MandateHealthState.PENDING_REVIEW
        if pending
        else MandateHealthState.READY
    )
    reasons = [_reason_from_score(score) for score in dimension_scores if score.score < 100]
    reasons.sort(key=lambda reason: _severity_rank(reason.severity), reverse=True)
    recommended_action = _overall_recommended_action(health_state, reasons)
    return DpmMandateHealthSnapshot(
        health_snapshot_id=(
            f"mh_{input_.twin.as_of_date.strftime('%Y%m%d')}_{input_.twin.portfolio_id.lower()}"
        ),
        mandate_id=input_.twin.mandate_id,
        portfolio_id=input_.twin.portfolio_id,
        as_of_date=input_.twin.as_of_date,
        calculated_at=datetime.now(timezone.utc),
        health_score=int(weighted.quantize(Decimal("1"), ROUND_HALF_UP)),
        health_state=health_state,
        dimension_scores=dimension_scores,
        top_reasons=reasons[:5],
        recommended_action=recommended_action,
        source_readiness_state=input_.source_readiness_state,
        evidence_refs=[
            lineage.source_record_id
            for lineage in input_.twin.source_lineage
            if lineage.source_record_id
        ],
    )


def monitoring_exceptions_from_health(
    snapshot: DpmMandateHealthSnapshot,
    *,
    source_lineage: list[DpmSourceProductLineage],
) -> list[DpmMonitoringException]:
    detected_at = snapshot.calculated_at
    exceptions: list[DpmMonitoringException] = []
    for reason in snapshot.top_reasons:
        exceptions.append(
            DpmMonitoringException(
                exception_id=(
                    f"me_{snapshot.as_of_date.strftime('%Y%m%d')}_"
                    f"{snapshot.portfolio_id.lower()}_{reason.dimension.value.lower()}"
                ),
                mandate_id=snapshot.mandate_id,
                portfolio_id=snapshot.portfolio_id,
                detected_at=detected_at,
                as_of_date=snapshot.as_of_date,
                dimension=reason.dimension,
                severity=reason.severity,
                reason_code=reason.reason_code,
                recommended_action=reason.recommended_action,
                source_lineage=source_lineage,
            )
        )
    return exceptions


def _lineage_from_core_product(
    *,
    product_name: str,
    product_version: str,
    lineage: dict[str, str],
    data_quality_status: Optional[str],
    latest_evidence_timestamp: Optional[datetime],
) -> DpmSourceProductLineage:
    return DpmSourceProductLineage(
        product_name=product_name,
        product_version=product_version,
        source_record_id=lineage.get("source_record_id") or lineage.get("contract_version"),
        lineage=lineage,
        data_quality_status=data_quality_status,
        latest_evidence_timestamp=latest_evidence_timestamp,
    )


def _ready_score(dimension: MandateHealthDimension) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=100,
        state=MandateHealthState.READY,
        reason_code=f"{dimension.value}_READY",
    )


def _attention_score(
    *,
    dimension: MandateHealthDimension,
    score: int,
    state: MandateHealthState,
    reason_code: str,
    measured_value: Optional[Decimal | str | int] = None,
    threshold_value: Optional[Decimal | str | int] = None,
) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=max(0, min(score, 100)),
        state=state,
        reason_code=reason_code,
        measured_value=measured_value,
        threshold_value=threshold_value,
    )


def _score_source_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if (
        input_.source_readiness_state in {"INCOMPLETE", "UNAVAILABLE"}
        or input_.missing_source_families
    ):
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="DPM_SOURCE_INCOMPLETE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    if input_.source_readiness_state == "DEGRADED" or input_.stale_source_families:
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="DPM_SOURCE_STALE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    return _ready_score(MandateHealthDimension.SOURCE_READINESS)


def _score_allocation_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if not input_.current_weights or not input_.target_weights:
        return _attention_score(
            dimension=MandateHealthDimension.ALLOCATION_DRIFT,
            score=85,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="ALLOCATION_DRIFT_NOT_ASSESSED",
        )
    default_band = Decimal("0.025")
    max_drift = max(
        (
            abs(input_.current_weights.get(instrument_id, Decimal("0")) - target_weight)
            for instrument_id, target_weight in input_.target_weights.items()
        ),
        default=Decimal("0"),
    )
    if max_drift <= default_band:
        return _ready_score(MandateHealthDimension.ALLOCATION_DRIFT)
    score = _score_from_penalty((max_drift - default_band) * Decimal("1000"))
    return _attention_score(
        dimension=MandateHealthDimension.ALLOCATION_DRIFT,
        score=score,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="ALLOCATION_DRIFT",
        measured_value=max_drift,
        threshold_value=default_band,
    )


def _score_risk_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.tracking_error is None or input_.twin.constraints.max_tracking_error is None:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    if input_.tracking_error <= input_.twin.constraints.max_tracking_error:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    return _attention_score(
        dimension=MandateHealthDimension.RISK_DRIFT,
        score=65,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="TRACKING_ERROR_ABOVE_LIMIT",
        measured_value=input_.tracking_error,
        threshold_value=input_.twin.constraints.max_tracking_error,
    )


def _score_cash_liquidity(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    constraints = input_.twin.constraints
    if input_.cash_weight < constraints.cash_band_min_weight:
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=60,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_BELOW_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_min_weight,
        )
    if input_.cash_weight > constraints.cash_band_max_weight:
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=75,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_ABOVE_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_max_weight,
        )
    return _ready_score(MandateHealthDimension.CASH_LIQUIDITY)


def _score_tax_turnover(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.tax_lot_missing_security_ids:
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=40,
            state=MandateHealthState.BLOCKED,
            reason_code="TAX_LOTS_INCOMPLETE",
            measured_value=len(input_.tax_lot_missing_security_ids),
            threshold_value=0,
        )
    if (
        input_.turnover_budget_used is not None
        and input_.twin.constraints.turnover_budget is not None
        and input_.turnover_budget_used >= input_.twin.constraints.turnover_budget * Decimal("0.8")
    ):
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="TURNOVER_BUDGET_NEAR_LIMIT",
            measured_value=input_.turnover_budget_used,
            threshold_value=input_.twin.constraints.turnover_budget,
        )
    return _ready_score(MandateHealthDimension.TAX_TURNOVER)


def _score_eligibility_restrictions(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    restricted = set(input_.restricted_held_instruments)
    restricted.update(
        instrument_id
        for instrument_id in input_.current_weights
        if instrument_id in set(input_.twin.constraints.restricted_instruments)
    )
    if restricted:
        return _attention_score(
            dimension=MandateHealthDimension.ELIGIBILITY_RESTRICTIONS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="RESTRICTED_INSTRUMENT_HELD",
            measured_value=len(restricted),
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.ELIGIBILITY_RESTRICTIONS)


def _score_performance_attention(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.performance_under_review:
        return _attention_score(
            dimension=MandateHealthDimension.PERFORMANCE_ATTENTION,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="PERFORMANCE_UNDER_REVIEW",
        )
    return _ready_score(MandateHealthDimension.PERFORMANCE_ATTENTION)


def _score_workflow_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.workflow_blocked:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="REBALANCE_RUN_BLOCKED",
        )
    if input_.approval_required:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="APPROVAL_REQUIRED",
        )
    return _ready_score(MandateHealthDimension.WORKFLOW_READINESS)


def _score_review_cadence(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    due_date = input_.twin.review_policy.next_review_due_date
    if due_date is not None and due_date < input_.twin.as_of_date:
        days_overdue = (input_.twin.as_of_date - due_date).days
        return _attention_score(
            dimension=MandateHealthDimension.REVIEW_CADENCE,
            score=65,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MANDATE_REVIEW_OVERDUE",
            measured_value=days_overdue,
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.REVIEW_CADENCE)


def _score_model_freshness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.model_effective_to is not None and input_.model_effective_to < input_.twin.as_of_date:
        return _attention_score(
            dimension=MandateHealthDimension.MODEL_FRESHNESS,
            score=55,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MODEL_VERSION_STALE",
            measured_value=input_.model_effective_to.isoformat(),
            threshold_value=input_.twin.as_of_date.isoformat(),
        )
    return _ready_score(MandateHealthDimension.MODEL_FRESHNESS)


def _reason_from_score(score: DpmMandateDimensionScore) -> DpmMandateHealthReason:
    severity = (
        MonitoringSeverity.CRITICAL
        if score.state == MandateHealthState.BLOCKED
        else MonitoringSeverity.WARNING
    )
    return DpmMandateHealthReason(
        dimension=score.dimension,
        reason_code=score.reason_code,
        severity=severity,
        message=f"{score.dimension.value} requires attention: {score.reason_code}",
        recommended_action=_recommended_action_for_dimension(score.dimension, score.state),
    )


def _recommended_action_for_dimension(
    dimension: MandateHealthDimension,
    state: MandateHealthState,
) -> MandateRecommendedAction:
    if dimension == MandateHealthDimension.SOURCE_READINESS:
        return MandateRecommendedAction.FIX_SOURCE_DATA
    if dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS:
        return MandateRecommendedAction.REVIEW_RESTRICTION
    if dimension in {
        MandateHealthDimension.WORKFLOW_READINESS,
        MandateHealthDimension.REVIEW_CADENCE,
    }:
        return MandateRecommendedAction.REVIEW_WORKFLOW
    if state == MandateHealthState.PENDING_REVIEW:
        return MandateRecommendedAction.SIMULATE_REBALANCE
    return MandateRecommendedAction.REVIEW_MANDATE


def _overall_recommended_action(
    health_state: MandateHealthState,
    reasons: list[DpmMandateHealthReason],
) -> MandateRecommendedAction:
    if health_state == MandateHealthState.READY:
        return MandateRecommendedAction.NONE
    if reasons:
        return reasons[0].recommended_action
    return MandateRecommendedAction.REVIEW_MANDATE


def _severity_rank(severity: MonitoringSeverity) -> int:
    return {
        MonitoringSeverity.INFO: 0,
        MonitoringSeverity.WARNING: 1,
        MonitoringSeverity.CRITICAL: 2,
    }[severity]


if sum(DIMENSION_WEIGHTS.values()) != 100:
    raise RuntimeError("Mandate health dimension weights must total 100")
