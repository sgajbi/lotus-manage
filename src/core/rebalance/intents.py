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
    TaxBudgetConstraintEvent,
    TaxImpact,
)
from src.core.valuation import get_fx_rate


def _lot_cost_in_instrument_ccy(
    *,
    unit_cost: Money,
    instrument_ccy: str,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
) -> Decimal | None:
    if unit_cost.currency == instrument_ccy:
        return unit_cost.amount
    fx = get_fx_rate(market_data, unit_cost.currency, instrument_ccy)
    if fx is None:
        dq_log["fx_missing"].append(f"{unit_cost.currency}/{instrument_ccy}")
        return None
    return unit_cost.amount * fx


def _hifo_sorted_lots(
    *,
    position: Position | None,
    instrument_ccy: str,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
) -> list[tuple[Any, Decimal]]:
    if not position or not position.lots:
        return []
    lots_with_cost = []
    for lot in position.lots:
        cost = _lot_cost_in_instrument_ccy(
            unit_cost=lot.unit_cost,
            instrument_ccy=instrument_ccy,
            market_data=market_data,
            dq_log=dq_log,
        )
        if cost is None:
            return []
        lots_with_cost.append((lot, cost))
    return sorted(
        lots_with_cost,
        key=lambda item: (item[1], item[0].purchase_date, item[0].lot_id),
        reverse=True,
    )


def _clamped_sell_quantity(
    *,
    requested_qty: Decimal,
    position: Position | None,
    diagnostics: DiagnosticsData,
) -> Decimal:
    available_qty = position.quantity if position is not None else Decimal("0")
    if requested_qty <= available_qty:
        return requested_qty
    if "SELL_QUANTITY_CLAMPED_TO_AVAILABLE_HOLDING" not in diagnostics.warnings:
        diagnostics.warnings.append("SELL_QUANTITY_CLAMPED_TO_AVAILABLE_HOLDING")
    return max(available_qty, Decimal("0"))


def _record_tax_budget_limit_reached(
    *,
    instrument_id: str,
    requested_quantity: Decimal,
    allowed_quantity: Decimal,
    diagnostics: DiagnosticsData,
) -> None:
    if "TAX_BUDGET_LIMIT_REACHED" not in diagnostics.warnings:
        diagnostics.warnings.append("TAX_BUDGET_LIMIT_REACHED")
    diagnostics.tax_budget_constraint_events.append(
        TaxBudgetConstraintEvent(
            instrument_id=instrument_id,
            requested_quantity=requested_quantity,
            allowed_quantity=allowed_quantity,
            reason_code="TAX_BUDGET_LIMIT_REACHED",
        )
    )


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
    if side == "SELL" and quantity < requested_quantity:
        applied_constraints.append("AVAILABLE_HOLDING")
    if (
        side == "SELL"
        and tax_awareness_enabled
        and sell_quantity_before_tax is not None
        and quantity < sell_quantity_before_tax
    ):
        applied_constraints.append("TAX_BUDGET")
    return applied_constraints


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


@dataclass
class _TaxBudgetAccumulator:
    total_realized_gain_base: Decimal
    total_realized_loss_base: Decimal
    tax_budget_used_base: Decimal
    tax_budget_limit_base: Decimal | None


@dataclass(frozen=True)
class _TargetTradeDelta:
    side: Literal["BUY", "SELL"]
    raw_quantity: Decimal


@dataclass(frozen=True)
class _TaxBudgetLotAllowance:
    requested_quantity: Decimal
    allowed_quantity: Decimal
    realized_base: Decimal


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


def _tax_budget_allowed_lot_quantity(
    *,
    lot_sell_qty: Decimal,
    per_unit_gain_base: Decimal,
    tax_budget: _TaxBudgetAccumulator,
) -> Decimal:
    if tax_budget.tax_budget_limit_base is None or per_unit_gain_base <= Decimal("0"):
        return lot_sell_qty
    if tax_budget.tax_budget_used_base >= tax_budget.tax_budget_limit_base:
        return Decimal("0")

    remaining_headroom = tax_budget.tax_budget_limit_base - tax_budget.tax_budget_used_base
    max_qty_headroom = remaining_headroom / per_unit_gain_base
    return min(lot_sell_qty, max_qty_headroom)


def _tax_budget_lot_allowance(
    *,
    remaining_quantity: Decimal,
    lot_quantity: Decimal,
    lot_unit_cost: Decimal,
    sell_price: Decimal,
    base_rate: Decimal,
    tax_budget: _TaxBudgetAccumulator,
) -> _TaxBudgetLotAllowance:
    lot_sell_qty = min(remaining_quantity, lot_quantity)
    per_unit_gain_base = (sell_price - lot_unit_cost) * base_rate
    allowed_quantity = _tax_budget_allowed_lot_quantity(
        lot_sell_qty=lot_sell_qty,
        per_unit_gain_base=per_unit_gain_base,
        tax_budget=tax_budget,
    )
    return _TaxBudgetLotAllowance(
        requested_quantity=lot_sell_qty,
        allowed_quantity=allowed_quantity,
        realized_base=per_unit_gain_base * allowed_quantity,
    )


def _apply_tax_budget_lot_allowance(
    *,
    allowance: _TaxBudgetLotAllowance,
    tax_budget: _TaxBudgetAccumulator,
) -> None:
    if allowance.realized_base >= Decimal("0"):
        tax_budget.total_realized_gain_base += allowance.realized_base
        tax_budget.tax_budget_used_base += allowance.realized_base
    else:
        tax_budget.total_realized_loss_base += abs(allowance.realized_base)


def _tax_budget_limited_sell_quantity(
    *,
    options: EngineOptions,
    position: Position | None,
    requested_qty: Decimal,
    sell_price: Decimal,
    price_ccy: str,
    base_rate: Decimal,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
    tax_budget: _TaxBudgetAccumulator,
) -> Decimal:
    if not options.enable_tax_awareness:
        return requested_qty

    sorted_lots = _hifo_sorted_lots(
        position=position,
        instrument_ccy=price_ccy,
        market_data=market_data,
        dq_log=dq_log,
    )
    if not sorted_lots:
        return requested_qty

    remaining = requested_qty
    allowed_qty = Decimal("0")
    for lot, lot_unit_cost in sorted_lots:
        if remaining <= Decimal("0"):
            break
        if lot.quantity <= Decimal("0"):
            continue

        allowance = _tax_budget_lot_allowance(
            remaining_quantity=remaining,
            lot_quantity=lot.quantity,
            lot_unit_cost=lot_unit_cost,
            sell_price=sell_price,
            base_rate=base_rate,
            tax_budget=tax_budget,
        )
        if allowance.allowed_quantity <= Decimal("0"):
            break

        _apply_tax_budget_lot_allowance(allowance=allowance, tax_budget=tax_budget)

        allowed_qty += allowance.allowed_quantity
        remaining -= allowance.allowed_quantity

        if allowance.allowed_quantity < allowance.requested_quantity:
            break

    return allowed_qty


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


def _tax_impact_from_budget(
    *,
    tax_budget: _TaxBudgetAccumulator,
    base_currency: str,
) -> TaxImpact:
    normalized_budget_used = tax_budget.tax_budget_used_base
    if tax_budget.tax_budget_limit_base is not None:
        if abs(tax_budget.tax_budget_limit_base - normalized_budget_used) <= Decimal(
            "0.0000000001"
        ):
            normalized_budget_used = tax_budget.tax_budget_limit_base
    budget_limit = (
        Money(amount=tax_budget.tax_budget_limit_base, currency=base_currency)
        if tax_budget.tax_budget_limit_base is not None
        else None
    )
    budget_used = (
        Money(
            amount=min(normalized_budget_used, tax_budget.tax_budget_limit_base),
            currency=base_currency,
        )
        if tax_budget.tax_budget_limit_base is not None
        else None
    )
    return TaxImpact(
        total_realized_gain=Money(
            amount=tax_budget.total_realized_gain_base,
            currency=base_currency,
        ),
        total_realized_loss=Money(
            amount=tax_budget.total_realized_loss_base,
            currency=base_currency,
        ),
        budget_limit=budget_limit,
        budget_used=budget_used,
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

    target_dict = {t.instrument_id: t.final_weight for t in targets}
    for i_id, target_w in target_dict.items():
        market_context = _intent_market_context(
            instrument_id=i_id,
            portfolio=portfolio,
            market_data=market_data,
            dq_log=dq_log,
        )
        if market_context is None:
            continue
        price_ent, rate, curr = market_context

        curr_instr_val, unit_value = _current_instrument_value_and_unit_value(
            position=curr,
            price=price_ent,
        )

        target_instr_val = (total_val * target_w) / rate

        trade_delta = _target_trade_delta(
            target_instrument_value=target_instr_val,
            current_instrument_value=curr_instr_val,
            unit_value=unit_value,
        )
        side = trade_delta.side
        requested_quantity = trade_delta.raw_quantity
        quantity = requested_quantity

        sell_quantity_before_tax: Decimal | None = None
        if side == "SELL" and requested_quantity > 0:
            quantity = _clamped_sell_quantity(
                requested_qty=requested_quantity,
                position=curr,
                diagnostics=diagnostics,
            )
            sell_quantity_before_tax = quantity
            quantity = _tax_budget_limited_sell_quantity(
                options=options,
                position=curr,
                requested_qty=sell_quantity_before_tax,
                sell_price=unit_value,
                price_ccy=price_ent.currency,
                base_rate=rate,
                market_data=market_data,
                dq_log=dq_log,
                tax_budget=tax_budget,
            )
            if options.enable_tax_awareness and quantity < sell_quantity_before_tax:
                _record_tax_budget_limit_reached(
                    instrument_id=i_id,
                    requested_quantity=sell_quantity_before_tax,
                    allowed_quantity=quantity,
                    diagnostics=diagnostics,
                )

        notional = quantity * unit_value
        notional_base = notional * rate

        shelf_ent = next((s for s in shelf if s.instrument_id == i_id), None)
        threshold = _trade_notional_threshold(options=options, shelf_entry=shelf_ent)

        if _suppress_dust_trade(
            instrument_id=i_id,
            notional=notional,
            notional_currency=price_ent.currency,
            threshold=threshold,
            options=options,
            suppressed=suppressed,
        ):
            continue

        if quantity > 0:
            applied_constraints = _security_intent_constraints(
                threshold=threshold,
                side=side,
                quantity=quantity,
                requested_quantity=requested_quantity,
                sell_quantity_before_tax=sell_quantity_before_tax,
                tax_awareness_enabled=options.enable_tax_awareness,
            )
            intents.append(
                SecurityTradeIntent(
                    intent_id=f"oi_{len(intents) + 1}",
                    side=side,
                    instrument_id=i_id,
                    quantity=quantity,
                    notional=Money(amount=notional, currency=price_ent.currency),
                    notional_base=Money(amount=notional_base, currency=portfolio.base_currency),
                    rationale=IntentRationale(code="DRIFT_REBALANCE", message="Align"),
                    constraints_applied=applied_constraints,
                )
            )

    tax_impact = None
    if options.enable_tax_awareness:
        tax_impact = _tax_impact_from_budget(
            tax_budget=tax_budget,
            base_currency=portfolio.base_currency,
        )

    return intents, tax_impact
