from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional, TypeAlias

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
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

DigitalTwinLineageSourceProduct: TypeAlias = (
    DpmCoreMandateBindingResponse
    | DpmCoreModelPortfolioTargetResponse
    | DpmCoreClientRestrictionProfileResponse
    | DpmCoreSustainabilityPreferenceProfileResponse
    | DpmCorePortfolioCashflowProjectionResponse
    | DpmCoreClientIncomeNeedsScheduleResponse
    | DpmCoreLiquidityReserveRequirementResponse
    | DpmCorePlannedWithdrawalScheduleResponse
)
SourceReadinessState: TypeAlias = Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"]


@dataclass(frozen=True)
class MandateSourceReadinessProjection:
    state: SourceReadinessState
    missing_source_families: list[str]
    degraded_source_families: list[str]
    stale_source_families: list[str]


def bounded_ratio(value: Decimal, *, field_name: str) -> Decimal:
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


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
        return bounded_ratio(value, field_name=info.field_name or "ratio")

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


class DpmMandateSourceHealthContext(BaseModel):
    source_system: Literal["lotus-risk", "lotus-performance"]
    source_product_name: str
    source_product_version: str = "v1"
    health_state: Literal["ready", "attention", "unavailable"]
    threshold_breached: Optional[bool] = None
    request_fingerprint: str
    source_metric: dict[str, object] = Field(default_factory=dict)
    methodology_posture: dict[str, object] = Field(default_factory=dict)
    benchmark_context: dict[str, object] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_source_product_identity(self) -> "DpmMandateSourceHealthContext":
        expected_products = {
            "lotus-risk": "MandateRiskHealthContext",
            "lotus-performance": "MandatePerformanceHealthContext",
        }
        expected_product = expected_products[self.source_system]
        if self.source_product_name != expected_product:
            raise ValueError(f"{self.source_system} context must use {expected_product}")
        if self.source_product_version != "v1":
            raise ValueError("source_product_version must be v1")
        if not self.request_fingerprint.startswith("sha256:"):
            raise ValueError("request_fingerprint must be a sha256 fingerprint")
        return self


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
    restricted_target_instruments: list[str] = Field(default_factory=list)
    sustainability_review_required: bool = False
    projected_net_cashflow: Optional[Decimal] = Field(default=None)
    projected_cashflow_currency: Optional[str] = Field(default=None)
    tax_lot_missing_security_ids: list[str] = Field(default_factory=list)
    turnover_budget_used: Optional[Decimal] = Field(default=None)
    tax_budget_used_base: Optional[Decimal] = Field(default=None)
    tracking_error: Optional[Decimal] = Field(default=None)
    performance_under_review: bool = False
    risk_health_context: Optional[DpmMandateSourceHealthContext] = Field(
        default=None,
        description=(
            "Bounded source-owned lotus-risk MandateRiskHealthContext:v1 posture. Manage "
            "preserves this context and may use its health_state/threshold posture without "
            "recalculating risk methodology."
        ),
    )
    performance_health_context: Optional[DpmMandateSourceHealthContext] = Field(
        default=None,
        description=(
            "Bounded source-owned lotus-performance MandatePerformanceHealthContext:v1 posture. "
            "Manage preserves this context and may use its health_state/threshold posture without "
            "recalculating performance methodology."
        ),
    )
    workflow_blocked: bool = False
    approval_required: bool = False
    model_effective_to: Optional[date] = Field(default=None)

    @model_validator(mode="after")
    def _validate_source_health_context_slots(self) -> "DpmMandateHealthInput":
        if (
            self.risk_health_context is not None
            and self.risk_health_context.source_system != "lotus-risk"
        ):
            raise ValueError("risk_health_context must use lotus-risk MandateRiskHealthContext")
        if (
            self.performance_health_context is not None
            and self.performance_health_context.source_system != "lotus-performance"
        ):
            raise ValueError(
                "performance_health_context must use lotus-performance "
                "MandatePerformanceHealthContext"
            )
        return self


class DpmMandateHealthSourceProductRequirement(BaseModel):
    source_system: str
    source_product_name: str
    source_product_version: str
    required_for_ready: bool = False


class DpmMandateHealthSourceAnalyticsPosture(BaseModel):
    product_family: Literal["MANDATE_HEALTH_RISK_PERFORMANCE_CONTEXT"] = (
        "MANDATE_HEALTH_RISK_PERFORMANCE_CONTEXT"
    )
    risk_tracking_error_supplied: bool
    performance_attention_signal_supplied: bool
    risk_health_context_supplied: bool = False
    performance_health_context_supplied: bool = False
    risk_context_preservation: Literal["SUPPORTED_WHEN_SUPPLIED"] = "SUPPORTED_WHEN_SUPPLIED"
    performance_context_preservation: Literal["SUPPORTED_WHEN_SUPPLIED"] = "SUPPORTED_WHEN_SUPPLIED"
    source_context_preservation: Literal["SOURCE_PRODUCT_CONTEXT_PRESERVED_WHEN_SUPPLIED"] = (
        "SOURCE_PRODUCT_CONTEXT_PRESERVED_WHEN_SUPPLIED"
    )
    required_source_products: list[DpmMandateHealthSourceProductRequirement]
    source_context_refs: list[str] = Field(default_factory=list)
    blocked_capabilities: list[str] = Field(
        default_factory=lambda: [
            "LOCAL_TRACKING_ERROR_CALCULATION",
            "LOCAL_VOLATILITY_CALCULATION",
            "LOCAL_DRAWDOWN_CALCULATION",
            "LOCAL_PERFORMANCE_ATTRIBUTION_CALCULATION",
            "LOCAL_BENCHMARK_RELATIVE_PERFORMANCE_CALCULATION",
        ]
    )
    reason_codes: list[str] = Field(
        default_factory=lambda: [
            "MANDATE_HEALTH_SOURCE_ANALYTICS_PRESERVED_WHEN_SUPPLIED",
            "RISK_PERFORMANCE_METHODOLOGY_REMAINS_SOURCE_OWNED",
        ]
    )


def default_source_analytics_posture() -> DpmMandateHealthSourceAnalyticsPosture:
    return DpmMandateHealthSourceAnalyticsPosture(
        risk_tracking_error_supplied=False,
        performance_attention_signal_supplied=False,
        required_source_products=[
            DpmMandateHealthSourceProductRequirement(
                source_system="lotus-risk",
                source_product_name="MandateRiskHealthContext",
                source_product_version="v1",
                required_for_ready=False,
            ),
            DpmMandateHealthSourceProductRequirement(
                source_system="lotus-performance",
                source_product_name="MandatePerformanceHealthContext",
                source_product_version="v1",
                required_for_ready=False,
            ),
        ],
    )


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
    source_analytics_posture: DpmMandateHealthSourceAnalyticsPosture = Field(
        default_factory=default_source_analytics_posture
    )


class DpmMonitoringException(BaseModel):
    exception_id: str
    monitoring_run_id: Optional[str] = Field(
        default=None,
        description="Monitoring run that generated the exception, when available.",
        examples=["dmr_20260503_083000"],
    )
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
    state: Literal["READY", "PARTIAL", "EMPTY", "DEGRADED", "BLOCKED"] = Field(
        description=(
            "Bounded command-center supportability state derived from command-center "
            "completeness and source-readiness evidence."
        ),
        examples=["READY"],
    )
    data_completeness_state: Literal["COMPLETE", "PARTIAL", "EMPTY"] = Field(
        description="Whether command-center data is complete, partial, or empty for the query.",
        examples=["PARTIAL"],
    )
    reason: str = Field(
        description="Bounded reason explaining the supportability state.",
        examples=["COMMAND_CENTER_READY"],
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
