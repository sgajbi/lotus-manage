from decimal import Decimal

from src.core.models import (
    EngineOptions,
    ExcludedInstrument,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
    SimulatedState,
)


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

    for target in model.targets:
        shelf_ent = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_ent:
            dq_log["shelf_missing"].append(target.instrument_id)
            continue
        if shelf_ent.status in ["BANNED", "SUSPENDED"]:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id,
                    reason_code=f"SHELF_STATUS_{shelf_ent.status}",
                )
            )
            continue
        if shelf_ent.status == "RESTRICTED" and not options.allow_restricted:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id, reason_code="SHELF_STATUS_RESTRICTED"
                )
            )
            continue
        if shelf_ent.status == "SELL_ONLY":
            sell_only_excess += target.weight
            eligible_targets[target.instrument_id] = Decimal("0.0")
            sell_list.append(target.instrument_id)
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id, reason_code="SHELF_STATUS_SELL_ONLY"
                )
            )
            continue
        eligible_targets[target.instrument_id] = target.weight
        buy_list.append(target.instrument_id)
        sell_list.append(target.instrument_id)

    for pos in portfolio.positions:
        if pos.quantity != 0 and pos.instrument_id not in eligible_targets:
            shelf_ent = next((s for s in shelf if s.instrument_id == pos.instrument_id), None)
            curr = next(
                (p for p in current_val.positions if p.instrument_id == pos.instrument_id), None
            )
            if not shelf_ent:
                if curr:
                    eligible_targets[pos.instrument_id] = curr.weight
                    excluded.append(
                        ExcludedInstrument(
                            instrument_id=pos.instrument_id,
                            reason_code="LOCKED_DUE_TO_MISSING_SHELF",
                        )
                    )
            elif shelf_ent.status in ["SUSPENDED", "BANNED", "RESTRICTED"]:
                if curr:
                    eligible_targets[pos.instrument_id] = curr.weight
                    excluded.append(
                        ExcludedInstrument(
                            instrument_id=pos.instrument_id,
                            reason_code=f"LOCKED_DUE_TO_{shelf_ent.status}",
                        )
                    )
            else:
                eligible_targets[pos.instrument_id] = Decimal("0.0")
                sell_list.append(pos.instrument_id)

    return eligible_targets, excluded, buy_list, sell_list, sell_only_excess
