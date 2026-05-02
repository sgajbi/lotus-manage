from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.core.models import (
    BatchRebalanceRequest,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    ShelfEntry,
    SimulationScenario,
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
    risk_profile: str = Field(description="Mandate risk profile.")
    investment_horizon: str = Field(description="Mandate investment horizon.")
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
    found_count: int = Field(description="Number of securities resolved from core source data.")
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
        description="Resolved eligibility records in request order."
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


def _options_from_override(options_override: dict[str, Any]) -> EngineOptions:
    return EngineOptions.model_validate(options_override)


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
        options=_options_from_override(options_override),
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
        scenarios=scenarios,
    )
