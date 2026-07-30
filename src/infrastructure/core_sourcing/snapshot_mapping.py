from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Mapping

from src.core.models import CashBalance, Money, PortfolioSnapshot, Position
from src.infrastructure.core_sourcing.errors import DpmCoreResolverError


CORE_SNAPSHOT_INCOMPLETE = "DPM_CORE_PORTFOLIO_SNAPSHOT_INCOMPLETE"
CoreSnapshotIdentityNamespace = Literal["security_id", "instrument_id", "unknown"]


@dataclass(frozen=True)
class CoreSnapshotMappedRow:
    position: Position | None = None
    cash_currency: str | None = None
    cash_amount: Decimal | None = None


def core_snapshot_base_currency(payload: Mapping[str, Any]) -> str:
    valuation_context = _required_mapping(payload, "valuation_context")
    return _required_currency(
        valuation_context.get("portfolio_currency") or valuation_context.get("reporting_currency"),
        field="valuation_context.portfolio_currency",
    )


def core_snapshot_row_identity(row: Mapping[str, Any]) -> tuple[str, CoreSnapshotIdentityNamespace]:
    if row.get("security_id") is not None:
        return (
            _required_text(row.get("security_id"), field="positions_baseline[].security_id"),
            "security_id",
        )
    return (
        _required_text(row.get("instrument_id"), field="positions_baseline[].instrument_id"),
        "instrument_id",
    )


def core_snapshot_row_instrument_id(row: Mapping[str, Any]) -> str:
    instrument_id, _namespace = core_snapshot_row_identity(row)
    return instrument_id


def core_snapshot_row_quantity(row: Mapping[str, Any]) -> Decimal:
    return _required_decimal(row.get("quantity"), field="positions_baseline[].quantity")


def core_snapshot_row_currency(row: Mapping[str, Any], *, base_currency: str) -> str:
    return _required_currency(row.get("currency"), field="positions_baseline[].currency")


def core_snapshot_row_market_value(row: Mapping[str, Any]) -> Decimal | None:
    if row.get("market_value_local") is None:
        return None
    return _required_decimal(
        row.get("market_value_local"),
        field="positions_baseline[].market_value_local",
    )


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
    identity_namespace: CoreSnapshotIdentityNamespace = "unknown",
) -> CoreSnapshotMappedRow:
    position = Position(
        instrument_id=instrument_id,
        quantity=quantity,
        market_value=(
            Money(amount=market_value, currency=currency) if market_value is not None else None
        ),
    )
    position._core_source_identity_namespace = identity_namespace
    return CoreSnapshotMappedRow(position=position)


def held_instrument_ids(portfolio_snapshot: PortfolioSnapshot) -> list[str]:
    return [position.instrument_id for position in portfolio_snapshot.positions]


def map_core_snapshot_row(
    row: Mapping[str, Any],
    *,
    base_currency: str,
) -> CoreSnapshotMappedRow | None:
    instrument_id, identity_namespace = core_snapshot_row_identity(row)
    if not instrument_id:
        return None

    quantity = core_snapshot_row_quantity(row)
    currency = core_snapshot_row_currency(row, base_currency=base_currency)
    if core_snapshot_row_is_cash(instrument_id):
        return cash_core_snapshot_row(currency=currency, quantity=quantity)
    market_value = core_snapshot_row_market_value(row)
    if market_value is None:
        raise ValueError("positions_baseline[].market_value_local is required for positions")

    return position_core_snapshot_row(
        instrument_id=instrument_id,
        quantity=quantity,
        currency=currency,
        market_value=market_value,
        identity_namespace=identity_namespace,
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
    try:
        portfolio_id = _required_text(payload.get("portfolio_id"), field="portfolio_id")
        as_of_date = _required_business_date(payload.get("as_of_date"), field="as_of_date")
        sections = _required_mapping(payload, "sections")
        rows = _required_mapping_list(sections.get("positions_baseline"), "positions_baseline")
        _required_mapping(sections, "portfolio_totals")
        base_currency = core_snapshot_base_currency(payload)
        positions, cash_by_currency = portfolio_positions_and_cash_from_core_rows(
            rows,
            base_currency=base_currency,
        )

        return PortfolioSnapshot(
            snapshot_id=_optional_text(payload.get("snapshot_id"))
            or f"PortfolioStateSnapshot:{portfolio_id}:{as_of_date.isoformat()}",
            portfolio_id=portfolio_id,
            base_currency=base_currency,
            positions=positions,
            cash_balances=[
                CashBalance(currency=currency, amount=amount)
                for currency, amount in sorted(cash_by_currency.items())
            ],
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise DpmCoreResolverError(CORE_SNAPSHOT_INCOMPLETE) from exc


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _required_mapping_list(value: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if not all(isinstance(row, Mapping) for row in value):
        raise ValueError(f"{field} entries must be objects")
    return value


def _required_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must not be blank")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text fields must be strings when supplied")
    text = value.strip()
    return text or None


def _required_currency(value: Any, *, field: str) -> str:
    currency = _required_text(value, field=field).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError(f"{field} must be an ISO 4217 currency code")
    return currency


def _required_decimal(value: Any, *, field: str) -> Decimal:
    if value is None:
        raise ValueError(f"{field} is required")
    return Decimal(str(value))


def _required_business_date(value: Any, *, field: str) -> date:
    text = _required_text(value, field=field)
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError(f"{field} must use YYYY-MM-DD")
    return parsed


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
