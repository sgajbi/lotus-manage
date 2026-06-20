from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from src.core.models import CashBalance, Money, PortfolioSnapshot, Position


@dataclass(frozen=True)
class CoreSnapshotMappedRow:
    position: Position | None = None
    cash_currency: str | None = None
    cash_amount: Decimal | None = None


def core_snapshot_base_currency(payload: Mapping[str, Any]) -> str:
    valuation_context = payload.get("valuation_context") or {}
    return str(
        valuation_context.get("portfolio_currency")
        or valuation_context.get("reporting_currency")
        or "USD"
    )


def core_snapshot_row_instrument_id(row: Mapping[str, Any]) -> str:
    return str(row.get("security_id") or row.get("instrument_id") or "").strip()


def core_snapshot_row_quantity(row: Mapping[str, Any]) -> Decimal:
    return Decimal(str(row.get("quantity") or "0"))


def core_snapshot_row_currency(row: Mapping[str, Any], *, base_currency: str) -> str:
    return str(row.get("currency") or base_currency).upper()


def core_snapshot_row_market_value(row: Mapping[str, Any]) -> Decimal | None:
    market_value = row.get("market_value_local")
    if market_value is None:
        return None
    return Decimal(str(market_value))


def core_snapshot_row_is_cash(instrument_id: str) -> bool:
    return instrument_id.startswith("CASH_")


def cash_core_snapshot_row(
    *,
    currency: str,
    quantity: Decimal,
) -> CoreSnapshotMappedRow:
    return CoreSnapshotMappedRow(cash_currency=currency, cash_amount=quantity)


def position_core_snapshot_row(
    *,
    instrument_id: str,
    quantity: Decimal,
    currency: str,
    market_value: Decimal | None,
) -> CoreSnapshotMappedRow:
    return CoreSnapshotMappedRow(
        position=Position(
            instrument_id=instrument_id,
            quantity=quantity,
            market_value=(
                Money(amount=market_value, currency=currency) if market_value is not None else None
            ),
        )
    )


def held_instrument_ids(portfolio_snapshot: PortfolioSnapshot) -> list[str]:
    return [position.instrument_id for position in portfolio_snapshot.positions]


def map_core_snapshot_row(
    row: Mapping[str, Any],
    *,
    base_currency: str,
) -> CoreSnapshotMappedRow | None:
    instrument_id = core_snapshot_row_instrument_id(row)
    if not instrument_id:
        return None

    quantity = core_snapshot_row_quantity(row)
    currency = core_snapshot_row_currency(row, base_currency=base_currency)
    if core_snapshot_row_is_cash(instrument_id):
        return cash_core_snapshot_row(currency=currency, quantity=quantity)

    return position_core_snapshot_row(
        instrument_id=instrument_id,
        quantity=quantity,
        currency=currency,
        market_value=core_snapshot_row_market_value(row),
    )


def merge_core_snapshot_mapped_row(
    *,
    positions: list[Position],
    cash_by_currency: dict[str, Decimal],
    mapped_row: CoreSnapshotMappedRow,
) -> None:
    if mapped_row.position is not None:
        positions.append(mapped_row.position)
        return
    if mapped_row.cash_currency is not None and mapped_row.cash_amount is not None:
        cash_by_currency[mapped_row.cash_currency] = (
            cash_by_currency.get(mapped_row.cash_currency, Decimal("0")) + mapped_row.cash_amount
        )


def portfolio_positions_and_cash_from_core_rows(
    rows: list[Mapping[str, Any]],
    *,
    base_currency: str,
) -> tuple[list[Position], dict[str, Decimal]]:
    positions: list[Position] = []
    cash_by_currency: dict[str, Decimal] = {}
    for row in rows:
        mapped_row = map_core_snapshot_row(row, base_currency=base_currency)
        if mapped_row is None:
            continue
        merge_core_snapshot_mapped_row(
            positions=positions,
            cash_by_currency=cash_by_currency,
            mapped_row=mapped_row,
        )

    return positions, cash_by_currency


def portfolio_snapshot_from_core_snapshot(payload: dict[str, Any]) -> PortfolioSnapshot:
    sections = payload.get("sections") or {}
    rows = sections.get("positions_baseline") or []
    base_currency = core_snapshot_base_currency(payload)
    positions, cash_by_currency = portfolio_positions_and_cash_from_core_rows(
        rows,
        base_currency=base_currency,
    )

    return PortfolioSnapshot(
        snapshot_id=payload.get("snapshot_id")
        or f"PortfolioStateSnapshot:{payload.get('portfolio_id')}:{payload.get('as_of_date')}",
        portfolio_id=str(payload["portfolio_id"]),
        base_currency=base_currency,
        positions=positions,
        cash_balances=[
            CashBalance(currency=currency, amount=amount)
            for currency, amount in sorted(cash_by_currency.items())
        ],
    )


def required_currency_pairs(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    base_currency: str,
) -> list[tuple[str, str]]:
    base = base_currency.upper()
    return sorted(
        (currency, base)
        for currency in required_non_base_currencies(
            portfolio_snapshot=portfolio_snapshot,
            base_currency=base,
        )
    )


def position_market_value_currencies(
    positions: list[Position],
) -> set[str]:
    return {
        position.market_value.currency.upper()
        for position in positions
        if position.market_value is not None
    }


def cash_balance_currencies(cash_balances: list[CashBalance]) -> set[str]:
    return {cash.currency.upper() for cash in cash_balances}


def required_non_base_currencies(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    base_currency: str,
) -> set[str]:
    currencies = position_market_value_currencies(portfolio_snapshot.positions)
    currencies.update(cash_balance_currencies(portfolio_snapshot.cash_balances))
    return {currency for currency in currencies if currency != base_currency}
