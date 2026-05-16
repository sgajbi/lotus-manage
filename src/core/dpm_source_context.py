from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field

from src.core.models import (
    BatchRebalanceRequest,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    Money,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Price,
    ShelfEntry,
    SimulationScenario,
    TaxLot,
    ValuationMode,
)


class DpmCorePolicyContext(BaseModel):
    recommended_policy_pack_id: Optional[str] = Field(
        default=None,
        description="Optional policy-pack id recommended by the core source-data resolver.",
    )
    tenant_id: Optional[str] = Field(default=None, description="Resolved tenant selector.")
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Resolved booking-center selector.",
    )
    mandate_id: Optional[str] = Field(default=None, description="Resolved mandate selector.")


class DpmCoreSourceLineage(BaseModel):
    portfolio_snapshot_id: str = Field(description="Core-governed portfolio snapshot id.")
    market_data_snapshot_id: str = Field(description="Core-governed market-data snapshot id.")
    model_portfolio_id: Optional[str] = Field(
        default=None,
        description="Core-governed model portfolio id.",
    )
    model_portfolio_version: Optional[str] = Field(
        default=None,
        description="Core-governed model portfolio version.",
    )
    shelf_version: Optional[str] = Field(
        default=None,
        description="Core-governed product shelf version.",
    )
    integration_policy_version: Optional[str] = Field(
        default=None,
        description="Core integration policy version used to assemble the context.",
    )
    source_lineage_bundle_id: Optional[str] = Field(
        default=None,
        description="Core source-lineage bundle id for audit tie-out.",
    )


class DpmCoreSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Resolver supportability state for this execution context.",
        examples=["READY"],
    )
    reason: str = Field(
        default="DPM_CORE_CONTEXT_READY",
        description="Bounded supportability reason code.",
    )
    freshness_bucket: str = Field(
        default="unknown",
        description="Bounded freshness bucket for the resolved context.",
    )
    missing_source_families: list[str] = Field(
        default_factory=list,
        description="Required source-data families missing from the context.",
    )
    degraded_source_families: list[str] = Field(
        default_factory=list,
        description="Source-data families present but degraded.",
    )


class DpmCoreModelPortfolioTargetRow(BaseModel):
    instrument_id: str = Field(description="Core-governed target instrument identifier.")
    target_weight: Decimal = Field(description="Target instrument weight as a decimal ratio.")
    min_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional lower target band as a decimal ratio.",
    )
    max_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional upper target band as a decimal ratio.",
    )
    target_status: str = Field(description="Target lifecycle status from lotus-core.")
    quality_status: str = Field(description="Data quality status from lotus-core.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for audit and replay.",
    )


class DpmCoreModelPortfolioTargetSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for model target consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    target_count: int = Field(description="Number of target rows returned by lotus-core.")
    total_target_weight: Decimal = Field(description="Sum of returned target weights.")


class DpmCoreModelPortfolioTargetResponse(BaseModel):
    product_name: Literal["DpmModelPortfolioTarget"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    model_portfolio_id: str = Field(description="Core-governed model portfolio identifier.")
    model_portfolio_version: str = Field(description="Core-governed model portfolio version.")
    as_of_date: date = Field(description="As-of date used to resolve the target product.")
    display_name: str = Field(description="Business display name for the model portfolio.")
    base_currency: str = Field(description="Model portfolio base currency.")
    risk_profile: str = Field(description="Mandate risk profile aligned to the model.")
    mandate_type: str = Field(description="Mandate type for which this model is approved.")
    rebalance_frequency: Optional[str] = Field(
        default=None,
        description="Expected rebalance cadence.",
    )
    approval_status: str = Field(description="Approval lifecycle status for the model version.")
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the model version was approved.",
    )
    effective_from: date = Field(description="Resolved model version effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Resolved model version effective end date.",
    )
    targets: list[DpmCoreModelPortfolioTargetRow] = Field(
        description="Resolved target rows from lotus-core."
    )
    supportability: DpmCoreModelPortfolioTargetSupportability = Field(
        description="Completeness and readiness posture for the model target product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreRebalanceBands(BaseModel):
    default_band: Decimal = Field(description="Default rebalance band as a decimal ratio.")
    cash_reserve_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional mandate cash reserve target as a decimal ratio.",
    )


class DpmCoreMandateBindingSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for mandate binding consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="Source families missing from the mandate binding product.",
    )


class DpmCoreMandateBindingResponse(BaseModel):
    product_name: Literal["DiscretionaryMandateBinding"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    mandate_id: str = Field(description="Core-governed discretionary mandate identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_type: str = Field(description="Resolved mandate type.")
    discretionary_authority_status: str = Field(description="Resolved discretionary authority.")
    booking_center_code: str = Field(description="Resolved booking-center code.")
    jurisdiction_code: str = Field(description="Resolved jurisdiction code.")
    model_portfolio_id: str = Field(description="Model portfolio selected by the mandate.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Policy pack selected by the mandate.",
    )
    mandate_objective: Optional[str] = Field(
        default=None,
        description="Source-owned discretionary mandate objective from lotus-core.",
    )
    risk_profile: str = Field(description="Mandate risk profile.")
    investment_horizon: str = Field(description="Mandate investment horizon.")
    review_cadence: Optional[str] = Field(
        default=None,
        description="Source-owned mandate review cadence from lotus-core.",
    )
    last_review_date: Optional[date] = Field(
        default=None,
        description="Most recent completed mandate review date from lotus-core.",
    )
    next_review_due_date: Optional[date] = Field(
        default=None,
        description="Next due mandate review date from lotus-core.",
    )
    leverage_allowed: bool = Field(description="Whether mandate leverage is allowed.")
    tax_awareness_allowed: bool = Field(description="Whether tax-aware execution is allowed.")
    settlement_awareness_required: bool = Field(
        description="Whether settlement-aware execution is required."
    )
    rebalance_frequency: str = Field(description="Mandate rebalance cadence.")
    rebalance_bands: DpmCoreRebalanceBands = Field(
        description="Mandate rebalance bands and cash reserve policy."
    )
    effective_from: date = Field(description="Resolved binding effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Resolved binding effective end date.",
    )
    binding_version: int = Field(description="Resolved binding version.")
    supportability: DpmCoreMandateBindingSupportability = Field(
        description="Completeness and readiness posture for the mandate binding product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreBenchmarkAssignmentResponse(BaseModel):
    product_name: Literal["BenchmarkAssignment"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    benchmark_id: str = Field(description="Core-governed benchmark identifier.")
    as_of_date: date = Field(description="As-of date used to resolve the assignment.")
    effective_from: date = Field(description="Assignment effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Assignment effective end date.",
    )
    assignment_source: str = Field(description="Source channel that established the assignment.")
    assignment_status: str = Field(description="Benchmark assignment lifecycle status.")
    policy_pack_id: Optional[str] = Field(default=None)
    source_system: Optional[str] = Field(default=None)
    assignment_recorded_at: datetime = Field(
        description="Timestamp when the assignment was recorded in lotus-core."
    )
    assignment_version: int = Field(description="Version used for effective-date tie-breaks.")
    contract_version: str = Field(default="rfc_062_v1")
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)


class DpmCorePortfolioManagerBookMember(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    booking_center_code: str = Field(description="Portfolio booking center.")
    portfolio_type: str = Field(description="Portfolio type used for book filtering.")
    status: str = Field(description="Portfolio lifecycle status in the PM book.")
    open_date: Optional[date] = Field(default=None, description="Portfolio open date.")
    close_date: Optional[date] = Field(default=None, description="Portfolio close date.")
    base_currency: Optional[str] = Field(default=None, description="Portfolio base currency.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )


class DpmCorePortfolioManagerBookSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for PM-book membership consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    returned_portfolio_count: int = Field(
        description="Number of portfolio memberships returned by lotus-core."
    )
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Core-applied filters used to resolve the book membership.",
    )


class DpmCorePortfolioManagerBookMembershipResponse(BaseModel):
    product_name: Literal["PortfolioManagerBookMembership"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve the PM book.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    portfolio_manager_id: str = Field(description="Portfolio manager identifier.")
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Optional booking-center filter.",
    )
    members: list[DpmCorePortfolioManagerBookMember] = Field(
        description="Resolved PM-book portfolio memberships from lotus-core."
    )
    supportability: DpmCorePortfolioManagerBookSupportability = Field(
        description="Completeness and readiness posture for PM-book membership."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Core snapshot identifier for the resolved PM-book membership.",
    )


class DpmCoreCioModelChangeAffectedMandate(BaseModel):
    portfolio_id: str = Field(description="Core-governed affected portfolio identifier.")
    mandate_id: str = Field(description="Core-governed affected mandate identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    booking_center_code: str = Field(description="Mandate booking center.")
    jurisdiction_code: str = Field(description="Mandate jurisdiction.")
    discretionary_authority_status: str = Field(
        description="Discretionary authority status selected by lotus-core."
    )
    model_portfolio_id: str = Field(description="Approved model portfolio identifier.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Policy pack associated with the mandate binding.",
    )
    risk_profile: str = Field(description="Mandate risk profile.")
    effective_from: date = Field(description="Mandate binding effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Mandate binding effective end date.",
    )
    binding_version: int = Field(description="Selected mandate binding version.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )


class DpmCoreCioModelChangeSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for CIO model-change cohort consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    returned_mandate_count: int = Field(
        description="Number of affected mandates returned by lotus-core."
    )
    filters_applied: list[str] = Field(
        default_factory=list,
        description="Core-applied filters used to resolve the affected cohort.",
    )


class DpmCoreCioModelChangeAffectedCohortResponse(BaseModel):
    product_name: Literal["CioModelChangeAffectedCohort"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve the cohort.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    model_portfolio_id: str = Field(description="Approved model portfolio identifier.")
    model_portfolio_version: str = Field(description="Approved model portfolio version.")
    model_change_event_id: str = Field(description="Core source-owned model-change event id.")
    approval_state: str = Field(description="Selected model definition approval state.")
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the selected model version was approved.",
    )
    effective_from: date = Field(description="Selected model version effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Selected model version effective end date.",
    )
    affected_mandates: list[DpmCoreCioModelChangeAffectedMandate] = Field(
        description="Resolved affected mandates from lotus-core."
    )
    supportability: DpmCoreCioModelChangeSupportability = Field(
        description="Completeness and readiness posture for CIO model-change discovery."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Core snapshot identifier for the resolved affected cohort.",
    )


class DpmCoreInstrumentEligibilityRecord(BaseModel):
    security_id: str = Field(description="Core-governed security identifier.")
    found: bool = Field(description="Whether lotus-core found an effective eligibility profile.")
    eligibility_status: Literal["APPROVED", "RESTRICTED", "SELL_ONLY", "BANNED", "UNKNOWN"] = Field(
        description="Core-governed instrument eligibility status."
    )
    product_shelf_status: Literal["APPROVED", "RESTRICTED", "SELL_ONLY", "BANNED", "SUSPENDED"] = (
        Field(description="Core product-shelf status.")
    )
    buy_allowed: bool = Field(description="Whether DPM may create buy intents.")
    sell_allowed: bool = Field(description="Whether DPM may create sell intents.")
    restriction_reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded restriction reason codes from lotus-core.",
    )
    settlement_days: Optional[int] = Field(
        default=None,
        description="Instrument settlement cycle in business days.",
    )
    settlement_calendar_id: Optional[str] = Field(
        default=None,
        description="Settlement calendar identifier.",
    )
    liquidity_tier: Optional[Literal["L1", "L2", "L3", "L4", "L5"]] = Field(
        default=None,
        description="Liquidity tier used for suitability and execution controls.",
    )
    issuer_id: Optional[str] = Field(default=None, description="Direct issuer identifier.")
    issuer_name: Optional[str] = Field(default=None, description="Direct issuer name.")
    ultimate_parent_issuer_id: Optional[str] = Field(
        default=None,
        description="Ultimate parent issuer identifier.",
    )
    ultimate_parent_issuer_name: Optional[str] = Field(
        default=None,
        description="Ultimate parent issuer name.",
    )
    asset_class: Optional[str] = Field(default=None, description="Asset-class label.")
    country_of_risk: Optional[str] = Field(default=None, description="Country of risk.")
    effective_from: Optional[date] = Field(default=None, description="Effective start date.")
    effective_to: Optional[date] = Field(default=None, description="Effective end date.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )
    quality_status: str = Field(description="Core row-level data quality status.")


class DpmCoreInstrumentEligibilitySupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for instrument eligibility consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_count: int = Field(description="Number of securities requested.")
    found_count: int = Field(
        validation_alias=AliasChoices("found_count", "resolved_count"),
        description="Number of securities resolved from core source data.",
    )
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without an effective eligibility profile.",
    )


class DpmCoreInstrumentEligibilityBulkResponse(BaseModel):
    product_name: Literal["InstrumentEligibilityProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve eligibility.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    eligibility: list[DpmCoreInstrumentEligibilityRecord] = Field(
        validation_alias=AliasChoices("eligibility", "records"),
        description="Resolved eligibility records in request order.",
    )
    supportability: DpmCoreInstrumentEligibilitySupportability = Field(
        description="Completeness and readiness posture for the eligibility product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreTaxLotPageMetadata(BaseModel):
    page_size: int = Field(description="Maximum tax lots requested from lotus-core.")
    sort_key: str = Field(description="Deterministic sort key used by lotus-core.")
    returned_component_count: int = Field(description="Number of tax lots returned in this page.")
    request_scope_fingerprint: str = Field(description="Opaque request scope fingerprint.")
    next_page_token: Optional[str] = Field(
        default=None,
        description="Opaque continuation token for the next tax-lot page.",
    )


class DpmCorePortfolioTaxLotRecord(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    security_id: str = Field(description="Core-governed security identifier.")
    instrument_id: str = Field(description="Core-governed instrument identifier.")
    lot_id: str = Field(description="Stable core tax-lot identifier.")
    open_quantity: Decimal = Field(description="Current open lot quantity.")
    original_quantity: Decimal = Field(description="Original acquired lot quantity.")
    acquisition_date: date = Field(description="Lot acquisition date.")
    cost_basis_base: Decimal = Field(description="Current lot cost basis in portfolio currency.")
    cost_basis_local: Decimal = Field(description="Current lot cost basis in local trade currency.")
    local_currency: Optional[str] = Field(
        default=None,
        description="Local trade currency for this lot when available.",
    )
    tax_lot_status: Literal["OPEN", "CLOSED"] = Field(description="Current tax-lot status.")
    source_transaction_id: str = Field(description="Core source transaction identifier.")
    source_lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Lot-level core lineage metadata.",
    )


class DpmCorePortfolioTaxLotSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for tax-lot consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_security_count: Optional[int] = Field(
        default=None,
        description="Number of securities explicitly requested from core.",
    )
    returned_lot_count: int = Field(description="Number of tax lots returned in this page.")
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without tax lots after core exhausted the page scope.",
    )


class DpmCorePortfolioTaxLotWindowResponse(BaseModel):
    product_name: Literal["PortfolioTaxLotWindow"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="As-of date used to resolve tax lots.")
    lots: list[DpmCorePortfolioTaxLotRecord] = Field(
        description="Resolved tax lots from lotus-core."
    )
    page: DpmCoreTaxLotPageMetadata = Field(description="Core pagination metadata.")
    supportability: DpmCorePortfolioTaxLotSupportability = Field(
        description="Completeness and readiness posture for tax-lot consumption."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreMarketDataPriceCoverageRecord(BaseModel):
    instrument_id: str = Field(description="Requested instrument identifier.")
    found: bool = Field(description="Whether lotus-core found a price observation.")
    price_date: Optional[date] = Field(default=None, description="Resolved price date.")
    price: Optional[Decimal] = Field(default=None, description="Resolved price value.")
    currency: Optional[str] = Field(default=None, description="Resolved price currency.")
    age_days: Optional[int] = Field(default=None, description="Observation age in days.")
    quality_status: Literal["READY", "STALE", "MISSING"] = Field(
        description="Core price coverage quality status."
    )


class DpmCoreMarketDataFxCoverageRecord(BaseModel):
    from_currency: str = Field(description="Source currency.")
    to_currency: str = Field(description="Target currency.")
    found: bool = Field(description="Whether lotus-core found an FX observation.")
    rate_date: Optional[date] = Field(default=None, description="Resolved FX rate date.")
    rate: Optional[Decimal] = Field(default=None, description="Resolved FX conversion rate.")
    age_days: Optional[int] = Field(default=None, description="Observation age in days.")
    quality_status: Literal["READY", "STALE", "MISSING"] = Field(
        description="Core FX coverage quality status."
    )


class DpmCoreMarketDataCoverageSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for market-data consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_price_count: int = Field(description="Number of requested price observations.")
    resolved_price_count: int = Field(description="Number of resolved price observations.")
    requested_fx_count: int = Field(description="Number of requested FX observations.")
    resolved_fx_count: int = Field(description="Number of resolved FX observations.")
    missing_instrument_ids: list[str] = Field(
        default_factory=list,
        description="Requested instruments without a price observation.",
    )
    stale_instrument_ids: list[str] = Field(
        default_factory=list,
        description="Requested instruments whose price observation is stale.",
    )
    missing_currency_pairs: list[str] = Field(
        default_factory=list,
        description="Requested FX pairs without a rate observation.",
    )
    stale_currency_pairs: list[str] = Field(
        default_factory=list,
        description="Requested FX pairs whose rate observation is stale.",
    )


class DpmCoreMarketDataCoverageWindowResponse(BaseModel):
    product_name: Literal["MarketDataCoverageWindow"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve market data.")
    valuation_currency: Optional[str] = Field(
        default=None,
        description="Requested valuation currency context.",
    )
    price_coverage: list[DpmCoreMarketDataPriceCoverageRecord] = Field(
        default_factory=list,
        description="Resolved price coverage records from lotus-core.",
    )
    fx_coverage: list[DpmCoreMarketDataFxCoverageRecord] = Field(
        default_factory=list,
        description="Resolved FX coverage records from lotus-core.",
    )
    supportability: DpmCoreMarketDataCoverageSupportability = Field(
        description="Completeness and readiness posture for market-data consumption."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreIntegrationWindow(BaseModel):
    start_date: date = Field(description="Inclusive source evidence window start date.")
    end_date: date = Field(description="Inclusive source evidence window end date.")


class DpmCoreTransactionCostCurvePoint(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    security_id: str = Field(description="Security identifier represented by the cost point.")
    transaction_type: str = Field(description="Observed transaction type.")
    currency: str = Field(description="Currency of observed notional and cost values.")
    observation_count: int = Field(description="Number of observed transactions represented.")
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
        description="Bounded deterministic sample of source transaction identifiers.",
    )
    source_lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Point-level source lineage from lotus-core.",
    )


class DpmCoreTransactionCostCurvePageMetadata(BaseModel):
    page_size: int = Field(description="Maximum cost-curve points requested.")
    sort_key: str = Field(description="Deterministic sort key applied by lotus-core.")
    returned_component_count: int = Field(description="Number of curve points returned.")
    request_scope_fingerprint: str = Field(
        description="Core fingerprint of request selectors and paging scope."
    )
    next_page_token: Optional[str] = Field(
        default=None,
        description="Opaque continuation token when more points are available.",
    )


class DpmCoreTransactionCostCurveSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for transaction-cost evidence."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_security_count: Optional[int] = Field(
        default=None,
        description="Number of securities explicitly requested from core.",
    )
    returned_curve_point_count: int = Field(
        description="Number of qualifying observed cost-curve points returned."
    )
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without qualifying cost evidence.",
    )


class DpmCoreTransactionCostCurveResponse(BaseModel):
    product_name: Literal["TransactionCostCurve"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="As-of date used for the curve.")
    window: DpmCoreIntegrationWindow = Field(description="Observed transaction-date window.")
    curve_points: list[DpmCoreTransactionCostCurvePoint] = Field(
        default_factory=list,
        description="Observed transaction-cost curve points from lotus-core.",
    )
    page: DpmCoreTransactionCostCurvePageMetadata = Field(
        description="Core pagination metadata for the cost-curve response."
    )
    supportability: DpmCoreTransactionCostCurveSupportability = Field(
        description="Completeness and readiness posture for cost-curve evidence."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core product-level lineage metadata.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )


class DpmCoreCashflowProjectionPoint(BaseModel):
    projection_date: date = Field(description="Projection date represented by the source row.")
    net_cashflow: Decimal = Field(description="Daily net cashflow in portfolio currency.")
    projected_cumulative_cashflow: Decimal = Field(
        description="Running cumulative cashflow over the returned projection window."
    )


class DpmCorePortfolioCashflowProjectionResponse(BaseModel):
    product_name: Literal["PortfolioCashflowProjection"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="Business-date anchor for the projection.")
    range_start_date: date = Field(description="Inclusive projection-window start date.")
    range_end_date: date = Field(description="Inclusive projection-window end date.")
    include_projected: bool = Field(
        description="Whether projected future external cash movements are included."
    )
    portfolio_currency: str = Field(description="Currency for projected cashflow measures.")
    points: list[DpmCoreCashflowProjectionPoint] = Field(default_factory=list)
    total_net_cashflow: Decimal = Field(
        description="Source-owned total net cashflow over the returned projection window."
    )
    projection_days: int = Field(description="Projection horizon in days.")
    notes: Optional[str] = Field(default=None)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)
    lineage: dict[str, str] = Field(default_factory=dict)


class DpmCoreClientIncomeNeedsScheduleEntry(BaseModel):
    schedule_id: str = Field(description="Source-owned income-needs schedule identifier.")
    need_type: str = Field(description="Bounded income need type.")
    need_status: str = Field(description="Income-needs lifecycle status.")
    amount: Decimal = Field(description="Source-supplied income need amount.")
    currency: str = Field(description="Currency for the income need amount.")
    frequency: str = Field(description="Income-needs cadence.")
    start_date: date = Field(description="Income-needs schedule start date.")
    end_date: Optional[date] = Field(default=None, description="Income-needs schedule end date.")
    priority: int = Field(description="Source-supplied priority.")
    funding_policy: Optional[str] = Field(default=None)
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreClientIncomeNeedsScheduleSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for income-needs schedule consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    schedule_count: int = Field(description="Number of effective schedules returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreClientIncomeNeedsScheduleResponse(BaseModel):
    product_name: Literal["ClientIncomeNeedsSchedule"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the schedules.")
    schedules: list[DpmCoreClientIncomeNeedsScheduleEntry] = Field(default_factory=list)
    supportability: DpmCoreClientIncomeNeedsScheduleSupportability = Field(
        description="Completeness and readiness posture for income-needs evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreLiquidityReserveRequirementEntry(BaseModel):
    reserve_requirement_id: str = Field(description="Source-owned reserve requirement id.")
    reserve_type: str = Field(description="Bounded reserve requirement type.")
    reserve_status: str = Field(description="Reserve requirement lifecycle status.")
    required_amount: Decimal = Field(description="Required reserve amount.")
    currency: str = Field(description="Currency for required_amount.")
    horizon_days: int = Field(description="Reserve horizon in calendar days.")
    priority: int = Field(description="Source-supplied priority.")
    policy_source: str = Field(description="Source policy or bank reference.")
    effective_from: date = Field(description="Requirement effective start date.")
    effective_to: Optional[date] = Field(
        default=None, description="Requirement effective end date."
    )
    requirement_version: int = Field(description="Selected requirement version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreLiquidityReserveRequirementSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for liquidity-reserve requirement consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requirement_count: int = Field(description="Number of effective requirements returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreLiquidityReserveRequirementResponse(BaseModel):
    product_name: Literal["LiquidityReserveRequirement"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve requirements.")
    requirements: list[DpmCoreLiquidityReserveRequirementEntry] = Field(default_factory=list)
    supportability: DpmCoreLiquidityReserveRequirementSupportability = Field(
        description="Completeness and readiness posture for reserve evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCorePlannedWithdrawalScheduleEntry(BaseModel):
    withdrawal_schedule_id: str = Field(description="Source-owned withdrawal schedule id.")
    withdrawal_type: str = Field(description="Bounded planned withdrawal type.")
    withdrawal_status: str = Field(description="Withdrawal lifecycle status.")
    amount: Decimal = Field(description="Source-supplied planned withdrawal amount.")
    currency: str = Field(description="Currency for the amount.")
    scheduled_date: date = Field(description="Scheduled withdrawal date.")
    recurrence_frequency: Optional[str] = Field(default=None)
    purpose_code: Optional[str] = Field(default=None)
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCorePlannedWithdrawalScheduleSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for planned-withdrawal schedule consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    withdrawal_count: int = Field(description="Number of withdrawals returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCorePlannedWithdrawalScheduleResponse(BaseModel):
    product_name: Literal["PlannedWithdrawalSchedule"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the schedules.")
    horizon_days: int = Field(description="Forward withdrawal horizon.")
    withdrawals: list[DpmCorePlannedWithdrawalScheduleEntry] = Field(default_factory=list)
    supportability: DpmCorePlannedWithdrawalScheduleSupportability = Field(
        description="Completeness and readiness posture for planned-withdrawal evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalHedgeExecutionReadinessSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury hedge execution readiness."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before readiness is usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description="Treasury, OMS, execution, and autonomous-action capabilities blocked.",
    )


class DpmCoreExternalHedgeExecutionReadinessResponse(BaseModel):
    product_name: Literal["ExternalHedgeExecutionReadiness"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve readiness posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    readiness_checks: list[dict[str, str]] = Field(
        default_factory=list,
        description="External treasury readiness checks emitted by core.",
    )
    supportability: DpmCoreExternalHedgeExecutionReadinessSupportability = Field(
        description="Fail-closed external treasury supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalCurrencyExposureSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury currency exposure."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    exposure_count: int = Field(
        ge=0,
        description="External currency exposure row count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before exposure is usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description="FX, treasury, OMS, execution, and autonomous-action capabilities blocked.",
    )


class DpmCoreExternalCurrencyExposureResponse(BaseModel):
    product_name: Literal["ExternalCurrencyExposure"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve exposure posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    exposures: list[dict[str, str]] = Field(
        default_factory=list,
        description="External treasury exposure rows, empty while source ingestion is unavailable.",
    )
    supportability: DpmCoreExternalCurrencyExposureSupportability = Field(
        description="Fail-closed external treasury exposure supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreClientRestrictionEntry(BaseModel):
    restriction_scope: str = Field(description="Source-owned restriction scope.")
    restriction_code: str = Field(description="Bounded restriction code.")
    restriction_status: str = Field(description="Restriction lifecycle status.")
    restriction_source: str = Field(description="Source channel that captured the restriction.")
    applies_to_buy: bool = Field(description="Whether the restriction applies to buy actions.")
    applies_to_sell: bool = Field(description="Whether the restriction applies to sell actions.")
    instrument_ids: list[str] = Field(default_factory=list)
    asset_classes: list[str] = Field(default_factory=list)
    issuer_ids: list[str] = Field(default_factory=list)
    country_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Restriction effective start date.")
    effective_to: Optional[date] = Field(
        default=None, description="Restriction effective end date."
    )
    restriction_version: int = Field(description="Selected restriction version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreClientRestrictionSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for restriction-profile consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    restriction_count: int = Field(description="Number of effective restrictions returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreClientRestrictionProfileResponse(BaseModel):
    product_name: Literal["ClientRestrictionProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    restrictions: list[DpmCoreClientRestrictionEntry] = Field(default_factory=list)
    supportability: DpmCoreClientRestrictionSupportability = Field(
        description="Completeness and readiness posture for restriction evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreSustainabilityPreferenceEntry(BaseModel):
    preference_framework: str = Field(description="Source-owned sustainability framework.")
    preference_code: str = Field(description="Bounded sustainability preference code.")
    preference_status: str = Field(description="Preference lifecycle status.")
    preference_source: str = Field(description="Source channel that captured the preference.")
    minimum_allocation: Optional[Decimal] = Field(default=None)
    maximum_allocation: Optional[Decimal] = Field(default=None)
    applies_to_asset_classes: list[str] = Field(default_factory=list)
    exclusion_codes: list[str] = Field(default_factory=list)
    positive_tilt_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Preference effective start date.")
    effective_to: Optional[date] = Field(default=None, description="Preference effective end date.")
    preference_version: int = Field(description="Selected preference version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreSustainabilityPreferenceSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for sustainability-preference consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    preference_count: int = Field(description="Number of effective preferences returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreSustainabilityPreferenceProfileResponse(BaseModel):
    product_name: Literal["SustainabilityPreferenceProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    preferences: list[DpmCoreSustainabilityPreferenceEntry] = Field(default_factory=list)
    supportability: DpmCoreSustainabilityPreferenceSupportability = Field(
        description="Completeness and readiness posture for sustainability evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExecutionContext(BaseModel):
    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Core-governed portfolio holdings and cash snapshot."
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Core-governed prices and FX used for execution."
    )
    model_portfolio: ModelPortfolio = Field(description="Resolved discretionary model targets.")
    shelf_entries: list[ShelfEntry] = Field(
        description="Resolved product shelf and eligibility metadata."
    )
    policy_context: DpmCorePolicyContext = Field(
        default_factory=DpmCorePolicyContext,
        description="Policy selectors resolved by core.",
    )
    source_lineage: DpmCoreSourceLineage = Field(description="Core source-lineage identifiers.")
    supportability: DpmCoreSupportability = Field(
        description="Completeness and freshness posture for the context."
    )
    transaction_cost_curve: Optional[DpmCoreTransactionCostCurveResponse] = Field(
        default=None,
        description=(
            "Optional source-owned observed transaction-cost evidence from "
            "TransactionCostCurve:v1. Absence preserves labelled local cost estimates only."
        ),
    )
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse] = Field(
        default=None,
        description=(
            "Optional source-owned operational cashflow evidence from "
            "PortfolioCashflowProjection:v1. Absence preserves settlement/current-cash-only "
            "liquidity behavior."
        ),
    )
    client_income_needs_schedule: Optional[DpmCoreClientIncomeNeedsScheduleResponse] = Field(
        default=None,
        description=(
            "Optional source-owned client income-needs evidence from "
            "ClientIncomeNeedsSchedule:v1. Manage preserves this as supportability evidence and "
            "does not turn it into financial-planning advice or a funding recommendation."
        ),
    )
    liquidity_reserve_requirement: Optional[DpmCoreLiquidityReserveRequirementResponse] = Field(
        default=None,
        description=(
            "Optional source-owned liquidity reserve evidence from LiquidityReserveRequirement:v1."
        ),
    )
    planned_withdrawal_schedule: Optional[DpmCorePlannedWithdrawalScheduleResponse] = Field(
        default=None,
        description=(
            "Optional source-owned planned-withdrawal evidence from "
            "PlannedWithdrawalSchedule:v1. This is not an OMS instruction or forecast."
        ),
    )
    external_hedge_execution_readiness: Optional[DpmCoreExternalHedgeExecutionReadinessResponse] = (
        Field(
            default=None,
            description=(
                "Optional lotus-core ExternalHedgeExecutionReadiness:v1 posture. Manage preserves "
                "this as fail-closed external treasury readiness evidence and does not turn it into "
                "hedge advice, pricing, counterparty, execution, OMS, fill, or settlement truth."
            ),
        )
    )
    external_currency_exposure: Optional[DpmCoreExternalCurrencyExposureResponse] = Field(
        default=None,
        description=(
            "Optional lotus-core ExternalCurrencyExposure:v1 posture. Manage preserves this as "
            "fail-closed external treasury exposure evidence and does not turn it into FX "
            "attribution, hedge advice, treasury instruction, execution readiness, OMS, fill, or "
            "settlement truth."
        ),
    )
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse] = Field(
        default=None,
        description=(
            "Optional source-owned client restriction evidence from "
            "ClientRestrictionProfile:v1. Absence keeps ESG/restriction-aware construction "
            "truthfully degraded."
        ),
    )
    sustainability_preference_profile: Optional[DpmCoreSustainabilityPreferenceProfileResponse] = (
        Field(
            default=None,
            description=(
                "Optional source-owned sustainability preference evidence from "
                "SustainabilityPreferenceProfile:v1."
            ),
        )
    )


class DpmStatefulInput(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of: date = Field(description="Business date for stateful source-data resolution.")
    mandate_id: Optional[str] = Field(default=None, description="Discretionary mandate selector.")
    model_portfolio_id: Optional[str] = Field(
        default=None,
        description="Model portfolio selector for discretionary execution.",
    )
    policy_pack_id: Optional[str] = Field(
        default=None, description="Optional policy-pack selector."
    )
    tenant_id: Optional[str] = Field(default=None, description="Tenant selector.")
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Booking-center selector.",
    )
    include_tax_lots: bool = Field(
        default=True,
        description="Ask core to include tax lots when available.",
    )
    include_settlement_profile: bool = Field(
        default=True,
        description="Ask core to include settlement metadata when available.",
    )
    include_shelf: bool = Field(default=True, description="Ask core to include shelf metadata.")
    include_model_portfolio: bool = Field(
        default=True,
        description="Ask core to include model portfolio targets.",
    )


class DpmResolvedSourceContext(BaseModel):
    input_mode: Literal["stateful"] = "stateful"
    source_system: str = Field(default="lotus-core")
    stateful_context_hash: str
    context: DpmCoreExecutionContext


class DpmResolvedRebalanceInput(BaseModel):
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: list[ShelfEntry]
    options: EngineOptions


class DpmCoreContextIncompleteError(ValueError):
    pass


def build_core_resolver_payload(stateful_input: DpmStatefulInput) -> dict[str, Any]:
    return {
        "as_of": stateful_input.as_of.isoformat(),
        "mandate_id": stateful_input.mandate_id,
        "model_portfolio_id": stateful_input.model_portfolio_id,
        "tenant_id": stateful_input.tenant_id,
        "booking_center_code": stateful_input.booking_center_code,
        "include_tax_lots": stateful_input.include_tax_lots,
        "include_settlement_profile": stateful_input.include_settlement_profile,
        "include_shelf": stateful_input.include_shelf,
        "include_model_portfolio": stateful_input.include_model_portfolio,
    }


def _options_from_override(
    options_override: dict[str, Any],
    *,
    default_valuation_mode: ValuationMode | None = None,
) -> EngineOptions:
    payload = dict(options_override)
    if default_valuation_mode is not None and "valuation_mode" not in payload:
        payload["valuation_mode"] = default_valuation_mode
    return EngineOptions.model_validate(payload)


def build_model_portfolio_from_core_targets(
    response: DpmCoreModelPortfolioTargetResponse,
) -> ModelPortfolio:
    if response.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(response.supportability.reason)
    if not response.targets:
        raise DpmCoreContextIncompleteError("DPM_CORE_MODEL_TARGETS_EMPTY")
    return ModelPortfolio(
        targets=[
            ModelTarget(instrument_id=target.instrument_id, weight=target.target_weight)
            for target in response.targets
            if target.target_status.lower() == "active"
        ]
    )


def build_policy_context_from_core_mandate(
    response: DpmCoreMandateBindingResponse,
    *,
    tenant_id: Optional[str] = None,
) -> DpmCorePolicyContext:
    if response.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(response.supportability.reason)
    if response.mandate_type.lower() != "discretionary":
        raise DpmCoreContextIncompleteError("DPM_CORE_MANDATE_NOT_DISCRETIONARY")
    if response.discretionary_authority_status.lower() != "active":
        raise DpmCoreContextIncompleteError("DPM_CORE_DISCRETIONARY_AUTHORITY_NOT_ACTIVE")
    return DpmCorePolicyContext(
        recommended_policy_pack_id=response.policy_pack_id,
        tenant_id=tenant_id,
        booking_center_code=response.booking_center_code,
        mandate_id=response.mandate_id,
    )


def _shelf_attribute_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def build_shelf_entries_from_core_eligibility(
    response: DpmCoreInstrumentEligibilityBulkResponse,
) -> list[ShelfEntry]:
    if response.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(response.supportability.reason)

    eligible_records = [record for record in response.eligibility if record.found]
    if not eligible_records:
        raise DpmCoreContextIncompleteError("DPM_CORE_INSTRUMENT_ELIGIBILITY_EMPTY")

    shelf_entries: list[ShelfEntry] = []
    for record in eligible_records:
        shelf_entries.append(
            ShelfEntry(
                instrument_id=record.security_id,
                status=record.product_shelf_status,
                asset_class=record.asset_class or "UNKNOWN",
                issuer_id=record.issuer_id,
                liquidity_tier=record.liquidity_tier,
                settlement_days=record.settlement_days if record.settlement_days is not None else 2,
                attributes={
                    "buy_allowed": _shelf_attribute_value(record.buy_allowed),
                    "sell_allowed": _shelf_attribute_value(record.sell_allowed),
                    "eligibility_status": record.eligibility_status,
                    "country_of_risk": _shelf_attribute_value(record.country_of_risk),
                    "settlement_calendar_id": _shelf_attribute_value(record.settlement_calendar_id),
                    "ultimate_parent_issuer_id": _shelf_attribute_value(
                        record.ultimate_parent_issuer_id
                    ),
                    "restriction_reason_codes": ",".join(record.restriction_reason_codes),
                    "source_record_id": _shelf_attribute_value(record.source_record_id),
                },
            )
        )
    return shelf_entries


def build_portfolio_snapshot_with_core_tax_lots(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    response: DpmCorePortfolioTaxLotWindowResponse,
) -> PortfolioSnapshot:
    if response.supportability.state != "READY":
        raise DpmCoreContextIncompleteError(response.supportability.reason)
    if response.portfolio_id != portfolio_snapshot.portfolio_id:
        raise DpmCoreContextIncompleteError("DPM_CORE_TAX_LOT_PORTFOLIO_MISMATCH")

    lots_by_instrument: dict[str, list[TaxLot]] = {}
    for lot in response.lots:
        if lot.tax_lot_status != "OPEN" or lot.open_quantity <= Decimal("0"):
            continue
        unit_cost_amount = lot.cost_basis_base / lot.open_quantity
        unit_cost_currency = portfolio_snapshot.base_currency
        if lot.local_currency:
            unit_cost_amount = lot.cost_basis_local / lot.open_quantity
            unit_cost_currency = lot.local_currency
        lots_by_instrument.setdefault(lot.instrument_id, []).append(
            TaxLot(
                lot_id=lot.lot_id,
                quantity=lot.open_quantity,
                unit_cost=Money(amount=unit_cost_amount, currency=unit_cost_currency),
                purchase_date=lot.acquisition_date.isoformat(),
            )
        )

    positions = []
    for position in portfolio_snapshot.positions:
        position_payload = position.model_dump(mode="python")
        position_payload["lots"] = lots_by_instrument.get(position.instrument_id, [])
        positions.append(type(position).model_validate(position_payload))
    return PortfolioSnapshot.model_validate(
        {**portfolio_snapshot.model_dump(mode="python"), "positions": positions}
    )


def build_market_data_snapshot_from_core_coverage(
    response: DpmCoreMarketDataCoverageWindowResponse,
) -> MarketDataSnapshot:
    if response.supportability.state != "READY":
        raise DpmCoreContextIncompleteError(response.supportability.reason)

    prices: list[Price] = []
    for record in response.price_coverage:
        if (
            not record.found
            or record.quality_status != "READY"
            or record.price is None
            or record.currency is None
        ):
            raise DpmCoreContextIncompleteError("DPM_CORE_MARKET_DATA_PRICE_INCOMPLETE")
        prices.append(
            Price(
                instrument_id=record.instrument_id,
                price=record.price,
                currency=record.currency,
            )
        )

    fx_rates: list[FxRate] = []
    for fx_record in response.fx_coverage:
        if not fx_record.found or fx_record.quality_status != "READY" or fx_record.rate is None:
            raise DpmCoreContextIncompleteError("DPM_CORE_MARKET_DATA_FX_INCOMPLETE")
        fx_rates.append(
            FxRate(
                pair=f"{fx_record.from_currency.upper()}/{fx_record.to_currency.upper()}",
                rate=fx_record.rate,
            )
        )

    return MarketDataSnapshot(
        snapshot_id=f"core-market-data-coverage:{response.as_of_date.isoformat()}",
        prices=prices,
        fx_rates=fx_rates,
    )


def build_rebalance_request_from_core_context(
    *,
    context: DpmCoreExecutionContext,
    options_override: dict[str, Any],
) -> DpmResolvedRebalanceInput:
    if context.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(context.supportability.reason)
    if context.supportability.missing_source_families:
        raise DpmCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE")

    return DpmResolvedRebalanceInput(
        portfolio_snapshot=context.portfolio_snapshot,
        market_data_snapshot=context.market_data_snapshot,
        model_portfolio=context.model_portfolio,
        shelf_entries=context.shelf_entries,
        options=_options_from_override(
            options_override,
            default_valuation_mode=ValuationMode.TRUST_SNAPSHOT,
        ),
    )


def build_batch_rebalance_request_from_core_context(
    *,
    context: DpmCoreExecutionContext,
    scenarios: dict[str, SimulationScenario],
) -> BatchRebalanceRequest:
    if context.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(context.supportability.reason)
    if context.supportability.missing_source_families:
        raise DpmCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE")

    return BatchRebalanceRequest(
        portfolio_snapshot=context.portfolio_snapshot,
        market_data_snapshot=context.market_data_snapshot,
        model_portfolio=context.model_portfolio,
        shelf_entries=context.shelf_entries,
        scenarios={
            name: SimulationScenario(
                description=scenario.description,
                options={
                    "valuation_mode": ValuationMode.TRUST_SNAPSHOT,
                    **scenario.options,
                },
            )
            for name, scenario in scenarios.items()
        },
    )
