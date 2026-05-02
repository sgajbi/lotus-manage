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
