"""
FILE: src/core/models.py
"""

import re
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


class ValuationMode(str, Enum):
    CALCULATED = "CALCULATED"
    TRUST_SNAPSHOT = "TRUST_SNAPSHOT"


class TargetMethod(str, Enum):
    HEURISTIC = "HEURISTIC"
    SOLVER = "SOLVER"


def _quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


_GROUP_CONSTRAINT_KEY_FORMAT = "<attribute_key>:<attribute_value>"
_SCENARIO_NAME_REGEX = re.compile(r"^[a-z0-9_-]{1,64}$")


def _validate_group_constraint_keys(
    group_constraints: Dict[str, "GroupConstraint"],
) -> Dict[str, "GroupConstraint"]:
    for key in group_constraints:
        if key.count(":") != 1:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
        attribute_key, attribute_value = key.split(":", 1)
        if not attribute_key or not attribute_value:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
    return group_constraints


def _validate_optional_ratio_between_zero_and_one(
    value: Optional[Decimal], *, field_name: str
) -> Optional[Decimal]:
    if value is None:
        return value
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def _validate_non_negative_amounts_by_currency(
    amounts_by_currency: Dict[str, Decimal], *, field_name: str
) -> Dict[str, Decimal]:
    for currency, amount in amounts_by_currency.items():
        if not currency:
            raise ValueError(f"{field_name} keys must be non-empty currency codes")
        if amount < Decimal("0"):
            raise ValueError(f"{field_name} values must be non-negative")
    return amounts_by_currency


class Money(BaseModel):
    amount: Decimal = Field(
        description="Monetary amount as decimal string/number.",
        examples=["1000.50"],
    )
    currency: str = Field(
        description="ISO currency code (for example USD, SGD).",
        examples=["USD"],
    )


class FxRate(BaseModel):
    pair: str = Field(
        description="Currency pair in BASE/QUOTE style used by engine lookup.",
        examples=["USD/SGD"],
    )
    rate: Decimal = Field(description="FX conversion rate for the pair.", examples=["1.35"])


class Position(BaseModel):
    instrument_id: str = Field(description="Unique instrument identifier.", examples=["AAPL"])
    quantity: Decimal = Field(description="Held quantity before simulation.", examples=["100"])
    market_value: Optional[Money] = Field(
        default=None,
        description="Optional trusted market value used when valuation_mode=TRUST_SNAPSHOT.",
    )
    lots: List["TaxLot"] = Field(
        default_factory=list,
        description="Optional tax-lot breakdown for tax-aware sell allocation.",
    )

    @model_validator(mode="after")
    def validate_lot_quantity_total(self) -> "Position":
        if not self.lots:
            return self
        total = sum((lot.quantity for lot in self.lots), Decimal("0"))
        if abs(total - self.quantity) > Decimal("0.0001"):
            raise ValueError(
                "sum(lot.quantity) must equal position.quantity within tolerance 0.0001"
            )
        return self


class CashBalance(BaseModel):
    currency: str = Field(description="Cash currency code.", examples=["USD"])
    amount: Decimal = Field(
        description="Available cash amount used by current simulation stages.",
        examples=["25000"],
    )
    settled: Optional[Decimal] = Field(
        default=None,
        description="Optional settled cash amount used by settlement-aware ladder.",
    )
    pending: Optional[Decimal] = Field(
        default=None,
        description="Optional pending cash amount for informational reporting.",
    )


class PortfolioSnapshot(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_id": "pf_1",
                "base_currency": "USD",
                "positions": [{"instrument_id": "AAPL", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "5000"}],
            }
        }
    }

    snapshot_id: Optional[str] = Field(
        default=None,
        description="Optional immutable snapshot identifier for lineage.",
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    base_currency: str = Field(
        description="Base reporting currency for valuation and rules.",
        examples=["USD"],
    )
    positions: List[Position] = Field(default_factory=list, description="Current held positions.")
    cash_balances: List[CashBalance] = Field(
        default_factory=list,
        description="Current portfolio cash balances by currency.",
    )


class Price(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier for the price row.", examples=["AAPL"]
    )
    price: Decimal = Field(
        description="Last/mark price used in valuation and sizing.", examples=["180.25"]
    )
    currency: str = Field(description="Currency of the price.", examples=["USD"])


class MarketDataSnapshot(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "prices": [{"instrument_id": "AAPL", "price": "180.25", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            }
        }
    }

    snapshot_id: Optional[str] = Field(
        default=None,
        description="Optional immutable market-data snapshot identifier for lineage.",
    )
    prices: List[Price] = Field(default_factory=list, description="Instrument prices.")
    fx_rates: List[FxRate] = Field(
        default_factory=list, description="FX rates for currency conversion."
    )


class ModelTarget(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier in model target.", examples=["AAPL"]
    )
    weight: Decimal = Field(
        description="Target portfolio weight for the instrument.", examples=["0.25"]
    )


class ModelPortfolio(BaseModel):
    targets: List[ModelTarget] = Field(description="List of model target weights.")


class TaxLot(BaseModel):
    lot_id: str = Field(
        description="Unique lot identifier within instrument.", examples=["LOT_001"]
    )
    quantity: Decimal = Field(ge=0, description="Lot quantity.", examples=["50"])
    unit_cost: Money = Field(description="Per-unit cost basis for the lot.")
    purchase_date: str = Field(description="Lot purchase date (ISO date string).")


class ShelfEntry(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier in product shelf.", examples=["AAPL"]
    )
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    asset_class: str = Field(
        default="UNKNOWN", description="Asset-class label for aggregation/reporting."
    )
    issuer_id: Optional[str] = Field(
        default=None,
        description="Issuer identifier used for concentration analytics and suitability checks.",
        examples=["ISSUER_TECH_1"],
    )
    liquidity_tier: Optional[Literal["L1", "L2", "L3", "L4", "L5"]] = Field(
        default=None,
        description="Liquidity tier label used for suitability liquidity exposure checks.",
        examples=["L1", "L4"],
    )
    settlement_days: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Settlement lag in business-day offsets used by settlement ladder.",
    )
    min_notional: Optional[Money] = Field(
        default=None,
        description="Optional per-instrument minimum trade notional.",
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Attribute tags used for group constraints (for example sector, region).",
    )


class GroupConstraint(BaseModel):
    max_weight: Decimal = Field(
        description="Maximum allowed aggregate weight for the tagged group."
    )

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v: Decimal) -> Decimal:
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("max_weight must be between 0 and 1 inclusive")
        return v


class EngineOptions(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "target_method": "HEURISTIC",
                "max_turnover_pct": "0.15",
                "enable_tax_awareness": True,
                "max_realized_capital_gains": "100",
                "enable_settlement_awareness": False,
            }
        }
    }

    valuation_mode: ValuationMode = Field(
        default=ValuationMode.CALCULATED,
        description="Valuation source policy.",
        examples=["CALCULATED"],
    )
    target_method: TargetMethod = Field(
        default=TargetMethod.HEURISTIC,
        description="Stage-3 target generation method.",
        examples=["HEURISTIC"],
    )
    compare_target_methods: bool = Field(
        default=False,
        description="Run both target methods and include divergence diagnostics.",
        examples=[False],
    )
    compare_target_methods_tolerance: Decimal = Field(
        default=Decimal("0.0001"),
        description="Tolerance used when comparing method outputs.",
        examples=["0.0001"],
    )

    cash_band_min_weight: Decimal = Field(
        default=Decimal("0.00"),
        description="Lower soft bound for cash weight.",
        examples=["0.00"],
    )
    cash_band_max_weight: Decimal = Field(
        default=Decimal("1.00"),
        description="Upper soft bound for cash weight.",
        examples=["1.00"],
    )

    single_position_max_weight: Optional[Decimal] = Field(
        default=None,
        description="Hard maximum weight allowed for a single position.",
        examples=["0.30"],
    )
    min_trade_notional: Optional[Money] = Field(
        default=None,
        description="Request-level minimum trade notional threshold.",
    )

    allow_restricted: bool = Field(
        default=False,
        description="Allow buys in RESTRICTED shelf instruments.",
        examples=[False],
    )
    suppress_dust_trades: bool = Field(
        default=True,
        description="Suppress trades under minimum notional threshold.",
        examples=[True],
    )
    dust_trade_threshold: Optional[Money] = Field(
        default=None,
        description="Reserved field; currently not consumed by engine logic.",
    )
    fx_buffer_pct: Decimal = Field(
        default=Decimal("0.01"),
        description="Buffer applied when generating FX funding intents.",
        examples=["0.01"],
    )
    block_on_missing_prices: bool = Field(
        default=True,
        description="Block run when required prices are missing.",
        examples=[True],
    )
    block_on_missing_fx: bool = Field(
        default=True,
        description="Block run when required FX rates are missing.",
        examples=[True],
    )
    min_cash_buffer_pct: Decimal = Field(
        default=Decimal("0.0"),
        description="Minimum cash buffer preserved during target generation.",
        examples=["0.05"],
    )
    max_turnover_pct: Optional[Decimal] = Field(
        default=None,
        description="Optional turnover cap as percentage of portfolio value.",
        examples=["0.15"],
    )
    enable_tax_awareness: bool = Field(
        default=False,
        description="Enable tax-aware lot-based sell allocation.",
        examples=[True],
    )
    max_realized_capital_gains: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Optional run-level realized capital gains budget in base currency.",
        examples=["100"],
    )
    enable_settlement_awareness: bool = Field(
        default=False,
        description="Enable settlement-time cash ladder overdraft checks.",
        examples=[True],
    )
    enable_workflow_gates: bool = Field(
        default=True,
        description="Enable deterministic workflow gate decision output.",
        examples=[True],
    )
    workflow_requires_mandate_approval: bool = Field(
        default=False,
        description=(
            "Require mandate approval before execution in gate-decision policy. "
            "Normally false for discretionary mandate workflows."
        ),
        examples=[False],
    )
    mandate_approval_already_obtained: bool = Field(
        default=False,
        description=(
            "Signals that mandate approval has already been obtained, allowing "
            "gate progression to execution-ready when policy permits."
        ),
        examples=[False],
    )
    link_buy_to_same_currency_sell_dependency: Optional[bool] = Field(
        default=None,
        description=(
            "Attach BUY intent dependency to a same-currency SELL intent. "
            "When null, lotus-manage links same-currency BUY intents to generated SELL funding."
        ),
        examples=[None, True, False],
    )
    settlement_horizon_days: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Settlement ladder horizon in day offsets from T+0.",
        examples=[5],
    )
    fx_settlement_days: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Settlement lag used for generated FX intents.",
        examples=[2],
    )
    max_overdraft_by_ccy: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Optional overdraft allowance by currency for settlement ladder.",
        examples=[{"USD": "1000"}],
    )

    # Key format: "<attribute_key>:<attribute_value>", for example "sector:TECH"
    group_constraints: Dict[str, GroupConstraint] = Field(
        default_factory=dict,
        description="Group constraint map keyed by '<attribute_key>:<attribute_value>'.",
        examples=[{"sector:TECH": {"max_weight": "0.25"}}],
    )

    @field_validator("group_constraints")
    @classmethod
    def validate_group_constraint_keys(
        cls, v: Dict[str, GroupConstraint]
    ) -> Dict[str, GroupConstraint]:
        return _validate_group_constraint_keys(v)

    @field_validator("max_turnover_pct")
    @classmethod
    def validate_max_turnover_pct(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return _validate_optional_ratio_between_zero_and_one(v, field_name="max_turnover_pct")

    @field_validator("max_overdraft_by_ccy")
    @classmethod
    def validate_max_overdraft_by_ccy(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        return _validate_non_negative_amounts_by_currency(v, field_name="max_overdraft_by_ccy")


class AllocationMetric(BaseModel):
    key: str = Field(description="Allocation bucket key (instrument, asset class, or tag value).")
    weight: Decimal = Field(description="Weight of the bucket in portfolio total value.")
    value: Money = Field(description="Monetary value of the bucket.")

    @field_serializer("weight")
    def serialize_weight(self, value: Decimal) -> Decimal:
        return _quantize_ratio(value)


class PositionSummary(BaseModel):
    instrument_id: str = Field(description="Instrument identifier.")
    quantity: Decimal = Field(description="Simulated quantity.")
    instrument_currency: str = Field(description="Instrument trading currency.")
    asset_class: str = Field(default="UNKNOWN", description="Asset-class label for aggregation.")
    price: Optional[Money] = Field(default=None, description="Price used in valuation.")
    value_in_instrument_ccy: Money = Field(description="Position value in instrument currency.")
    value_in_base_ccy: Money = Field(description="Position value converted to base currency.")
    weight: Decimal = Field(description="Portfolio weight in base currency terms.")

    @field_serializer("weight")
    def serialize_weight(self, value: Decimal) -> Decimal:
        return _quantize_ratio(value)


class SimulatedState(BaseModel):
    total_value: Money = Field(description="Total simulated portfolio value in base currency.")
    cash_balances: List[CashBalance] = Field(
        default_factory=list, description="Cash balances by currency."
    )
    positions: List[PositionSummary] = Field(
        default_factory=list, description="Position-level simulated state."
    )
    allocation_by_asset_class: List[AllocationMetric] = Field(
        default_factory=list,
        description="Allocation grouped by asset class plus CASH bucket.",
    )
    allocation_by_instrument: List[AllocationMetric] = Field(
        default_factory=list,
        description="Allocation grouped by instrument id.",
    )
    allocation: List[AllocationMetric] = Field(
        default_factory=list,
        description="Legacy allocation view, aligned to allocation_by_instrument.",
    )
    allocation_by_attribute: Dict[str, List[AllocationMetric]] = Field(
        default_factory=dict,
        description="Allocation grouped by configured shelf attributes.",
    )


class ExcludedInstrument(BaseModel):
    instrument_id: str = Field(description="Instrument excluded from buy/sell universe.")
    reason_code: str = Field(description="Reason code for exclusion.")
    details: Optional[str] = Field(
        default=None, description="Optional details for exclusion reason."
    )


class UniverseCoverage(BaseModel):
    price_coverage_pct: Decimal = Field(
        description="Price coverage percentage for required instruments."
    )
    fx_coverage_pct: Decimal = Field(
        description="FX coverage percentage for required currency pairs."
    )


class UniverseData(BaseModel):
    universe_id: str = Field(description="Universe identifier for the run.")
    eligible_for_buy: List[str] = Field(
        default_factory=list, description="Instrument ids eligible for buy intents."
    )
    eligible_for_sell: List[str] = Field(
        default_factory=list,
        description="Instrument ids eligible for sell intents.",
    )
    excluded: List[ExcludedInstrument] = Field(
        default_factory=list,
        description="Instruments excluded by shelf/data constraints.",
    )
    coverage: UniverseCoverage = Field(description="Market-data coverage metrics.")


class TargetInstrument(BaseModel):
    model_config = {"protected_namespaces": ()}
    instrument_id: str = Field(description="Instrument identifier in target trace.")
    model_weight: Decimal = Field(description="Input model weight.")
    final_weight: Decimal = Field(description="Final constrained target weight.")
    final_value: Money = Field(description="Final constrained target value in base currency.")
    tags: List[str] = Field(
        default_factory=list, description="Trace tags explaining target adjustments."
    )


class TargetData(BaseModel):
    target_id: str = Field(description="Target stage identifier.")
    strategy: Dict[str, Any] = Field(description="Strategy metadata (currently minimal).")
    targets: List[TargetInstrument] = Field(description="Instrument-level target trace output.")


class IntentRationale(BaseModel):
    code: str = Field(description="Short rationale code for generated intent.")
    message: str = Field(description="Human-readable rationale message.")


class SecurityTradeIntent(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = Field(
        default="SECURITY_TRADE",
        description="Intent discriminator.",
    )
    intent_id: str = Field(description="Intent identifier unique within run.")
    instrument_id: str = Field(description="Instrument identifier for trade.")
    side: Literal["BUY", "SELL"] = Field(description="Trade side.")
    quantity: Optional[Decimal] = Field(default=None, description="Trade quantity.")
    notional: Optional[Money] = Field(
        default=None, description="Trade notional in instrument currency."
    )
    notional_base: Optional[Money] = Field(
        default=None, description="Trade notional converted to base currency."
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this intent."
    )
    constraints_applied: List[str] = Field(
        default_factory=list,
        description="Constraint labels applied during sizing.",
    )


class FxSpotIntent(BaseModel):
    intent_type: Literal["FX_SPOT"] = Field(default="FX_SPOT", description="Intent discriminator.")
    intent_id: str = Field(description="Intent identifier unique within run.")
    pair: str = Field(description="FX pair of the conversion intent.")
    buy_currency: str = Field(description="Currency bought by this FX trade.")
    buy_amount: Decimal = Field(description="Estimated amount bought.")
    sell_currency: str = Field(description="Currency sold by this FX trade.")
    sell_amount_estimated: Decimal = Field(description="Estimated amount sold.")
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this FX intent."
    )


OrderIntent = Union[SecurityTradeIntent, FxSpotIntent]


class RuleResult(BaseModel):
    rule_id: str = Field(description="Rule identifier.")
    severity: Literal["HARD", "SOFT", "INFO"] = Field(description="Rule severity tier.")
    status: Literal["PASS", "FAIL"] = Field(description="Rule evaluation outcome.")
    measured: Decimal = Field(description="Measured value used in evaluation.")
    threshold: Dict[str, Decimal] = Field(description="Threshold values applied by the rule.")
    reason_code: str = Field(description="Reason code for rule outcome.")
    remediation_hint: Optional[str] = Field(
        default=None, description="Optional guidance on remediation."
    )


class SuppressedIntent(BaseModel):
    instrument_id: str = Field(description="Instrument id for suppressed trade.")
    reason: str = Field(description="Suppression reason.")
    intended_notional: Money = Field(description="Original intended notional.")
    threshold: Money = Field(description="Suppression threshold that was not met.")


class DroppedIntent(BaseModel):
    instrument_id: str = Field(description="Instrument id for dropped trade under turnover cap.")
    reason: str = Field(description="Drop reason code.")
    potential_notional: Money = Field(description="Potential notional if the trade had been kept.")
    score: Decimal = Field(description="Ranking score used in turnover selection.")


class GroupConstraintEvent(BaseModel):
    constraint_key: str = Field(description="Applied group constraint key.")
    group_weight_before: Decimal = Field(description="Group weight before capping.")
    max_weight: Decimal = Field(description="Configured maximum allowed group weight.")
    released_weight: Decimal = Field(description="Weight released by cap operation.")
    recipients: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Redistribution recipients and allocated weight shares.",
    )
    status: Literal["CAPPED", "BLOCKED"] = Field(description="Constraint application outcome.")


class TaxBudgetConstraintEvent(BaseModel):
    instrument_id: str = Field(description="Instrument constrained by tax budget.")
    requested_quantity: Decimal = Field(description="Requested sell quantity before budget limit.")
    allowed_quantity: Decimal = Field(description="Allowed sell quantity after budget constraint.")
    reason_code: str = Field(description="Constraint reason code.")


class CashLadderPoint(BaseModel):
    date_offset: int = Field(description="Day offset from T+0.")
    currency: str = Field(description="Currency for projected balance.")
    projected_balance: Decimal = Field(description="Projected cumulative balance on the day.")


class CashLadderBreach(BaseModel):
    date_offset: int = Field(description="Day offset where breach occurs.")
    currency: str = Field(description="Currency where breach occurs.")
    projected_balance: Decimal = Field(description="Projected balance at breach point.")
    allowed_floor: Decimal = Field(description="Configured allowed floor for that currency/day.")
    reason_code: str = Field(description="Breach reason code.")


class FundingPlanEntry(BaseModel):
    target_currency: str = Field(description="Currency required by generated BUY intents.")
    required: Decimal = Field(description="Total required amount in target currency.")
    available_before_fx: Decimal = Field(
        description="Available amount in target currency before generated FX."
    )
    fx_needed: Decimal = Field(description="Generated FX buy amount needed in target currency.")
    fx_pair: Optional[str] = Field(
        default=None,
        description="Resolved FX pair used for funding, when available.",
    )
    funding_currency: Optional[str] = Field(
        default=None,
        description="Currency sold to fund target-currency buys.",
    )


class InsufficientCashEntry(BaseModel):
    currency: str = Field(description="Currency where funding cash deficit is detected.")
    deficit: Decimal = Field(description="Deficit amount in the funding currency.")


class DiagnosticsData(BaseModel):
    warnings: List[str] = Field(default_factory=list, description="Run-level warning codes.")
    suppressed_intents: List[SuppressedIntent] = Field(
        default_factory=list,
        description="Intents suppressed during generation (for example dust suppression).",
    )
    dropped_intents: List[DroppedIntent] = Field(
        default_factory=list,
        description="Intents dropped by turnover control.",
    )
    group_constraint_events: List[GroupConstraintEvent] = Field(
        default_factory=list,
        description="Group constraint capping/redistribution events.",
    )
    tax_budget_constraint_events: List[TaxBudgetConstraintEvent] = Field(
        default_factory=list,
        description="Tax budget constraint events by instrument.",
    )
    cash_ladder: List[CashLadderPoint] = Field(
        default_factory=list,
        description="Settlement-aware projected cash ladder points.",
    )
    cash_ladder_breaches: List[CashLadderBreach] = Field(
        default_factory=list,
        description="Settlement ladder breaches that trigger blocks.",
    )
    missing_fx_pairs: List[str] = Field(
        default_factory=list,
        description="Missing FX pairs required for generated funding or valuation.",
    )
    funding_plan: List[FundingPlanEntry] = Field(
        default_factory=list,
        description="Funding plan details for generated FX intents.",
    )
    insufficient_cash: List[InsufficientCashEntry] = Field(
        default_factory=list,
        description="Funding deficits that block simulation.",
    )
    data_quality: Dict[str, List[str]] = Field(
        description="Data-quality issue buckets and affected keys."
    )


class LineageData(BaseModel):
    portfolio_snapshot_id: str = Field(description="Portfolio snapshot id used by run.")
    market_data_snapshot_id: str = Field(description="Market-data snapshot id used by run.")
    request_hash: str = Field(description="Request hash/idempotency marker used in lineage.")
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Request idempotency key.",
        examples=["rebalance-idem-001"],
    )
    engine_version: Optional[str] = Field(
        default=None,
        description="Engine version identifier.",
        examples=["0.1.0"],
    )


class Reconciliation(BaseModel):
    before_total_value: Money = Field(description="Before-state total value.")
    after_total_value: Money = Field(description="After-state total value.")
    delta: Money = Field(description="After minus before.")
    tolerance: Money = Field(description="Allowed reconciliation tolerance.")
    status: Literal["OK", "MISMATCH"] = Field(description="Reconciliation outcome.")


class TaxImpact(BaseModel):
    total_realized_gain: Money = Field(
        description="Aggregate realized gain from constrained sell allocation."
    )
    total_realized_loss: Money = Field(
        description="Aggregate realized loss from constrained sell allocation."
    )
    budget_limit: Optional[Money] = Field(default=None, description="Configured gains budget.")
    budget_used: Optional[Money] = Field(default=None, description="Portion of budget consumed.")


class SuitabilityEvidenceSnapshotIds(BaseModel):
    portfolio_snapshot_id: str = Field(
        description="Portfolio snapshot id used as evidence source.",
        examples=["pf_mandate_01"],
    )
    market_data_snapshot_id: str = Field(
        description="Market-data snapshot id used as evidence source.",
        examples=["md_2026_02_19"],
    )


class SuitabilityEvidence(BaseModel):
    as_of: str = Field(
        description="Suitability evidence as-of identifier derived from request snapshots.",
        examples=["md_2026_02_19"],
    )
    snapshot_ids: SuitabilityEvidenceSnapshotIds = Field(
        description="Snapshot identifiers used by suitability checks."
    )


class SuitabilityIssue(BaseModel):
    issue_id: str = Field(
        description="Stable suitability issue identifier.",
        examples=["SUIT_SINGLE_POSITION_MAX"],
    )
    issue_key: str = Field(
        description="Deterministic issue key used for before/after classification.",
        examples=["SINGLE_POSITION_MAX|US_EQ_ETF"],
    )
    dimension: Literal[
        "CONCENTRATION",
        "ISSUER",
        "LIQUIDITY",
        "GOVERNANCE",
        "CASH",
        "DATA_QUALITY",
    ] = Field(
        description="Suitability issue dimension.",
        examples=["CONCENTRATION"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Mandate review severity level.",
        examples=["HIGH"],
    )
    status_change: Literal["NEW", "RESOLVED", "PERSISTENT"] = Field(
        description="Before/after suitability state transition class.",
        examples=["NEW"],
    )
    summary: str = Field(
        description="Short suitability issue narrative.",
        examples=["Single position exceeds 10% cap."],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic suitability measurement details encoded as strings.",
        examples=[
            {
                "threshold": "0.10",
                "measured_before": "0.12",
                "measured_after": "0.09",
                "instrument_id": "US_EQ_ETF",
            }
        ],
    )
    evidence: SuitabilityEvidence = Field(description="Evidence lineage for this issue.")


class SuitabilitySummary(BaseModel):
    new_count: int = Field(description="Count of NEW suitability issues.", examples=[1])
    resolved_count: int = Field(description="Count of RESOLVED suitability issues.", examples=[2])
    persistent_count: int = Field(
        description="Count of PERSISTENT suitability issues.",
        examples=[3],
    )
    highest_severity_new: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Highest severity among NEW issues, when present.",
        examples=["HIGH"],
    )


class SuitabilityResult(BaseModel):
    summary: SuitabilitySummary = Field(description="Suitability issue summary counts.")
    issues: List[SuitabilityIssue] = Field(
        default_factory=list,
        description="Deterministic ordered suitability issue list.",
    )
    recommended_gate: Literal["NONE", "RISK_REVIEW", "COMPLIANCE_REVIEW"] = Field(
        description="Review gate recommendation derived from NEW issue severities.",
        examples=["COMPLIANCE_REVIEW"],
    )


class GateReason(BaseModel):
    reason_code: str = Field(
        description="Stable workflow reason code.",
        examples=["HARD_RULE_FAIL:INSUFFICIENT_CASH"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Reason severity level used for deterministic ordering.",
        examples=["HIGH"],
    )
    source: Literal["RULE_ENGINE", "SUITABILITY", "DATA_QUALITY"] = Field(
        description="Reason source subsystem.",
        examples=["RULE_ENGINE"],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic structured details for the reason.",
    )


class GateDecisionSummary(BaseModel):
    hard_fail_count: int = Field(description="Count of hard rule failures.", examples=[1])
    soft_fail_count: int = Field(description="Count of soft rule failures.", examples=[0])
    new_high_suitability_count: int = Field(
        description="Count of NEW suitability issues with HIGH severity.",
        examples=[0],
    )
    new_medium_suitability_count: int = Field(
        description="Count of NEW suitability issues with MEDIUM severity.",
        examples=[0],
    )


class GateDecision(BaseModel):
    gate: Literal[
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "MANDATE_APPROVAL_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    ] = Field(
        description="Deterministic workflow gate outcome.",
        examples=["MANDATE_APPROVAL_REQUIRED"],
    )
    recommended_next_step: Literal[
        "FIX_INPUT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "REQUEST_MANDATE_APPROVAL",
        "EXECUTE",
        "NONE",
    ] = Field(
        description="Recommended next workflow step based on gate policy.",
        examples=["REQUEST_MANDATE_APPROVAL"],
    )
    reasons: List[GateReason] = Field(
        default_factory=list,
        description="Deterministic ordered reasons explaining the gate.",
    )
    summary: GateDecisionSummary = Field(description="Gate summary counters.")


class RebalanceResult(BaseModel):
    """The complete, auditable result of a rebalance simulation."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "rebalance_run_id": "rr_abc12345",
                "status": "READY",
                "correlation_id": "c_none",
                "intents": [],
                "rule_results": [],
                "diagnostics": {
                    "warnings": [],
                    "data_quality": {"price_missing": [], "fx_missing": []},
                },
            }
        }
    }

    rebalance_run_id: str = Field(description="Run identifier.")
    correlation_id: str = Field(description="Correlation id used by request logging context.")
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"] = Field(
        description="Top-level domain outcome."
    )
    before: SimulatedState = Field(description="Before-state valuation snapshot.")
    universe: UniverseData = Field(description="Universe composition and exclusions.")
    target: TargetData = Field(description="Target generation trace.")
    intents: List[Annotated[OrderIntent, Field(discriminator="intent_type")]]
    after_simulated: SimulatedState = Field(description="After-state simulation snapshot.")
    reconciliation: Optional[Reconciliation] = Field(
        default=None, description="Reconciliation output."
    )
    tax_impact: Optional[TaxImpact] = Field(
        default=None, description="Tax impact summary when tax-aware enabled."
    )
    rule_results: List[RuleResult] = Field(
        default_factory=list, description="Rule engine evaluations."
    )
    explanation: Dict[str, Any] = Field(description="Additional explanatory payload.")
    diagnostics: DiagnosticsData = Field(description="Diagnostics and warnings for the run.")
    gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Deterministic workflow gate decision for downstream orchestration.",
    )
    lineage: LineageData = Field(description="Lineage identifiers and request hash.")


class SimulationScenario(BaseModel):
    description: Optional[str] = Field(default=None, description="Optional scenario description.")
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scenario-specific EngineOptions override payload.",
    )


class BatchRebalanceRequest(BaseModel):
    MAX_SCENARIOS_PER_REQUEST: ClassVar[int] = 20
    SCENARIO_NAME_PATTERN: ClassVar[re.Pattern[str]] = _SCENARIO_NAME_REGEX
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_batch",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "scenarios": {
                    "baseline": {"options": {}},
                    "solver_case": {"options": {"target_method": "SOLVER"}},
                },
            }
        }
    }

    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Shared portfolio snapshot for all scenarios.",
        examples=[{"portfolio_id": "pf_batch", "base_currency": "USD"}],
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Shared market-data snapshot for all scenarios.",
        examples=[{"prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}]}],
    )
    model_portfolio: ModelPortfolio = Field(
        description="Shared model targets for all scenarios.",
        examples=[{"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]}],
    )
    shelf_entries: List[ShelfEntry] = Field(
        description="Shared shelf metadata for all scenarios.",
        examples=[[{"instrument_id": "EQ_1", "status": "APPROVED"}]],
    )
    scenarios: Dict[str, SimulationScenario] = Field(
        description="Named scenario map for batch analysis.",
        examples=[
            {"baseline": {"options": {}}, "turnover_cap": {"options": {"max_turnover_pct": "0.1"}}}
        ],
    )

    @field_validator("scenarios")
    @classmethod
    def validate_scenarios(
        cls, scenarios: Dict[str, SimulationScenario]
    ) -> Dict[str, SimulationScenario]:
        if not scenarios:
            raise ValueError("at least one scenario is required")
        if len(scenarios) > cls.MAX_SCENARIOS_PER_REQUEST:
            raise ValueError(f"scenario count exceeds maximum of {cls.MAX_SCENARIOS_PER_REQUEST}")

        for scenario_name in scenarios:
            if not cls.SCENARIO_NAME_PATTERN.fullmatch(scenario_name):
                raise ValueError("scenario names must match regex [a-z0-9_\\-]{1,64}")

        return scenarios


class BatchScenarioMetric(BaseModel):
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"] = Field(
        description="Scenario run status.",
        examples=["READY"],
    )
    security_intent_count: int = Field(
        description="Count of SECURITY_TRADE intents.",
        examples=[1],
    )
    gross_turnover_notional_base: Money = Field(
        description="Gross turnover proxy in base currency.",
        examples=[{"amount": "4500.00", "currency": "USD"}],
    )


class BatchRebalanceResult(BaseModel):
    batch_run_id: str = Field(
        description="Batch execution identifier.", examples=["batch_ab12cd34"]
    )
    run_at_utc: str = Field(
        description="Batch execution timestamp (UTC ISO8601).",
        examples=["2026-02-18T10:00:00+00:00"],
    )
    base_snapshot_ids: Dict[str, str] = Field(
        description="Resolved base snapshot identifiers.",
        examples=[{"portfolio_snapshot_id": "pf_batch", "market_data_snapshot_id": "md"}],
    )
    results: Dict[str, RebalanceResult] = Field(
        default_factory=dict,
        description="Successful scenario results keyed by scenario name.",
        examples=[{"baseline": {"status": "READY", "rebalance_run_id": "rr_batch_baseline_001"}}],
    )
    comparison_metrics: Dict[str, BatchScenarioMetric] = Field(
        default_factory=dict,
        description="Per-scenario comparison metrics for successful scenarios.",
        examples=[
            {
                "baseline": {
                    "status": "READY",
                    "security_intent_count": 1,
                    "gross_turnover_notional_base": {"amount": "4500.00", "currency": "USD"},
                }
            }
        ],
    )
    failed_scenarios: Dict[str, str] = Field(
        default_factory=dict,
        description="Validation/runtime failures keyed by scenario name.",
        examples=[{"invalid_case": "INVALID_OPTIONS: validation failed"}],
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Batch-level warning codes.",
        examples=[["PARTIAL_BATCH_FAILURE"]],
    )
