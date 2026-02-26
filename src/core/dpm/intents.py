from decimal import Decimal
from typing import Any, cast

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    IntentRationale,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    SecurityTradeIntent,
    ShelfEntry,
    SuppressedIntent,
    TaxBudgetConstraintEvent,
    TaxImpact,
)
from src.core.valuation import get_fx_rate


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
    total_realized_gain_base = Decimal("0")
    total_realized_loss_base = Decimal("0")
    tax_budget_used_base = Decimal("0")
    tax_budget_limit_base = options.max_realized_capital_gains

    def lot_cost_in_instrument_ccy(unit_cost: Money, instrument_ccy: str) -> Decimal | None:
        if unit_cost.currency == instrument_ccy:
            return cast(Decimal, unit_cost.amount)
        fx = get_fx_rate(market_data, unit_cost.currency, instrument_ccy)
        if fx is None:
            dq_log["fx_missing"].append(f"{unit_cost.currency}/{instrument_ccy}")
            return None
        return cast(Decimal, unit_cost.amount * fx)

    def hifo_sorted_lots(position: Any, instrument_ccy: str) -> list[tuple[Any, Decimal]]:
        if not position or not position.lots:
            return []
        lots_with_cost = []
        for lot in position.lots:
            cost = lot_cost_in_instrument_ccy(lot.unit_cost, instrument_ccy)
            if cost is None:
                return []
            lots_with_cost.append((lot, cost))
        return sorted(
            lots_with_cost,
            key=lambda item: (item[1], item[0].purchase_date, item[0].lot_id),
            reverse=True,
        )

    def apply_tax_budget_sell_limit(
        position: Any,
        requested_qty: Decimal,
        sell_price: Decimal,
        price_ccy: str,
        base_rate: Decimal,
    ) -> Decimal:
        nonlocal total_realized_gain_base, total_realized_loss_base, tax_budget_used_base

        if not options.enable_tax_awareness:
            return requested_qty

        sorted_lots = hifo_sorted_lots(position, price_ccy)
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
                tax_budget_limit_base is not None
                and per_unit_gain_base > Decimal("0")
                and tax_budget_used_base < tax_budget_limit_base
            ):
                remaining_headroom = tax_budget_limit_base - tax_budget_used_base
                max_qty_headroom = remaining_headroom / per_unit_gain_base
                allowed_from_lot = min(lot_sell_qty, max_qty_headroom)
            elif (
                tax_budget_limit_base is not None
                and per_unit_gain_base > Decimal("0")
                and tax_budget_used_base >= tax_budget_limit_base
            ):
                allowed_from_lot = Decimal("0")

            if allowed_from_lot <= Decimal("0"):
                break

            lot_realized_base = per_unit_gain_base * allowed_from_lot
            if lot_realized_base >= Decimal("0"):
                total_realized_gain_base += lot_realized_base
                tax_budget_used_base += lot_realized_base
            else:
                total_realized_loss_base += abs(lot_realized_base)

            allowed_qty += allowed_from_lot
            remaining -= allowed_from_lot

            if allowed_from_lot < lot_sell_qty:
                break

        return allowed_qty

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

        target_instr_val = (total_val * target_w) / rate
        curr = next((p for p in portfolio.positions if p.instrument_id == i_id), None)
        curr_instr_val = (
            curr.market_value.amount
            if curr and curr.market_value
            else (curr.quantity * price_ent.price if curr else Decimal("0"))
        )

        delta = target_instr_val - curr_instr_val
        side = "BUY" if delta > 0 else "SELL"
        qty = int(abs(delta) // price_ent.price)
        quantity = Decimal(qty)

        if side == "SELL" and qty > 0:
            requested_qty = Decimal(qty)
            quantity = apply_tax_budget_sell_limit(
                position=curr,
                requested_qty=requested_qty,
                sell_price=price_ent.price,
                price_ccy=price_ent.currency,
                base_rate=rate,
            )
            if options.enable_tax_awareness and quantity < requested_qty:
                constraints = [c for c in diagnostics.warnings if c == "TAX_BUDGET_LIMIT_REACHED"]
                if not constraints:
                    diagnostics.warnings.append("TAX_BUDGET_LIMIT_REACHED")
                diagnostics.tax_budget_constraint_events.append(
                    TaxBudgetConstraintEvent(
                        instrument_id=i_id,
                        requested_quantity=requested_qty,
                        allowed_quantity=quantity,
                        reason_code="TAX_BUDGET_LIMIT_REACHED",
                    )
                )

        notional = quantity * price_ent.price
        notional_base = notional * rate

        shelf_ent = next((s for s in shelf if s.instrument_id == i_id), None)

        threshold = None
        if options.min_trade_notional:
            threshold = options.min_trade_notional
        elif shelf_ent and shelf_ent.min_notional:
            threshold = shelf_ent.min_notional

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
            applied_constraints = ["MIN_NOTIONAL"] if threshold else []
            if side == "SELL" and options.enable_tax_awareness:
                requested_qty = Decimal(qty)
                if quantity < requested_qty:
                    applied_constraints.append("TAX_BUDGET")
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
        normalized_budget_used = tax_budget_used_base
        if tax_budget_limit_base is not None:
            if abs(tax_budget_limit_base - normalized_budget_used) <= Decimal("0.0000000001"):
                normalized_budget_used = tax_budget_limit_base
        budget_limit = (
            Money(amount=tax_budget_limit_base, currency=portfolio.base_currency)
            if tax_budget_limit_base is not None
            else None
        )
        budget_used = (
            Money(
                amount=min(normalized_budget_used, tax_budget_limit_base),
                currency=portfolio.base_currency,
            )
            if tax_budget_limit_base is not None
            else None
        )
        tax_impact = TaxImpact(
            total_realized_gain=Money(
                amount=total_realized_gain_base,
                currency=portfolio.base_currency,
            ),
            total_realized_loss=Money(
                amount=total_realized_loss_base,
                currency=portfolio.base_currency,
            ),
            budget_limit=budget_limit,
            budget_used=budget_used,
        )

    return intents, tax_impact
