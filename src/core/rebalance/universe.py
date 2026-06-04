from decimal import Decimal

from src.core.models import (
    EngineOptions,
    ExcludedInstrument,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    ShelfEntry,
    SimulatedState,
)


def _shelf_by_instrument(shelf: list[ShelfEntry]) -> dict[str, ShelfEntry]:
    return {entry.instrument_id: entry for entry in shelf}


def _model_target_exclusion_reason(
    *,
    shelf_entry: ShelfEntry,
    options: EngineOptions,
) -> str | None:
    if shelf_entry.status in ["BANNED", "SUSPENDED"]:
        return f"SHELF_STATUS_{shelf_entry.status}"
    if shelf_entry.status == "RESTRICTED" and not options.allow_restricted:
        return "SHELF_STATUS_RESTRICTED"
    return None


def _add_model_target_to_universe(
    *,
    target: ModelTarget,
    shelf_by_id: dict[str, ShelfEntry],
    options: EngineOptions,
    dq_log: dict[str, list[str]],
    eligible_targets: dict[str, Decimal],
    excluded: list[ExcludedInstrument],
    buy_list: list[str],
    sell_list: list[str],
) -> Decimal:
    shelf_entry = shelf_by_id.get(target.instrument_id)
    if shelf_entry is None:
        dq_log["shelf_missing"].append(target.instrument_id)
        return Decimal("0.0")

    exclusion_reason = _model_target_exclusion_reason(shelf_entry=shelf_entry, options=options)
    if exclusion_reason is not None:
        excluded.append(
            ExcludedInstrument(
                instrument_id=target.instrument_id,
                reason_code=exclusion_reason,
            )
        )
        return Decimal("0.0")

    if shelf_entry.status == "SELL_ONLY":
        eligible_targets[target.instrument_id] = Decimal("0.0")
        sell_list.append(target.instrument_id)
        excluded.append(
            ExcludedInstrument(
                instrument_id=target.instrument_id,
                reason_code="SHELF_STATUS_SELL_ONLY",
            )
        )
        return target.weight

    eligible_targets[target.instrument_id] = target.weight
    buy_list.append(target.instrument_id)
    sell_list.append(target.instrument_id)
    return Decimal("0.0")


def _current_position_weight(
    *,
    current_val: SimulatedState,
    instrument_id: str,
) -> Decimal | None:
    current_position = next(
        (position for position in current_val.positions if position.instrument_id == instrument_id),
        None,
    )
    return current_position.weight if current_position is not None else None


def _locked_position_reason(shelf_entry: ShelfEntry | None) -> str | None:
    if shelf_entry is None:
        return "LOCKED_DUE_TO_MISSING_SHELF"
    if shelf_entry.status in ["SUSPENDED", "BANNED", "RESTRICTED"]:
        return f"LOCKED_DUE_TO_{shelf_entry.status}"
    return None


def _add_portfolio_position_to_universe(
    *,
    position: Position,
    shelf_by_id: dict[str, ShelfEntry],
    current_val: SimulatedState,
    eligible_targets: dict[str, Decimal],
    excluded: list[ExcludedInstrument],
    sell_list: list[str],
) -> None:
    if position.quantity == 0 or position.instrument_id in eligible_targets:
        return

    shelf_entry = shelf_by_id.get(position.instrument_id)
    locked_reason = _locked_position_reason(shelf_entry)
    if locked_reason is not None:
        current_weight = _current_position_weight(
            current_val=current_val,
            instrument_id=position.instrument_id,
        )
        if current_weight is not None:
            eligible_targets[position.instrument_id] = current_weight
            excluded.append(
                ExcludedInstrument(
                    instrument_id=position.instrument_id,
                    reason_code=locked_reason,
                )
            )
        return

    eligible_targets[position.instrument_id] = Decimal("0.0")
    sell_list.append(position.instrument_id)


def build_universe(
    model: ModelPortfolio,
    portfolio: PortfolioSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    dq_log: dict[str, list[str]],
    current_val: SimulatedState,
) -> tuple[dict[str, Decimal], list[ExcludedInstrument], list[str], list[str], Decimal]:
    """Stage 2: Filter targets and handle implicit locking/sells."""
    eligible_targets: dict[str, Decimal] = {}
    excluded: list[ExcludedInstrument] = []
    buy_list: list[str] = []
    sell_list: list[str] = []
    sell_only_excess = Decimal("0.0")

    shelf_by_id = _shelf_by_instrument(shelf)
    for target in model.targets:
        sell_only_excess += _add_model_target_to_universe(
            target=target,
            shelf_by_id=shelf_by_id,
            options=options,
            dq_log=dq_log,
            eligible_targets=eligible_targets,
            excluded=excluded,
            buy_list=buy_list,
            sell_list=sell_list,
        )

    for pos in portfolio.positions:
        _add_portfolio_position_to_universe(
            position=pos,
            shelf_by_id=shelf_by_id,
            current_val=current_val,
            eligible_targets=eligible_targets,
            excluded=excluded,
            sell_list=sell_list,
        )

    return eligible_targets, excluded, buy_list, sell_list, sell_only_excess
