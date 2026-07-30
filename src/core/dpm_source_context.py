from datetime import date
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.core.dpm_source_context_core_products import (
    DpmCoreBenchmarkAssignmentResponse as DpmCoreBenchmarkAssignmentResponse,
    DpmCoreCioModelChangeAffectedCohortResponse as DpmCoreCioModelChangeAffectedCohortResponse,
    DpmCoreCioModelChangeAffectedMandate as DpmCoreCioModelChangeAffectedMandate,
    DpmCoreCioModelChangeSupportability as DpmCoreCioModelChangeSupportability,
    DpmCoreMandateBindingResponse as DpmCoreMandateBindingResponse,
    DpmCoreMandateBindingSupportability as DpmCoreMandateBindingSupportability,
    DpmCoreModelPortfolioTargetResponse as DpmCoreModelPortfolioTargetResponse,
    DpmCoreModelPortfolioTargetRow as DpmCoreModelPortfolioTargetRow,
    DpmCoreModelPortfolioTargetSupportability as DpmCoreModelPortfolioTargetSupportability,
    DpmCorePortfolioManagerBookMember as DpmCorePortfolioManagerBookMember,
    DpmCorePortfolioManagerBookMembershipResponse as DpmCorePortfolioManagerBookMembershipResponse,
    DpmCorePortfolioManagerBookSupportability as DpmCorePortfolioManagerBookSupportability,
    DpmCorePortfolioUniverseCandidate as DpmCorePortfolioUniverseCandidate,
    DpmCorePortfolioUniverseCandidateResponse as DpmCorePortfolioUniverseCandidateResponse,
    DpmCorePortfolioUniverseCandidateSelectionBasis as DpmCorePortfolioUniverseCandidateSelectionBasis,
    DpmCorePortfolioUniverseCandidateSupportability as DpmCorePortfolioUniverseCandidateSupportability,
    DpmCorePortfolioUniversePageMetadata as DpmCorePortfolioUniversePageMetadata,
    DpmCoreRebalanceBands as DpmCoreRebalanceBands,
)
from src.core.dpm_source_context_execution_controls import (
    DpmCoreClientRestrictionEntry as DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse as DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientRestrictionSupportability as DpmCoreClientRestrictionSupportability,
    DpmCoreInstrumentEligibilityBulkResponse as DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreInstrumentEligibilityRecord as DpmCoreInstrumentEligibilityRecord,
    DpmCoreInstrumentEligibilitySupportability as DpmCoreInstrumentEligibilitySupportability,
    DpmCoreIntegrationWindow as DpmCoreIntegrationWindow,
    DpmCoreSustainabilityPreferenceEntry as DpmCoreSustainabilityPreferenceEntry,
    DpmCoreSustainabilityPreferenceProfileResponse as DpmCoreSustainabilityPreferenceProfileResponse,
    DpmCoreSustainabilityPreferenceSupportability as DpmCoreSustainabilityPreferenceSupportability,
    DpmCoreTransactionCostCurvePageMetadata as DpmCoreTransactionCostCurvePageMetadata,
    DpmCoreTransactionCostCurvePoint as DpmCoreTransactionCostCurvePoint,
    DpmCoreTransactionCostCurveResponse as DpmCoreTransactionCostCurveResponse,
    DpmCoreTransactionCostCurveSupportability as DpmCoreTransactionCostCurveSupportability,
)
from src.core.dpm_source_context_external_treasury import (
    DpmCoreExternalCurrencyExposureResponse as DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalCurrencyExposureSupportability as DpmCoreExternalCurrencyExposureSupportability,
    DpmCoreExternalEligibleHedgeInstrumentResponse as DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalEligibleHedgeInstrumentSupportability as DpmCoreExternalEligibleHedgeInstrumentSupportability,
    DpmCoreExternalFXForwardCurveResponse as DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalFXForwardCurveSupportability as DpmCoreExternalFXForwardCurveSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse as DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability as DpmCoreExternalHedgeExecutionReadinessSupportability,
    DpmCoreExternalHedgePolicyResponse as DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalHedgePolicySupportability as DpmCoreExternalHedgePolicySupportability,
    DpmCoreExternalOrderExecutionAcknowledgementResponse as DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExternalOrderExecutionAcknowledgementSupportability as DpmCoreExternalOrderExecutionAcknowledgementSupportability,
)
from src.core.dpm_source_context_financial_planning import (
    DpmCoreCashflowProjectionPoint as DpmCoreCashflowProjectionPoint,
    DpmCoreClientIncomeNeedsScheduleEntry as DpmCoreClientIncomeNeedsScheduleEntry,
    DpmCoreClientIncomeNeedsScheduleResponse as DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientIncomeNeedsScheduleSupportability as DpmCoreClientIncomeNeedsScheduleSupportability,
    DpmCoreLiquidityReserveRequirementEntry as DpmCoreLiquidityReserveRequirementEntry,
    DpmCoreLiquidityReserveRequirementResponse as DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreLiquidityReserveRequirementSupportability as DpmCoreLiquidityReserveRequirementSupportability,
    DpmCorePlannedWithdrawalScheduleEntry as DpmCorePlannedWithdrawalScheduleEntry,
    DpmCorePlannedWithdrawalScheduleResponse as DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePlannedWithdrawalScheduleSupportability as DpmCorePlannedWithdrawalScheduleSupportability,
    DpmCorePortfolioCashflowProjectionResponse as DpmCorePortfolioCashflowProjectionResponse,
)
from src.core.dpm_source_context_market_data import (
    DpmCoreMarketDataCoverageSupportability as DpmCoreMarketDataCoverageSupportability,
    DpmCoreMarketDataCoverageWindowResponse as DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreMarketDataFxCoverageRecord as DpmCoreMarketDataFxCoverageRecord,
    DpmCoreMarketDataPriceCoverageRecord as DpmCoreMarketDataPriceCoverageRecord,
    DpmCorePortfolioTaxLotRecord as DpmCorePortfolioTaxLotRecord,
    DpmCorePortfolioTaxLotSupportability as DpmCorePortfolioTaxLotSupportability,
    DpmCorePortfolioTaxLotWindowResponse as DpmCorePortfolioTaxLotWindowResponse,
    DpmCoreTaxLotPageMetadata as DpmCoreTaxLotPageMetadata,
)
from src.core.models import (
    BatchRebalanceRequest,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    Money,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
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


class DpmCoreSourceReadinessFamily(BaseModel):
    family: str = Field(description="Core source family represented by this readiness row.")
    product_name: str = Field(description="Core source-data product used for this family.")
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Source-family readiness state."
    )
    reason: str = Field(description="Source-owned bounded reason code.")
    missing_items: list[str] = Field(
        default_factory=list,
        description="Bounded missing source identifiers or source-family names.",
    )
    stale_items: list[str] = Field(
        default_factory=list,
        description="Bounded stale source identifiers or FX pairs.",
    )
    evidence_count: int = Field(
        default=0,
        ge=0,
        description="Source-family evidence count reported by lotus-core.",
    )


class DpmCoreSourceReadinessSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Overall Core DPM source-readiness state."
    )
    reason: str = Field(description="Core source-readiness reason code.")
    ready_family_count: int = Field(ge=0)
    degraded_family_count: int = Field(ge=0)
    incomplete_family_count: int = Field(ge=0)
    unavailable_family_count: int = Field(ge=0)


class DpmCoreSourceReadinessResponse(BaseModel):
    product_name: Literal["DpmSourceReadiness"] = Field(description="Core source product name.")
    product_version: Literal["v1"] = Field(description="Core source product version.")
    portfolio_id: str = Field(description="Portfolio whose DPM source readiness was evaluated.")
    as_of_date: date = Field(description="Readiness as-of date.")
    mandate_id: str | None = Field(default=None, description="Resolved mandate identifier.")
    model_portfolio_id: str | None = Field(
        default=None,
        description="Resolved model portfolio identifier.",
    )
    evaluated_instrument_ids: list[str] = Field(
        default_factory=list,
        description="Instrument universe evaluated by Core source readiness.",
    )
    families: list[DpmCoreSourceReadinessFamily] = Field(
        description="Source-family readiness rows from Core."
    )
    supportability: DpmCoreSourceReadinessSupportability = Field(
        description="Overall source-readiness posture from Core."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core readiness lineage metadata.",
    )
    data_quality_status: str | None = Field(default=None)
    latest_evidence_timestamp: str | None = Field(default=None)
    source_batch_fingerprint: str | None = Field(default=None)
    snapshot_id: str | None = Field(default=None)
    correlation_id: str | None = Field(default=None)


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
    source_readiness: Optional[DpmCoreSourceReadinessResponse] = Field(
        default=None,
        description=(
            "Core-owned DpmSourceReadiness:v1 envelope used to gate stateful source promotion "
            "and preserve source-family diagnostics."
        ),
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
    external_hedge_policy: Optional[DpmCoreExternalHedgePolicyResponse] = Field(
        default=None,
        description=(
            "Optional lotus-core ExternalHedgePolicy:v1 posture. Manage preserves this as "
            "fail-closed external treasury policy evidence and does not turn it into hedge-policy "
            "approval, hedge advice, treasury instruction, counterparty selection, OMS, fill, or "
            "settlement truth."
        ),
    )
    external_eligible_hedge_instruments: Optional[
        DpmCoreExternalEligibleHedgeInstrumentResponse
    ] = Field(
        default=None,
        description=(
            "Optional lotus-core ExternalEligibleHedgeInstrument:v1 posture. Manage preserves "
            "this as fail-closed external treasury eligible-instrument evidence and does not "
            "turn it into eligible-instrument selection, suitability approval, product "
            "recommendation, treasury instruction, best execution, OMS, fill, or settlement "
            "truth."
        ),
    )
    external_fx_forward_curve: Optional[DpmCoreExternalFXForwardCurveResponse] = Field(
        default=None,
        description=(
            "Optional lotus-core ExternalFXForwardCurve:v1 posture. Manage preserves this as "
            "fail-closed external treasury forward-curve evidence and does not turn it into "
            "forward pricing, FX valuation methodology, hedge advice, treasury instruction, "
            "counterparty selection, best execution, OMS, fill, or settlement truth."
        ),
    )
    external_order_execution_acknowledgement: Optional[
        DpmCoreExternalOrderExecutionAcknowledgementResponse
    ] = Field(
        default=None,
        description=(
            "Optional lotus-core ExternalOrderExecutionAcknowledgement:v1 posture. Manage "
            "preserves this as fail-closed external OMS acknowledgement evidence and does not "
            "turn it into order generation, venue routing, best execution, OMS acknowledgement, "
            "fill, settlement, execution-status certification, or autonomous execution truth."
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


def _eligible_core_eligibility_records(
    response: DpmCoreInstrumentEligibilityBulkResponse,
) -> list[DpmCoreInstrumentEligibilityRecord]:
    return [record for record in response.eligibility if record.found]


def _shelf_entry_attributes_from_core_eligibility(
    record: DpmCoreInstrumentEligibilityRecord,
) -> dict[str, str]:
    return {
        "buy_allowed": _shelf_attribute_value(record.buy_allowed),
        "sell_allowed": _shelf_attribute_value(record.sell_allowed),
        "eligibility_status": record.eligibility_status,
        "country_of_risk": _shelf_attribute_value(record.country_of_risk),
        "settlement_calendar_id": _shelf_attribute_value(record.settlement_calendar_id),
        "ultimate_parent_issuer_id": _shelf_attribute_value(record.ultimate_parent_issuer_id),
        "restriction_reason_codes": ",".join(record.restriction_reason_codes),
        "source_record_id": _shelf_attribute_value(record.source_record_id),
    }


def _shelf_entry_from_core_eligibility(
    record: DpmCoreInstrumentEligibilityRecord,
) -> ShelfEntry:
    return ShelfEntry(
        instrument_id=record.security_id,
        status=record.product_shelf_status,
        asset_class=record.asset_class or "UNKNOWN",
        issuer_id=record.issuer_id,
        liquidity_tier=record.liquidity_tier,
        settlement_days=record.settlement_days if record.settlement_days is not None else 2,
        attributes=_shelf_entry_attributes_from_core_eligibility(record),
    )


def build_shelf_entries_from_core_eligibility(
    response: DpmCoreInstrumentEligibilityBulkResponse,
) -> list[ShelfEntry]:
    if response.supportability.state not in {"READY", "DEGRADED"}:
        raise DpmCoreContextIncompleteError(response.supportability.reason)

    eligible_records = _eligible_core_eligibility_records(response)
    if not eligible_records:
        raise DpmCoreContextIncompleteError("DPM_CORE_INSTRUMENT_ELIGIBILITY_EMPTY")

    return [_shelf_entry_from_core_eligibility(record) for record in eligible_records]


def build_portfolio_snapshot_with_core_tax_lots(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    response: DpmCorePortfolioTaxLotWindowResponse,
) -> PortfolioSnapshot:
    if response.supportability.state != "READY":
        raise DpmCoreContextIncompleteError(response.supportability.reason)
    if response.portfolio_id != portfolio_snapshot.portfolio_id:
        raise DpmCoreContextIncompleteError("DPM_CORE_TAX_LOT_PORTFOLIO_MISMATCH")

    lots_by_instrument = _open_core_tax_lots_by_instrument(
        response=response,
        base_currency=portfolio_snapshot.base_currency,
    )
    _validate_core_tax_lot_coverage(
        portfolio_snapshot=portfolio_snapshot,
        lots_by_instrument=lots_by_instrument,
    )
    positions = [
        _portfolio_position_with_tax_lots(
            position=position,
            lots_by_instrument=lots_by_instrument,
        )
        for position in portfolio_snapshot.positions
    ]
    return PortfolioSnapshot.model_validate(
        {**portfolio_snapshot.model_dump(mode="python"), "positions": positions}
    )


def _validate_core_tax_lot_coverage(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    lots_by_instrument: dict[str, list[TaxLot]],
) -> None:
    for position in portfolio_snapshot.positions:
        if position.quantity <= Decimal("0"):
            continue
        lots = lots_by_instrument.get(position.instrument_id, [])
        if not lots:
            raise DpmCoreContextIncompleteError("DPM_CORE_TAX_LOTS_INCOMPLETE")
        lot_quantity = sum((lot.quantity for lot in lots), Decimal("0"))
        if abs(lot_quantity - position.quantity) > Decimal("0.0001"):
            raise DpmCoreContextIncompleteError("DPM_CORE_TAX_LOT_QUANTITY_MISMATCH")


def _open_core_tax_lots_by_instrument(
    *,
    response: DpmCorePortfolioTaxLotWindowResponse,
    base_currency: str,
) -> dict[str, list[TaxLot]]:
    lots_by_instrument: dict[str, list[TaxLot]] = {}
    for lot in response.lots:
        if lot.tax_lot_status != "OPEN" or lot.open_quantity <= Decimal("0"):
            continue
        # PortfolioSnapshot positions are keyed by Core's security_id. The separate
        # instrument_id is reference/vendor identity and must not be used for lot attachment.
        lots_by_instrument.setdefault(lot.security_id, []).append(
            _core_tax_lot_to_engine_lot(lot=lot, base_currency=base_currency)
        )
    return lots_by_instrument


def _core_tax_lot_to_engine_lot(
    *,
    lot: DpmCorePortfolioTaxLotRecord,
    base_currency: str,
) -> TaxLot:
    unit_cost_amount = lot.cost_basis_base / lot.open_quantity
    unit_cost_currency = base_currency
    if lot.local_currency:
        unit_cost_amount = lot.cost_basis_local / lot.open_quantity
        unit_cost_currency = lot.local_currency
    return TaxLot(
        lot_id=lot.lot_id,
        quantity=lot.open_quantity,
        unit_cost=Money(amount=unit_cost_amount, currency=unit_cost_currency),
        purchase_date=lot.acquisition_date.isoformat(),
    )


def _portfolio_position_with_tax_lots(
    *,
    position: Position,
    lots_by_instrument: dict[str, list[TaxLot]],
) -> Position:
    position_payload = position.model_dump(mode="python")
    position_payload["lots"] = lots_by_instrument.get(position.instrument_id, [])
    return type(position).model_validate(position_payload)


def build_market_data_snapshot_from_core_coverage(
    response: DpmCoreMarketDataCoverageWindowResponse,
) -> MarketDataSnapshot:
    if response.supportability.state != "READY":
        raise DpmCoreContextIncompleteError(response.supportability.reason)

    return MarketDataSnapshot(
        snapshot_id=f"core-market-data-coverage:{response.as_of_date.isoformat()}",
        prices=_core_coverage_prices(response.price_coverage),
        fx_rates=_core_coverage_fx_rates(response.fx_coverage),
    )


def _core_coverage_prices(
    records: list[DpmCoreMarketDataPriceCoverageRecord],
) -> list[Price]:
    return [_core_coverage_price(record) for record in records]


def _core_coverage_price(record: DpmCoreMarketDataPriceCoverageRecord) -> Price:
    if (
        not record.found
        or record.quality_status != "READY"
        or record.price is None
        or record.currency is None
    ):
        raise DpmCoreContextIncompleteError("DPM_CORE_MARKET_DATA_PRICE_INCOMPLETE")
    return Price(
        instrument_id=record.instrument_id,
        price=record.price,
        currency=record.currency,
    )


def _core_coverage_fx_rates(
    records: list[DpmCoreMarketDataFxCoverageRecord],
) -> list[FxRate]:
    return [_core_coverage_fx_rate(record) for record in records]


def _core_coverage_fx_rate(record: DpmCoreMarketDataFxCoverageRecord) -> FxRate:
    if not record.found or record.quality_status != "READY" or record.rate is None:
        raise DpmCoreContextIncompleteError("DPM_CORE_MARKET_DATA_FX_INCOMPLETE")
    return FxRate(
        pair=f"{record.from_currency.upper()}/{record.to_currency.upper()}",
        rate=record.rate,
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
