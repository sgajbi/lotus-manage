"""
FILE: src/core/valuation.py
"""

from decimal import Decimal
from typing import Dict, List, Optional

from src.core.models import (
    AllocationMetric,
    CashBalance,
    EngineOptions,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    PositionSummary,
    ShelfEntry,
    SimulatedState,
    ValuationMode,
)


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
    """
    Returns the FX rate to convert from_ccy -> to_ccy.
    Returns 1.0 if currencies match.
    Returns None if rate is missing.
    """
    if from_ccy == to_ccy:
        return Decimal("1.0")

    pair = f"{from_ccy}/{to_ccy}"
    direct = next((r.rate for r in market_data.fx_rates if r.pair == pair), None)
    if direct:
        return direct

    pair_inv = f"{to_ccy}/{from_ccy}"
    inverse = next((r.rate for r in market_data.fx_rates if r.pair == pair_inv), None)
    if inverse:
        return Decimal("1.0") / inverse

    return None


class ValuationService:
    """
    Central authority for valuing positions and cash based on the configured mode.
    """

    @staticmethod
    def value_position(
        position: Position,
        market_data: MarketDataSnapshot,
        base_ccy: str,
        options: EngineOptions,
        dq_log: Dict[str, List[str]],
    ) -> PositionSummary:
        """
        Calculates position value based on options.valuation_mode.
        """
        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == position.instrument_id), None
        )

        price_val = Decimal("0")
        currency = base_ccy

        if price_ent:
            price_val = price_ent.price
            currency = price_ent.currency

        mv_instr_ccy = Decimal("0")

        is_trust = options.valuation_mode == ValuationMode.TRUST_SNAPSHOT
        if is_trust and position.market_value:
            mv_instr_ccy = position.market_value.amount
            currency = position.market_value.currency
        else:
            mv_instr_ccy = position.quantity * price_val

        rate = get_fx_rate(market_data, currency, base_ccy)
        if rate is None:
            mv_base = Decimal("0")
        else:
            mv_base = mv_instr_ccy * rate

        return PositionSummary(
            instrument_id=position.instrument_id,
            quantity=position.quantity,
            instrument_currency=currency,
            price=Money(amount=price_val, currency=currency) if price_ent else None,
            value_in_instrument_ccy=Money(amount=mv_instr_ccy, currency=currency),
            value_in_base_ccy=Money(amount=mv_base, currency=base_ccy),
            weight=Decimal("0"),
        )


def _cash_value_in_base(
    *,
    cash: CashBalance,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    dq_log: Dict[str, List[str]] | None = None,
) -> Decimal:
    if cash.currency == base_ccy:
        return cash.amount

    rate = get_fx_rate(market_data, cash.currency, base_ccy)
    if rate:
        return cash.amount * rate

    if dq_log is not None:
        dq_log.setdefault("fx_missing", []).append(f"{cash.currency}/{base_ccy}")
    return Decimal("0")


def _valuation_options(options: Optional[EngineOptions]) -> EngineOptions:
    return options or EngineOptions()


def _valued_position_summaries(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    options: EngineOptions,
    dq_log: Dict[str, List[str]],
) -> tuple[list[PositionSummary], Decimal]:
    price_instruments = {price.instrument_id for price in market_data.prices}
    summaries: list[PositionSummary] = []
    total_value = Decimal("0")

    for position in portfolio.positions:
        if position.instrument_id not in price_instruments:
            dq_log.setdefault("price_missing", []).append(position.instrument_id)

        summary = ValuationService.value_position(
            position,
            market_data,
            portfolio.base_currency,
            options,
            dq_log,
        )
        _record_position_fx_gap(
            summary=summary,
            base_ccy=portfolio.base_currency,
            market_data=market_data,
            dq_log=dq_log,
        )
        summaries.append(summary)
        total_value += summary.value_in_base_ccy.amount

    return summaries, total_value


def _record_position_fx_gap(
    *,
    summary: PositionSummary,
    base_ccy: str,
    market_data: MarketDataSnapshot,
    dq_log: Dict[str, List[str]],
) -> None:
    if summary.instrument_currency == base_ccy:
        return
    if get_fx_rate(market_data, summary.instrument_currency, base_ccy) is None:
        dq_log.setdefault("fx_missing", []).append(f"{summary.instrument_currency}/{base_ccy}")


def _total_cash_value(
    *,
    cash_balances: list[CashBalance],
    market_data: MarketDataSnapshot,
    base_ccy: str,
    dq_log: Dict[str, List[str]] | None = None,
) -> Decimal:
    total = Decimal("0")
    for cash in cash_balances:
        total += _cash_value_in_base(
            cash=cash,
            market_data=market_data,
            base_ccy=base_ccy,
            dq_log=dq_log,
        )
    return total


def _safe_total_value(total_value: Decimal) -> Decimal:
    if total_value == 0:
        return Decimal("1")
    return total_value


def _allocation_metric(
    *, key: str, value: Decimal, total_value: Decimal, base_ccy: str
) -> AllocationMetric:
    return AllocationMetric(
        key=key,
        weight=value / total_value,
        value=Money(amount=value, currency=base_ccy),
    )


def _position_allocation_maps(
    *,
    position_summaries: list[PositionSummary],
    shelf: list[ShelfEntry],
) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]]]:
    shelf_by_instrument = {entry.instrument_id: entry for entry in shelf}
    allocation_by_asset_class: dict[str, Decimal] = {}
    allocation_by_attribute: dict[str, dict[str, Decimal]] = {}

    for position in position_summaries:
        value = position.value_in_base_ccy.amount
        shelf_entry = shelf_by_instrument.get(position.instrument_id)
        if shelf_entry is not None:
            position.asset_class = shelf_entry.asset_class
            _add_attribute_allocations(
                allocation_by_attribute=allocation_by_attribute,
                shelf_entry=shelf_entry,
                value=value,
            )
        allocation_by_asset_class[position.asset_class] = (
            allocation_by_asset_class.get(position.asset_class, Decimal("0")) + value
        )

    return allocation_by_asset_class, allocation_by_attribute


def _add_attribute_allocations(
    *,
    allocation_by_attribute: dict[str, dict[str, Decimal]],
    shelf_entry: ShelfEntry,
    value: Decimal,
) -> None:
    for attr_key, attr_val in shelf_entry.attributes.items():
        value_map = allocation_by_attribute.setdefault(attr_key, {})
        value_map[attr_val] = value_map.get(attr_val, Decimal("0")) + value


def _allocation_metrics(
    *,
    values_by_key: dict[str, Decimal],
    total_value: Decimal,
    base_ccy: str,
) -> list[AllocationMetric]:
    return [
        _allocation_metric(key=key, value=value, total_value=total_value, base_ccy=base_ccy)
        for key, value in values_by_key.items()
    ]


def _allocation_by_attribute_metrics(
    *,
    allocation_by_attribute: dict[str, dict[str, Decimal]],
    total_value: Decimal,
    base_ccy: str,
) -> dict[str, list[AllocationMetric]]:
    return {
        attr_key: _allocation_metrics(
            values_by_key=value_map,
            total_value=total_value,
            base_ccy=base_ccy,
        )
        for attr_key, value_map in allocation_by_attribute.items()
    }


def build_simulated_state(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    warnings: List[str],
    options: Optional[EngineOptions] = None,
) -> SimulatedState:
    """
    Constructs a full valuation of the portfolio.
    """
    options = _valuation_options(options)
    base_ccy = portfolio.base_currency
    pos_summaries, position_value = _valued_position_summaries(
        portfolio=portfolio,
        market_data=market_data,
        options=options,
        dq_log=dq_log,
    )
    cash_value = _total_cash_value(
        cash_balances=portfolio.cash_balances,
        market_data=market_data,
        base_ccy=base_ccy,
        dq_log=dq_log,
    )
    total_val = position_value + cash_value
    total_val_safe = _safe_total_value(total_val)

    for position in pos_summaries:
        position.weight = position.value_in_base_ccy.amount / total_val_safe

    alloc_class_map, alloc_attr_map = _position_allocation_maps(
        position_summaries=pos_summaries,
        shelf=shelf,
    )
    alloc_instr = [
        AllocationMetric(
            key=position.instrument_id, weight=position.weight, value=position.value_in_base_ccy
        )
        for position in pos_summaries
    ]
    alloc_class_map["CASH"] = alloc_class_map.get("CASH", Decimal("0")) + _total_cash_value(
        cash_balances=portfolio.cash_balances,
        market_data=market_data,
        base_ccy=base_ccy,
    )

    return SimulatedState(
        total_value=Money(amount=total_val, currency=base_ccy),
        cash_balances=portfolio.cash_balances,
        positions=pos_summaries,
        allocation_by_asset_class=_allocation_metrics(
            values_by_key=alloc_class_map,
            total_value=total_val_safe,
            base_ccy=base_ccy,
        ),
        allocation_by_instrument=alloc_instr,
        allocation=alloc_instr,
        allocation_by_attribute=_allocation_by_attribute_metrics(
            allocation_by_attribute=alloc_attr_map,
            total_value=total_val_safe,
            base_ccy=base_ccy,
        ),
    )
