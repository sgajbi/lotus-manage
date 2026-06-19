from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    IntentRationale,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    SecurityTradeIntent,
    ShelfEntry,
    SuppressedIntent,
    TaxImpact,
)
from src.core.rebalance.tax_budget import (
    _SellQuantityDecision,
    _TaxBudgetAccumulator,
    _TaxBudgetLotAllowance,
    _apply_tax_budget_lot_allowance,
    _clamped_sell_quantity,
    _hifo_sorted_lots,
    _record_tax_budget_limit_reached,
    _sell_quantity_after_safety_limits,
    _tax_budget_allowance_stops_lot_scan,
    _tax_budget_constraint_applies,
    _tax_budget_limited_quantity_from_lots,
    _tax_budget_limited_sell_quantity,
    _tax_budget_lot_allowance,
    _tax_budget_sale_allowance,
    _tax_impact_from_budget,
)
from src.core.valuation import get_fx_rate

__all__ = [
    "generate_intents",
    "_SellQuantityDecision",
    "_TaxBudgetAccumulator",
    "_TaxBudgetLotAllowance",
    "_TargetIntentContext",
    "_TargetTradeDelta",
    "_append_security_trade_intent",
    "_apply_tax_budget_lot_allowance",
    "_available_holding_constraint_applies",
    "_clamped_sell_quantity",
    "_current_instrument_value_and_unit_value",
    "_hifo_sorted_lots",
    "_intent_market_context",
    "_record_tax_budget_limit_reached",
    "_security_intent_constraints",
    "_security_trade_intent",
    "_sell_quantity_after_safety_limits",
    "_suppress_dust_trade",
    "_target_intent_context",
    "_target_trade_delta",
    "_target_weight_by_instrument",
    "_tax_budget_allowance_stops_lot_scan",
    "_tax_budget_constraint_applies",
    "_tax_budget_limited_quantity_from_lots",
    "_tax_budget_limited_sell_quantity",
    "_tax_budget_lot_allowance",
    "_tax_budget_sale_allowance",
    "_tax_impact_from_budget",
    "_trade_notional_threshold",
]


def _trade_notional_threshold(
    *,
    options: EngineOptions,
    shelf_entry: ShelfEntry | None,
) -> Money | None:
    if options.min_trade_notional:
        return options.min_trade_notional
    if shelf_entry and shelf_entry.min_notional:
        return shelf_entry.min_notional
    return None


def _security_intent_constraints(
    *,
    threshold: Money | None,
    side: Literal["BUY", "SELL"],
    quantity: Decimal,
    requested_quantity: Decimal,
    sell_quantity_before_tax: Decimal | None,
    tax_awareness_enabled: bool,
) -> list[str]:
    applied_constraints = ["MIN_NOTIONAL"] if threshold else []
    if _available_holding_constraint_applies(
        side=side,
        quantity=quantity,
        requested_quantity=requested_quantity,
    ):
        applied_constraints.append("AVAILABLE_HOLDING")
    if _tax_budget_constraint_applies(
        side=side,
        quantity=quantity,
        sell_quantity_before_tax=sell_quantity_before_tax,
        tax_awareness_enabled=tax_awareness_enabled,
    ):
        applied_constraints.append("TAX_BUDGET")
    return applied_constraints


def _available_holding_constraint_applies(
    *,
    side: Literal["BUY", "SELL"],
    quantity: Decimal,
    requested_quantity: Decimal,
) -> bool:
    return side == "SELL" and quantity < requested_quantity


def _suppress_dust_trade(
    *,
    instrument_id: str,
    notional: Decimal,
    notional_currency: str,
    threshold: Money | None,
    options: EngineOptions,
    suppressed: list[SuppressedIntent],
) -> bool:
    if not options.suppress_dust_trades or threshold is None or notional >= threshold.amount:
        return False

    suppressed.append(
        SuppressedIntent(
            instrument_id=instrument_id,
            reason="BELOW_MIN_NOTIONAL",
            intended_notional=Money(amount=notional, currency=notional_currency),
            threshold=threshold,
        )
    )
    return True


@dataclass(frozen=True)
class _TargetTradeDelta:
    side: Literal["BUY", "SELL"]
    raw_quantity: Decimal


@dataclass(frozen=True)
class _TargetIntentContext:
    instrument_id: str
    side: Literal["BUY", "SELL"]
    requested_quantity: Decimal
    quantity: Decimal
    unit_value: Decimal
    base_rate: Decimal
    price_currency: str
    threshold: Money | None
    sell_quantity_before_tax: Decimal | None


def _target_trade_delta(
    *,
    target_instrument_value: Decimal,
    current_instrument_value: Decimal,
    unit_value: Decimal,
) -> _TargetTradeDelta:
    delta = target_instrument_value - current_instrument_value
    side: Literal["BUY", "SELL"] = "BUY" if delta > 0 else "SELL"
    raw_quantity = Decimal(int(abs(delta) // unit_value))
    return _TargetTradeDelta(side=side, raw_quantity=raw_quantity)


def _intent_market_context(
    *,
    instrument_id: str,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
) -> tuple[Price, Decimal, Position | None] | None:
    price = next((item for item in market_data.prices if item.instrument_id == instrument_id), None)
    if price is None:
        dq_log["price_missing"].append(instrument_id)
        return None

    rate = get_fx_rate(market_data, price.currency, portfolio.base_currency)
    if not rate:
        dq_log["fx_missing"].append(f"{price.currency}/{portfolio.base_currency}")
        return None

    position = next(
        (item for item in portfolio.positions if item.instrument_id == instrument_id),
        None,
    )
    return price, rate, position


def _current_instrument_value_and_unit_value(
    *,
    position: Position | None,
    price: Price,
) -> tuple[Decimal, Decimal]:
    if position is None:
        return Decimal("0"), price.price
    if position.market_value is None:
        return position.quantity * price.price, price.price

    current_value = position.market_value.amount
    if position.quantity > Decimal("0"):
        return current_value, current_value / position.quantity
    return current_value, price.price


def _target_weight_by_instrument(targets: list[Any]) -> dict[str, Decimal]:
    return {target.instrument_id: target.final_weight for target in targets}


def _security_trade_intent(
    *,
    intent_id: str,
    side: Literal["BUY", "SELL"],
    instrument_id: str,
    quantity: Decimal,
    unit_value: Decimal,
    base_rate: Decimal,
    price_currency: str,
    portfolio_base_currency: str,
    threshold: Money | None,
    requested_quantity: Decimal,
    sell_quantity_before_tax: Decimal | None,
    tax_awareness_enabled: bool,
) -> SecurityTradeIntent:
    notional = quantity * unit_value
    return SecurityTradeIntent(
        intent_id=intent_id,
        side=side,
        instrument_id=instrument_id,
        quantity=quantity,
        notional=Money(amount=notional, currency=price_currency),
        notional_base=Money(amount=notional * base_rate, currency=portfolio_base_currency),
        rationale=IntentRationale(code="DRIFT_REBALANCE", message="Align"),
        constraints_applied=_security_intent_constraints(
            threshold=threshold,
            side=side,
            quantity=quantity,
            requested_quantity=requested_quantity,
            sell_quantity_before_tax=sell_quantity_before_tax,
            tax_awareness_enabled=tax_awareness_enabled,
        ),
    )


def _target_intent_context(
    *,
    instrument_id: str,
    target_weight: Decimal,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    total_val: Decimal,
    dq_log: dict[str, list[str]],
    diagnostics: DiagnosticsData,
    suppressed: list[SuppressedIntent],
    tax_budget: _TaxBudgetAccumulator,
) -> _TargetIntentContext | None:
    market_context = _intent_market_context(
        instrument_id=instrument_id,
        portfolio=portfolio,
        market_data=market_data,
        dq_log=dq_log,
    )
    if market_context is None:
        return None
    price_ent, rate, curr = market_context

    curr_instr_val, unit_value = _current_instrument_value_and_unit_value(
        position=curr,
        price=price_ent,
    )
    target_instr_val = (total_val * target_weight) / rate
    trade_delta = _target_trade_delta(
        target_instrument_value=target_instr_val,
        current_instrument_value=curr_instr_val,
        unit_value=unit_value,
    )
    sell_quantity = _sell_quantity_after_safety_limits(
        instrument_id=instrument_id,
        side=trade_delta.side,
        requested_quantity=trade_delta.raw_quantity,
        position=curr,
        options=options,
        sell_price=unit_value,
        price_currency=price_ent.currency,
        base_rate=rate,
        market_data=market_data,
        dq_log=dq_log,
        tax_budget=tax_budget,
        diagnostics=diagnostics,
    )
    shelf_ent = next((s for s in shelf if s.instrument_id == instrument_id), None)
    threshold = _trade_notional_threshold(options=options, shelf_entry=shelf_ent)
    notional = sell_quantity.quantity * unit_value

    if _suppress_dust_trade(
        instrument_id=instrument_id,
        notional=notional,
        notional_currency=price_ent.currency,
        threshold=threshold,
        options=options,
        suppressed=suppressed,
    ):
        return None

    return _TargetIntentContext(
        instrument_id=instrument_id,
        side=trade_delta.side,
        requested_quantity=trade_delta.raw_quantity,
        quantity=sell_quantity.quantity,
        unit_value=unit_value,
        base_rate=rate,
        price_currency=price_ent.currency,
        threshold=threshold,
        sell_quantity_before_tax=sell_quantity.sell_quantity_before_tax,
    )


def _append_security_trade_intent(
    *,
    intents: list[SecurityTradeIntent],
    context: _TargetIntentContext,
    portfolio_base_currency: str,
    tax_awareness_enabled: bool,
) -> None:
    if context.quantity <= Decimal("0"):
        return

    intents.append(
        _security_trade_intent(
            intent_id=f"oi_{len(intents) + 1}",
            side=context.side,
            instrument_id=context.instrument_id,
            quantity=context.quantity,
            unit_value=context.unit_value,
            base_rate=context.base_rate,
            price_currency=context.price_currency,
            portfolio_base_currency=portfolio_base_currency,
            threshold=context.threshold,
            requested_quantity=context.requested_quantity,
            sell_quantity_before_tax=context.sell_quantity_before_tax,
            tax_awareness_enabled=tax_awareness_enabled,
        )
    )


def generate_intents(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    targets: list[Any],
    shelf: list[ShelfEntry],
    options: EngineOptions,
    total_val: Decimal,
    dq_log: dict[str, list[str]],
    diagnostics: DiagnosticsData,
    suppressed: list[SuppressedIntent],
) -> tuple[list[SecurityTradeIntent], TaxImpact | None]:
    intents: list[SecurityTradeIntent] = []
    tax_budget = _TaxBudgetAccumulator(
        total_realized_gain_base=Decimal("0"),
        total_realized_loss_base=Decimal("0"),
        tax_budget_used_base=Decimal("0"),
        tax_budget_limit_base=options.max_realized_capital_gains,
    )

    target_dict = _target_weight_by_instrument(targets)
    for i_id, target_w in target_dict.items():
        intent_context = _target_intent_context(
            instrument_id=i_id,
            portfolio=portfolio,
            market_data=market_data,
            shelf=shelf,
            options=options,
            total_val=total_val,
            target_weight=target_w,
            dq_log=dq_log,
            tax_budget=tax_budget,
            diagnostics=diagnostics,
            suppressed=suppressed,
        )
        if intent_context is None:
            continue

        _append_security_trade_intent(
            intents=intents,
            context=intent_context,
            portfolio_base_currency=portfolio.base_currency,
            tax_awareness_enabled=options.enable_tax_awareness,
        )

    tax_impact = None
    if options.enable_tax_awareness:
        tax_impact = _tax_impact_from_budget(
            tax_budget=tax_budget,
            base_currency=portfolio.base_currency,
        )

    return intents, tax_impact
