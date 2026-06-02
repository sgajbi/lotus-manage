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


@dataclass
class _TaxBudgetAccumulator:
    total_realized_gain_base: Decimal
    total_realized_loss_base: Decimal
    tax_budget_used_base: Decimal
    tax_budget_limit_base: Decimal | None


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

        lot_sell_qty = min(remaining, lot.quantity)
        per_unit_gain_base = (sell_price - lot_unit_cost) * base_rate
        allowed_from_lot = lot_sell_qty

        if (
            tax_budget.tax_budget_limit_base is not None
            and per_unit_gain_base > Decimal("0")
            and tax_budget.tax_budget_used_base < tax_budget.tax_budget_limit_base
        ):
            remaining_headroom = tax_budget.tax_budget_limit_base - tax_budget.tax_budget_used_base
            max_qty_headroom = remaining_headroom / per_unit_gain_base
            allowed_from_lot = min(lot_sell_qty, max_qty_headroom)
        elif (
            tax_budget.tax_budget_limit_base is not None
            and per_unit_gain_base > Decimal("0")
            and tax_budget.tax_budget_used_base >= tax_budget.tax_budget_limit_base
        ):
            allowed_from_lot = Decimal("0")

        if allowed_from_lot <= Decimal("0"):
            break

        lot_realized_base = per_unit_gain_base * allowed_from_lot
        if lot_realized_base >= Decimal("0"):
            tax_budget.total_realized_gain_base += lot_realized_base
            tax_budget.tax_budget_used_base += lot_realized_base
        else:
            tax_budget.total_realized_loss_base += abs(lot_realized_base)

        allowed_qty += allowed_from_lot
        remaining -= allowed_from_lot

        if allowed_from_lot < lot_sell_qty:
            break

    return allowed_qty


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
        price_ent = next((p for p in market_data.prices if p.instrument_id == i_id), None)
        if not price_ent:
            dq_log["price_missing"].append(i_id)
            continue
        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        if not rate:
            dq_log["fx_missing"].append(f"{price_ent.currency}/{portfolio.base_currency}")
            continue

        curr = next((p for p in portfolio.positions if p.instrument_id == i_id), None)
        curr_instr_val = (
            curr.market_value.amount
            if curr and curr.market_value
            else (curr.quantity * price_ent.price if curr else Decimal("0"))
        )
        unit_value = price_ent.price
        if curr and curr.market_value and curr.quantity > Decimal("0"):
            unit_value = curr.market_value.amount / curr.quantity

        target_instr_val = (total_val * target_w) / rate

        delta = target_instr_val - curr_instr_val
        side: Literal["BUY", "SELL"] = "BUY" if delta > 0 else "SELL"
        qty = int(abs(delta) // unit_value)
        quantity = Decimal(qty)

        sell_quantity_before_tax: Decimal | None = None
        if side == "SELL" and qty > 0:
            requested_qty = Decimal(qty)
            quantity = _clamped_sell_quantity(
                requested_qty=requested_qty,
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

        if options.suppress_dust_trades and threshold and notional < threshold.amount:
            suppressed.append(
                SuppressedIntent(
                    instrument_id=i_id,
                    reason="BELOW_MIN_NOTIONAL",
                    intended_notional=Money(amount=notional, currency=price_ent.currency),
                    threshold=threshold,
                )
            )
            continue

        if quantity > 0:
            applied_constraints = _security_intent_constraints(
                threshold=threshold,
                side=side,
                quantity=quantity,
                requested_quantity=Decimal(qty),
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
        normalized_budget_used = tax_budget.tax_budget_used_base
        if tax_budget.tax_budget_limit_base is not None:
            if abs(tax_budget.tax_budget_limit_base - normalized_budget_used) <= Decimal(
                "0.0000000001"
            ):
                normalized_budget_used = tax_budget.tax_budget_limit_base
        budget_limit = (
            Money(amount=tax_budget.tax_budget_limit_base, currency=portfolio.base_currency)
            if tax_budget.tax_budget_limit_base is not None
            else None
        )
        budget_used = (
            Money(
                amount=min(normalized_budget_used, tax_budget.tax_budget_limit_base),
                currency=portfolio.base_currency,
            )
            if tax_budget.tax_budget_limit_base is not None
            else None
        )
        tax_impact = TaxImpact(
            total_realized_gain=Money(
                amount=tax_budget.total_realized_gain_base,
                currency=portfolio.base_currency,
            ),
            total_realized_loss=Money(
                amount=tax_budget.total_realized_loss_base,
                currency=portfolio.base_currency,
            ),
            budget_limit=budget_limit,
            budget_used=budget_used,
        )

    return intents, tax_impact
