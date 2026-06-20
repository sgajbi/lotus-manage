from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, TypeAlias, cast

from src.core.common.target_redistribution import redistribute_sell_only_excess
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

_GroupConstraintStatus: TypeAlias = Literal["READY", "BLOCKED"]
_TargetGenerationStatus: TypeAlias = Literal["READY", "BLOCKED", "PENDING_REVIEW"]


@dataclass(frozen=True)
class _TargetWeightPosture:
    total_weight: Decimal
    locked_weight: Decimal
    tradeable_weight: Decimal
    available_tradeable_weight: Decimal


def _build_shelf_attr_indexes(
    shelf: list[ShelfEntry],
) -> tuple[dict[str, dict[str, str]], set[str]]:
    shelf_attrs_by_id = {s.instrument_id: s.attributes for s in shelf}
    known_attr_keys = {k for attrs in shelf_attrs_by_id.values() for k in attrs}
    return shelf_attrs_by_id, known_attr_keys


def _constraint_key_parts(
    constraint_key: str,
    *,
    known_attr_keys: set[str],
    diagnostics: DiagnosticsData,
) -> tuple[str, str] | None:
    try:
        attr_key, attr_val = constraint_key.split(":", 1)
    except ValueError:
        diagnostics.warnings.append(f"INVALID_CONSTRAINT_KEY_{constraint_key}")
        return None

    if attr_key not in known_attr_keys:
        diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
        return None

    return attr_key, attr_val


def _group_constraint_members(
    *,
    eligible_targets: dict[str, Decimal],
    shelf_attrs_by_id: dict[str, dict[str, str]],
    attr_key: str,
    attr_val: str,
) -> list[str]:
    return [
        instrument_id
        for instrument_id in eligible_targets
        if shelf_attrs_by_id.get(instrument_id, {}).get(attr_key) == attr_val
    ]


def _cap_group_constraint_members(
    *,
    eligible_targets: dict[str, Decimal],
    group_members: list[str],
    max_weight: Decimal,
) -> tuple[Decimal, Decimal]:
    current_weight = sum((eligible_targets[i] for i in group_members), Decimal("0"))
    scale = max_weight / current_weight
    released_weight = current_weight - max_weight

    for instrument_id in group_members:
        eligible_targets[instrument_id] *= scale

    return current_weight, released_weight


def _redistribute_group_constraint_excess(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    group_members: list[str],
    released_weight: Decimal,
) -> dict[str, Decimal]:
    candidates = [
        instrument_id
        for instrument_id in eligible_targets
        if instrument_id in buy_set and instrument_id not in group_members
    ]
    total_candidate_weight = sum((eligible_targets[c] for c in candidates), Decimal("0"))
    if total_candidate_weight <= Decimal("0"):
        return {}

    recipients = {}
    for candidate in candidates:
        share = released_weight * (eligible_targets[candidate] / total_candidate_weight)
        eligible_targets[candidate] += share
        recipients[candidate] = share

    return recipients


def _record_group_constraint_event(
    *,
    diagnostics: DiagnosticsData,
    constraint_key: str,
    group_weight_before: Decimal,
    max_weight: Decimal,
    released_weight: Decimal,
    recipients: dict[str, Decimal],
) -> _GroupConstraintStatus:
    diagnostics.warnings.append(f"CAPPED_BY_GROUP_LIMIT_{constraint_key}")
    if recipients:
        diagnostics.group_constraint_events.append(
            GroupConstraintEvent(
                constraint_key=constraint_key,
                group_weight_before=group_weight_before,
                max_weight=max_weight,
                released_weight=released_weight,
                recipients=recipients,
                status="CAPPED",
            )
        )
        return "READY"

    diagnostics.warnings.append("NO_ELIGIBLE_REDISTRIBUTION_DESTINATION")
    diagnostics.group_constraint_events.append(
        GroupConstraintEvent(
            constraint_key=constraint_key,
            group_weight_before=group_weight_before,
            max_weight=max_weight,
            released_weight=released_weight,
            recipients={},
            status="BLOCKED",
        )
    )
    return "BLOCKED"


def apply_group_constraints(
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    shelf: list[ShelfEntry],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> _GroupConstraintStatus:
    """
    RFC-0008: Apply multi-dimensional group constraints.
    Caps overweight groups and redistributes excess to eligible buyable instruments.
    """
    if not options.group_constraints:
        return "READY"

    buy_set = set(buy_list)
    shelf_attrs_by_id, known_attr_keys = _build_shelf_attr_indexes(shelf)
    for constraint_key in sorted(options.group_constraints.keys()):
        status = _apply_group_constraint(
            constraint_key=constraint_key,
            max_weight=options.group_constraints[constraint_key].max_weight,
            eligible_targets=eligible_targets,
            buy_set=buy_set,
            shelf_attrs_by_id=shelf_attrs_by_id,
            known_attr_keys=known_attr_keys,
            diagnostics=diagnostics,
        )
        if status == "BLOCKED":
            return "BLOCKED"

    return "READY"


def _apply_group_constraint(
    *,
    constraint_key: str,
    max_weight: Decimal,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    shelf_attrs_by_id: dict[str, dict[str, str]],
    known_attr_keys: set[str],
    diagnostics: DiagnosticsData,
) -> _GroupConstraintStatus:
    constraint_parts = _constraint_key_parts(
        constraint_key,
        known_attr_keys=known_attr_keys,
        diagnostics=diagnostics,
    )
    if constraint_parts is None:
        return "READY"

    attr_key, attr_val = constraint_parts
    group_members = _group_constraint_members(
        eligible_targets=eligible_targets,
        shelf_attrs_by_id=shelf_attrs_by_id,
        attr_key=attr_key,
        attr_val=attr_val,
    )
    if not group_members:
        return "READY"

    current_w = sum((eligible_targets[i] for i in group_members), Decimal("0"))
    if current_w <= max_weight + Decimal("0.0001"):
        return "READY"

    current_w, excess = _cap_group_constraint_members(
        eligible_targets=eligible_targets,
        group_members=group_members,
        max_weight=max_weight,
    )
    recipients = _redistribute_group_constraint_excess(
        eligible_targets=eligible_targets,
        buy_set=buy_set,
        group_members=group_members,
        released_weight=excess,
    )
    return _record_group_constraint_event(
        diagnostics=diagnostics,
        constraint_key=constraint_key,
        group_weight_before=current_w,
        max_weight=max_weight,
        released_weight=excess,
        recipients=recipients,
    )


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


def _cap_tradeable_targets_to_available_weight(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
) -> _TargetGenerationStatus:
    posture = _target_weight_posture(eligible_targets=eligible_targets, buy_set=buy_set)
    if posture.total_weight <= Decimal("1.0001"):
        return "READY"

    status: _TargetGenerationStatus = (
        "PENDING_REVIEW" if posture.locked_weight > Decimal("1.0") else "READY"
    )
    _scale_tradeable_targets(
        eligible_targets=eligible_targets,
        buy_set=buy_set,
        tradeable_weight=posture.tradeable_weight,
        available_tradeable_weight=posture.available_tradeable_weight,
    )
    if posture.tradeable_weight > posture.available_tradeable_weight:
        return "PENDING_REVIEW"
    return status


def _target_weight_posture(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
) -> _TargetWeightPosture:
    total_weight = sum(eligible_targets.values(), Decimal("0.0"))
    locked_weight = sum(
        (
            weight
            for instrument_id, weight in eligible_targets.items()
            if instrument_id not in buy_set
        ),
        Decimal("0.0"),
    )
    tradeable_weight = total_weight - locked_weight
    return _TargetWeightPosture(
        total_weight=total_weight,
        locked_weight=locked_weight,
        tradeable_weight=tradeable_weight,
        available_tradeable_weight=max(Decimal("0.0"), Decimal("1.0") - locked_weight),
    )


def _scale_tradeable_targets(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    tradeable_weight: Decimal,
    available_tradeable_weight: Decimal,
) -> None:
    if tradeable_weight <= available_tradeable_weight or tradeable_weight <= Decimal("0.0"):
        return

    scale = available_tradeable_weight / tradeable_weight
    for instrument_id in eligible_targets:
        if instrument_id in buy_set:
            eligible_targets[instrument_id] *= scale


def _apply_single_position_max_weight(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    max_weight: Decimal,
) -> Literal["READY", "PENDING_REVIEW"]:
    excess = _cap_single_position_targets(
        eligible_targets=eligible_targets,
        max_weight=max_weight,
    )
    if excess <= Decimal("0.0"):
        return "READY"

    remainder = _redistribute_single_position_excess(
        eligible_targets=eligible_targets,
        buy_set=buy_set,
        max_weight=max_weight,
        excess=excess,
    )
    if remainder > Decimal("0.001"):
        return "PENDING_REVIEW"
    return "READY"


def _cap_single_position_targets(
    *,
    eligible_targets: dict[str, Decimal],
    max_weight: Decimal,
) -> Decimal:
    excess = sum(
        (max(Decimal("0.0"), weight - max_weight) for weight in eligible_targets.values()),
        Decimal("0.0"),
    )
    for instrument_id in eligible_targets:
        eligible_targets[instrument_id] = min(eligible_targets[instrument_id], max_weight)
    return excess


def _redistribute_single_position_excess(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    max_weight: Decimal,
    excess: Decimal,
) -> Decimal:
    candidates = {
        instrument_id: weight
        for instrument_id, weight in eligible_targets.items()
        if instrument_id in buy_set and weight < max_weight
    }
    total_candidate_weight = sum(candidates.values(), Decimal("0.0"))
    if total_candidate_weight <= Decimal("0.0"):
        return excess

    remainder = excess
    for instrument_id, weight in candidates.items():
        share = min(remainder * (weight / total_candidate_weight), max_weight - weight)
        eligible_targets[instrument_id] += share
        remainder -= share

    return remainder


def _apply_min_cash_buffer(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    min_cash_buffer_pct: Decimal,
) -> Literal["READY", "PENDING_REVIEW"]:
    if min_cash_buffer_pct <= Decimal("0.0"):
        return "READY"

    posture = _target_weight_posture(eligible_targets=eligible_targets, buy_set=buy_set)
    allowed_tradeable_weight = _cash_buffer_tradeable_weight_limit(
        posture=posture,
        min_cash_buffer_pct=min_cash_buffer_pct,
    )
    scaled = _scale_tradeable_targets_for_cash_buffer(
        eligible_targets=eligible_targets,
        buy_set=buy_set,
        tradeable_weight=posture.tradeable_weight,
        allowed_tradeable_weight=allowed_tradeable_weight,
    )
    if not scaled:
        return "READY"

    return "PENDING_REVIEW"


def _cash_buffer_tradeable_weight_limit(
    *,
    posture: _TargetWeightPosture,
    min_cash_buffer_pct: Decimal,
) -> Decimal:
    return max(
        Decimal("0.0"),
        posture.available_tradeable_weight - min_cash_buffer_pct,
    )


def _scale_tradeable_targets_for_cash_buffer(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    tradeable_weight: Decimal,
    allowed_tradeable_weight: Decimal,
) -> bool:
    if tradeable_weight <= allowed_tradeable_weight or tradeable_weight <= Decimal("0.0"):
        return False

    scale = allowed_tradeable_weight / tradeable_weight
    for instrument_id in eligible_targets:
        if instrument_id in buy_set:
            eligible_targets[instrument_id] *= scale
    return True


def _target_generation_status(
    current: _TargetGenerationStatus,
    candidate: _TargetGenerationStatus,
) -> _TargetGenerationStatus:
    if candidate == "BLOCKED" or current == "BLOCKED":
        return "BLOCKED"
    if candidate == "PENDING_REVIEW" or current == "PENDING_REVIEW":
        return "PENDING_REVIEW"
    return "READY"


def _heuristic_target_control_status(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    options: EngineOptions,
) -> _TargetGenerationStatus:
    status: _TargetGenerationStatus = _cap_tradeable_targets_to_available_weight(
        eligible_targets=eligible_targets,
        buy_set=buy_set,
    )

    if options.single_position_max_weight is not None:
        status = _target_generation_status(
            status,
            _apply_single_position_max_weight(
                eligible_targets=eligible_targets,
                buy_set=buy_set,
                max_weight=options.single_position_max_weight,
            ),
        )

    return _target_generation_status(
        status,
        _apply_min_cash_buffer(
            eligible_targets=eligible_targets,
            buy_set=buy_set,
            min_cash_buffer_pct=options.min_cash_buffer_pct,
        ),
    )


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
    buy_set = set(buy_list)

    status: _TargetGenerationStatus = cast(
        _TargetGenerationStatus,
        redistribute_sell_only_excess(
            eligible_targets=eligible_targets,
            buy_set=buy_set,
            sell_only_excess=sell_only_excess,
        ),
    )

    group_status = apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics)
    if group_status == "BLOCKED":
        return [], "BLOCKED"

    status = _target_generation_status(
        status,
        _heuristic_target_control_status(
            eligible_targets=eligible_targets,
            buy_set=buy_set,
            options=options,
        ),
    )

    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status
