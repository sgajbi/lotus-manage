from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    MarketDataSnapshot,
    Money,
    Position,
    TaxBudgetConstraintEvent,
    TaxImpact,
)
from src.core.valuation import get_fx_rate


TAX_LOT_EVIDENCE_INCOMPLETE_BUCKET = "tax_lot_evidence_incomplete"


@dataclass
class _TaxBudgetAccumulator:
    total_realized_gain_base: Decimal
    total_realized_loss_base: Decimal
    tax_budget_used_base: Decimal
    tax_budget_limit_base: Decimal | None


@dataclass(frozen=True)
class _TaxBudgetLotAllowance:
    requested_quantity: Decimal
    allowed_quantity: Decimal
    realized_base: Decimal


@dataclass(frozen=True)
class _SellQuantityDecision:
    quantity: Decimal
    sell_quantity_before_tax: Decimal | None


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


def _record_tax_lot_evidence_incomplete(
    *,
    instrument_id: str,
    reason_code: str,
    dq_log: dict[str, list[str]],
    diagnostics: DiagnosticsData,
) -> None:
    evidence_key = f"{instrument_id}:{reason_code}"
    bucket = dq_log.setdefault(TAX_LOT_EVIDENCE_INCOMPLETE_BUCKET, [])
    if evidence_key not in bucket:
        bucket.append(evidence_key)
    if reason_code not in diagnostics.warnings:
        diagnostics.warnings.append(reason_code)


def _tax_lot_quantity_covered(*, position: Position, requested_qty: Decimal) -> bool:
    lot_quantity = sum(
        (lot.quantity for lot in position.lots if lot.quantity > Decimal("0")),
        Decimal("0"),
    )
    return lot_quantity >= requested_qty


def _tax_lot_evidence_incomplete_for(
    *,
    instrument_id: str,
    dq_log: dict[str, list[str]],
) -> bool:
    prefix = f"{instrument_id}:"
    return any(
        evidence_key.startswith(prefix)
        for evidence_key in dq_log.get(TAX_LOT_EVIDENCE_INCOMPLETE_BUCKET, [])
    )


def _tax_budget_constraint_applies(
    *,
    side: Literal["BUY", "SELL"],
    quantity: Decimal,
    sell_quantity_before_tax: Decimal | None,
    tax_awareness_enabled: bool,
) -> bool:
    return (
        side == "SELL"
        and tax_awareness_enabled
        and sell_quantity_before_tax is not None
        and quantity < sell_quantity_before_tax
    )


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


def _tax_budget_sale_allowance(
    *,
    remaining_quantity: Decimal,
    lot_quantity: Decimal,
    lot_unit_cost: Decimal,
    sell_price: Decimal,
    base_rate: Decimal,
    tax_budget: _TaxBudgetAccumulator,
) -> _TaxBudgetLotAllowance | None:
    if remaining_quantity <= Decimal("0"):
        return None
    if lot_quantity <= Decimal("0"):
        return None
    return _tax_budget_lot_allowance(
        remaining_quantity=remaining_quantity,
        lot_quantity=lot_quantity,
        lot_unit_cost=lot_unit_cost,
        sell_price=sell_price,
        base_rate=base_rate,
        tax_budget=tax_budget,
    )


def _tax_budget_allowance_stops_lot_scan(
    *,
    allowance: _TaxBudgetLotAllowance | None,
    remaining_quantity: Decimal,
) -> bool:
    if allowance is None:
        return remaining_quantity <= Decimal("0")
    if allowance.allowed_quantity <= Decimal("0"):
        return True
    return allowance.allowed_quantity < allowance.requested_quantity


def _tax_budget_limited_quantity_from_lots(
    *,
    sorted_lots: list[tuple[Any, Decimal]],
    requested_qty: Decimal,
    sell_price: Decimal,
    base_rate: Decimal,
    tax_budget: _TaxBudgetAccumulator,
) -> Decimal:
    remaining = requested_qty
    allowed_qty = Decimal("0")
    for lot, lot_unit_cost in sorted_lots:
        allowance = _tax_budget_sale_allowance(
            remaining_quantity=remaining,
            lot_quantity=lot.quantity,
            lot_unit_cost=lot_unit_cost,
            sell_price=sell_price,
            base_rate=base_rate,
            tax_budget=tax_budget,
        )
        if allowance is None:
            if _tax_budget_allowance_stops_lot_scan(
                allowance=allowance,
                remaining_quantity=remaining,
            ):
                break
            continue

        _apply_tax_budget_lot_allowance(allowance=allowance, tax_budget=tax_budget)
        allowed_qty += allowance.allowed_quantity
        remaining -= allowance.allowed_quantity

        if _tax_budget_allowance_stops_lot_scan(
            allowance=allowance,
            remaining_quantity=remaining,
        ):
            break

    return allowed_qty


def _tax_budget_limited_sell_quantity(
    *,
    instrument_id: str,
    options: EngineOptions,
    position: Position | None,
    requested_qty: Decimal,
    sell_price: Decimal,
    price_ccy: str,
    base_rate: Decimal,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
    tax_budget: _TaxBudgetAccumulator,
    diagnostics: DiagnosticsData,
) -> Decimal:
    if not options.enable_tax_awareness:
        return requested_qty
    if position is None:
        _record_tax_lot_evidence_incomplete(
            instrument_id=instrument_id,
            reason_code="TAX_LOT_POSITION_MISSING",
            dq_log=dq_log,
            diagnostics=diagnostics,
        )
        return Decimal("0")
    if not position.lots:
        _record_tax_lot_evidence_incomplete(
            instrument_id=instrument_id,
            reason_code="TAX_LOTS_MISSING",
            dq_log=dq_log,
            diagnostics=diagnostics,
        )
        return Decimal("0")
    if not _tax_lot_quantity_covered(position=position, requested_qty=requested_qty):
        _record_tax_lot_evidence_incomplete(
            instrument_id=instrument_id,
            reason_code="TAX_LOTS_INCOMPLETE",
            dq_log=dq_log,
            diagnostics=diagnostics,
        )
        return Decimal("0")

    fx_missing_before = len(dq_log.get("fx_missing", []))
    sorted_lots = _hifo_sorted_lots(
        position=position,
        instrument_ccy=price_ccy,
        market_data=market_data,
        dq_log=dq_log,
    )
    if not sorted_lots:
        reason_code = (
            "TAX_LOT_COST_FX_MISSING"
            if len(dq_log.get("fx_missing", [])) > fx_missing_before
            else "TAX_LOTS_INCOMPLETE"
        )
        _record_tax_lot_evidence_incomplete(
            instrument_id=instrument_id,
            reason_code=reason_code,
            dq_log=dq_log,
            diagnostics=diagnostics,
        )
        return Decimal("0")

    return _tax_budget_limited_quantity_from_lots(
        sorted_lots=sorted_lots,
        requested_qty=requested_qty,
        sell_price=sell_price,
        base_rate=base_rate,
        tax_budget=tax_budget,
    )


def _sell_quantity_after_safety_limits(
    *,
    instrument_id: str,
    side: Literal["BUY", "SELL"],
    requested_quantity: Decimal,
    position: Position | None,
    options: EngineOptions,
    sell_price: Decimal,
    price_currency: str,
    base_rate: Decimal,
    market_data: MarketDataSnapshot,
    dq_log: dict[str, list[str]],
    tax_budget: _TaxBudgetAccumulator,
    diagnostics: DiagnosticsData,
) -> _SellQuantityDecision:
    if side != "SELL" or requested_quantity <= Decimal("0"):
        return _SellQuantityDecision(
            quantity=requested_quantity,
            sell_quantity_before_tax=None,
        )

    sell_quantity_before_tax = _clamped_sell_quantity(
        requested_qty=requested_quantity,
        position=position,
        diagnostics=diagnostics,
    )
    quantity = _tax_budget_limited_sell_quantity(
        instrument_id=instrument_id,
        options=options,
        position=position,
        requested_qty=sell_quantity_before_tax,
        sell_price=sell_price,
        price_ccy=price_currency,
        base_rate=base_rate,
        market_data=market_data,
        dq_log=dq_log,
        tax_budget=tax_budget,
        diagnostics=diagnostics,
    )
    if (
        options.enable_tax_awareness
        and quantity < sell_quantity_before_tax
        and not _tax_lot_evidence_incomplete_for(instrument_id=instrument_id, dq_log=dq_log)
    ):
        _record_tax_budget_limit_reached(
            instrument_id=instrument_id,
            requested_quantity=sell_quantity_before_tax,
            allowed_quantity=quantity,
            diagnostics=diagnostics,
        )
    return _SellQuantityDecision(
        quantity=quantity,
        sell_quantity_before_tax=sell_quantity_before_tax,
    )


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
