from copy import deepcopy
from decimal import Decimal
from typing import Any, Literal, cast

from src.core.common.diagnostics import make_diagnostics_data
from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GroupConstraintEvent,
    ModelPortfolio,
    ShelfEntry,
    TargetMethod,
)
from src.core.target_generation import build_target_trace, generate_targets_solver


def _build_shelf_attr_indexes(
    shelf: list[ShelfEntry],
) -> tuple[dict[str, dict[str, str]], set[str]]:
    shelf_attrs_by_id = {s.instrument_id: s.attributes for s in shelf}
    known_attr_keys = {k for attrs in shelf_attrs_by_id.values() for k in attrs}
    return shelf_attrs_by_id, known_attr_keys


def apply_group_constraints(
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    shelf: list[ShelfEntry],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> Literal["READY", "BLOCKED"]:
    """
    RFC-0008: Apply multi-dimensional group constraints.
    Caps overweight groups and redistributes excess to eligible buyable instruments.
    """
    if not options.group_constraints:
        return "READY"

    buy_set = set(buy_list)
    shelf_attrs_by_id, known_attr_keys = _build_shelf_attr_indexes(shelf)
    sorted_keys = sorted(options.group_constraints.keys())

    for constraint_key in sorted_keys:
        constraint = options.group_constraints[constraint_key]

        try:
            attr_key, attr_val = constraint_key.split(":", 1)
        except ValueError:
            diagnostics.warnings.append(f"INVALID_CONSTRAINT_KEY_{constraint_key}")
            continue

        if attr_key not in known_attr_keys:
            diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
            continue

        group_members = []
        for i_id in eligible_targets:
            attrs = shelf_attrs_by_id.get(i_id)
            if attrs and attrs.get(attr_key) == attr_val:
                group_members.append(i_id)

        if not group_members:
            continue

        current_w = sum(eligible_targets[i] for i in group_members)
        if current_w <= constraint.max_weight + Decimal("0.0001"):
            continue

        scale = constraint.max_weight / current_w
        excess = current_w - constraint.max_weight

        for i_id in group_members:
            eligible_targets[i_id] *= scale

        candidates = [i for i in eligible_targets if i in buy_set and i not in group_members]
        total_cand_w = sum(eligible_targets[c] for c in candidates)

        if total_cand_w > Decimal("0"):
            recipients = {}
            for c in candidates:
                share = excess * (eligible_targets[c] / total_cand_w)
                eligible_targets[c] += share
                recipients[c] = share

            diagnostics.warnings.append(f"CAPPED_BY_GROUP_LIMIT_{constraint_key}")
            diagnostics.group_constraint_events.append(
                GroupConstraintEvent(
                    constraint_key=constraint_key,
                    group_weight_before=current_w,
                    max_weight=constraint.max_weight,
                    released_weight=excess,
                    recipients=recipients,
                    status="CAPPED",
                )
            )
        else:
            diagnostics.warnings.append(f"CAPPED_BY_GROUP_LIMIT_{constraint_key}")
            diagnostics.warnings.append("NO_ELIGIBLE_REDISTRIBUTION_DESTINATION")
            diagnostics.group_constraint_events.append(
                GroupConstraintEvent(
                    constraint_key=constraint_key,
                    group_weight_before=current_w,
                    max_weight=constraint.max_weight,
                    released_weight=excess,
                    recipients={},
                    status="BLOCKED",
                )
            )
            return "BLOCKED"

    return "READY"


def generate_targets(
    model: ModelPortfolio,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    sell_only_excess: Decimal,
    shelf: list[ShelfEntry] | None = None,
    options: EngineOptions | None = None,
    total_val: Decimal = Decimal("0"),
    base_ccy: str = "USD",
    diagnostics: DiagnosticsData | None = None,
) -> tuple[list[Any], str]:
    if shelf is None:
        shelf = []
    if options is None:
        options = EngineOptions()
    if diagnostics is None:
        diagnostics = make_diagnostics_data()

    if options.target_method == TargetMethod.SOLVER:
        return cast(
            tuple[list[Any], str],
            generate_targets_solver(
                model=model,
                eligible_targets=eligible_targets,
                buy_list=buy_list,
                sell_only_excess=sell_only_excess,
                shelf=shelf,
                options=options,
                total_val=total_val,
                base_ccy=base_ccy,
                diagnostics=diagnostics,
            ),
        )

    return generate_targets_heuristic(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=diagnostics,
    )


def _to_weight_map(trace: list[Any]) -> dict[str, Decimal]:
    return {t.instrument_id: t.final_weight for t in trace}


def compare_target_generation_methods(
    *,
    model: ModelPortfolio,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    sell_only_excess: Decimal,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    total_val: Decimal,
    base_ccy: str,
    primary_trace: list[Any],
    primary_status: str,
) -> dict[str, Any]:
    primary_method = options.target_method
    alternate_method = (
        TargetMethod.SOLVER if primary_method == TargetMethod.HEURISTIC else TargetMethod.HEURISTIC
    )

    alt_options = options.model_copy(update={"target_method": alternate_method})
    alt_diag = make_diagnostics_data()
    alt_trace, alt_status = generate_targets(
        model=model,
        eligible_targets=deepcopy(eligible_targets),
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=alt_options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=alt_diag,
    )

    primary_weights = _to_weight_map(primary_trace)
    alternate_weights = _to_weight_map(alt_trace)
    tolerance = options.compare_target_methods_tolerance
    differing_instruments = []
    for i_id in sorted(set(primary_weights.keys()) | set(alternate_weights.keys())):
        p = primary_weights.get(i_id, Decimal("0"))
        a = alternate_weights.get(i_id, Decimal("0"))
        if abs(p - a) > tolerance:
            differing_instruments.append(i_id)

    return {
        "primary_method": primary_method.value,
        "primary_status": primary_status,
        "alternate_method": alternate_method.value,
        "alternate_status": alt_status,
        "tolerance": str(tolerance),
        "differing_instruments": differing_instruments,
        "alternate_warnings": sorted(set(alt_diag.warnings)),
    }


def generate_targets_heuristic(
    model: ModelPortfolio,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    sell_only_excess: Decimal,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    total_val: Decimal,
    base_ccy: str,
    diagnostics: DiagnosticsData,
) -> tuple[list[Any], str]:
    status = "READY"
    buy_set = set(buy_list)

    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in buy_set}
        total_rec = sum(recs.values())
        if total_rec > Decimal("0.0"):
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))
        else:
            status = "PENDING_REVIEW"

    group_status = apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics)
    if group_status == "BLOCKED":
        return [], "BLOCKED"

    total_w = sum(eligible_targets.values())
    if total_w > Decimal("1.0001"):
        tradeable_keys = [k for k in eligible_targets if k in buy_set]
        locked_w = sum(v for k, v in eligible_targets.items() if k not in buy_set)
        available_space = max(Decimal("0.0"), Decimal("1.0") - locked_w)
        if locked_w > Decimal("1.0"):
            status = "PENDING_REVIEW"
        tradeable_w = sum(eligible_targets[k] for k in tradeable_keys)
        if tradeable_w > available_space:
            if tradeable_w > Decimal("0.0"):
                scale = available_space / tradeable_w
                for k in tradeable_keys:
                    eligible_targets[k] *= scale
            status = "PENDING_REVIEW"

    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess = sum(max(Decimal("0.0"), w - max_w) for w in eligible_targets.values())
        for i_id in eligible_targets:
            eligible_targets[i_id] = min(eligible_targets[i_id], max_w)
        if excess > Decimal("0.0"):
            cands = {k: v for k, v in eligible_targets.items() if k in buy_set and v < max_w}
            total_cand = sum(cands.values())
            if total_cand > Decimal("0.0"):
                rem = excess
                for i_id, w in cands.items():
                    share = min(rem * (w / total_cand), max_w - w)
                    eligible_targets[i_id] += share
                    rem -= share
                if rem > Decimal("0.001"):
                    status = "PENDING_REVIEW"
            else:
                status = "PENDING_REVIEW"

    if options.min_cash_buffer_pct > Decimal("0.0"):
        tw = sum(v for k, v in eligible_targets.items() if k in buy_set)
        lw = sum(v for k, v in eligible_targets.items() if k not in buy_set)
        allowed = max(Decimal("0.0"), Decimal("1.0") - options.min_cash_buffer_pct - lw)
        if tw > allowed:
            if tw > Decimal("0.0"):
                scale = allowed / tw
                for k in eligible_targets:
                    if k in buy_set:
                        eligible_targets[k] *= scale
            status = "PENDING_REVIEW"

    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status
