from decimal import Decimal
from typing import Any, NamedTuple

from src.core.common.capabilities import has_solver_dependencies
from src.core.common.target_redistribution import redistribute_sell_only_excess
from src.core.models import DiagnosticsData, EngineOptions, Money, ShelfEntry, TargetInstrument

_SOLVER_STATUS_OPTIMAL = {"optimal", "optimal_inaccurate"}
_SOLVER_STATUS_INFEASIBLE = {"infeasible", "infeasible_inaccurate"}
_SOLVER_STATUS_UNBOUNDED = {"unbounded", "unbounded_inaccurate"}


class SolverTargetUniverse(NamedTuple):
    tradeable_ids: list[str]
    locked_ids: list[str]
    locked_weight: Decimal


class SolverInvestedBounds(NamedTuple):
    minimum: Decimal
    maximum: Decimal


class SolverGroupMembers(NamedTuple):
    tradeable_ids: list[str]
    locked_weight: Decimal


def _build_solver_attempts(cp: Any) -> tuple[tuple[Any, tuple[dict[str, Any], ...]], ...]:
    """
    Ordered solver attempts with bounded runtime and compatibility fallbacks.

    The first kwargs profile is preferred; subsequent profiles are compatibility
    fallbacks for environments where specific kwargs are unsupported.
    """
    return (
        (
            cp.OSQP,
            (
                {"max_iter": 2_000, "eps_abs": 1e-5, "eps_rel": 1e-5, "time_limit": 0.25},
                {"max_iter": 2_000, "eps_abs": 1e-5, "eps_rel": 1e-5},
                {"max_iter": 2_000},
                {},
            ),
        ),
        (
            cp.SCS,
            (
                {"max_iters": 5_000, "eps": 1e-4, "time_limit_secs": 0.5},
                {"max_iters": 5_000, "eps": 1e-4},
                {"max_iters": 5_000},
                {},
            ),
        ),
    )


def _solve_with_fallbacks(prob: Any, cp: Any) -> tuple[bool, str | None]:
    latest_status: str | None = None
    installed = _installed_solver_names(cp)

    for solver_name, kwargs_attempts in _build_solver_attempts(cp):
        if not _solver_is_available(solver_name=solver_name, installed=installed):
            continue

        for solve_kwargs in kwargs_attempts:
            attempt_status = _solve_attempt_status(
                prob=prob,
                cp=cp,
                solver_name=solver_name,
                solve_kwargs=solve_kwargs,
            )
            if attempt_status is None:
                continue

            latest_status = attempt_status
            if _solver_status_is_optimal(latest_status):
                return True, latest_status

    return False, latest_status


def _installed_solver_names(cp: Any) -> set[str]:
    try:
        return {str(solver_name) for solver_name in cp.installed_solvers()}
    except (AttributeError, TypeError, ValueError):
        return set()


def _solver_is_available(*, solver_name: Any, installed: set[str]) -> bool:
    return not installed or str(solver_name) in installed


def _solve_attempt_status(
    *,
    prob: Any,
    cp: Any,
    solver_name: Any,
    solve_kwargs: dict[str, Any],
) -> str | None:
    try:
        prob.solve(
            solver=solver_name,
            verbose=False,
            warm_start=False,
            **solve_kwargs,
        )
    except TypeError:
        # Binding rejected one or more kwargs; try compatibility profile.
        return None
    except (cp.SolverError, ValueError):
        # Runtime/configuration failure; still try compatibility profile.
        return None
    return str(prob.status).lower()


def _solver_status_is_optimal(status: str) -> bool:
    return status in _SOLVER_STATUS_OPTIMAL


def _solver_failure_reason(latest_status: str | None) -> str:
    if latest_status is None:
        return "SOLVER_ERROR"
    if latest_status in _SOLVER_STATUS_INFEASIBLE:
        return f"INFEASIBLE_{latest_status.upper()}"
    if latest_status in _SOLVER_STATUS_UNBOUNDED:
        return f"UNBOUNDED_{latest_status.upper()}"
    return f"SOLVER_NON_OPTIMAL_{latest_status.upper()}"


def _collect_infeasibility_hints(
    *,
    tradeable_ids: list[str],
    locked_weight: Decimal,
    options: EngineOptions,
    eligible_targets: dict[str, Decimal],
    shelf: list[ShelfEntry],
) -> list[str]:
    hints: list[str] = []
    shelf_attrs_by_id = {s.instrument_id: s.attributes for s in shelf}

    hints.extend(
        _infeasibility_capacity_hints(
            tradeable_count=len(tradeable_ids),
            locked_weight=locked_weight,
            options=options,
        )
    )

    indexed_tradeable = {i_id: idx for idx, i_id in enumerate(tradeable_ids)}
    for constraint_key in sorted(options.group_constraints.keys()):
        constraint = options.group_constraints[constraint_key]
        group_members = _solver_group_members(
            attr_key=constraint_key.split(":", 1)[0],
            attr_val=constraint_key.split(":", 1)[1],
            eligible_targets=eligible_targets,
            shelf_attrs_by_id=shelf_attrs_by_id,
            indexed_tradeable=indexed_tradeable,
        )
        if group_members.locked_weight > constraint.max_weight:
            hints.append(f"INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_{constraint_key}")
        if not group_members.tradeable_ids and group_members.locked_weight == Decimal("0"):
            continue

    return hints


def _infeasibility_capacity_hints(
    *,
    tradeable_count: int,
    locked_weight: Decimal,
    options: EngineOptions,
) -> list[str]:
    hints: list[str] = []
    invested_min = Decimal("1.0") - options.cash_band_max_weight - locked_weight
    invested_max = Decimal("1.0") - options.cash_band_min_weight - locked_weight
    if invested_min > invested_max:
        hints.append("INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION")

    if options.single_position_max_weight is not None:
        max_capacity = options.single_position_max_weight * Decimal(tradeable_count)
        if max_capacity < invested_min:
            hints.append("INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY")
    return hints


def _solver_target_universe(
    *,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
) -> SolverTargetUniverse:
    buy_set = set(buy_list)
    tradeable_ids = [i_id for i_id in eligible_targets if i_id in buy_set]
    locked_ids = [i_id for i_id in eligible_targets if i_id not in buy_set]
    locked_weight = sum((eligible_targets[i_id] for i_id in locked_ids), Decimal("0"))
    return SolverTargetUniverse(
        tradeable_ids=tradeable_ids,
        locked_ids=locked_ids,
        locked_weight=locked_weight,
    )


def _solver_invested_bounds(
    *,
    locked_weight: Decimal,
    options: EngineOptions,
) -> SolverInvestedBounds:
    return SolverInvestedBounds(
        minimum=Decimal("1.0") - options.cash_band_max_weight - locked_weight,
        maximum=Decimal("1.0") - options.cash_band_min_weight - locked_weight,
    )


def _solver_group_members(
    *,
    attr_key: str,
    attr_val: str,
    eligible_targets: dict[str, Decimal],
    shelf_attrs_by_id: dict[str, dict[str, str]],
    indexed_tradeable: dict[str, int],
) -> SolverGroupMembers:
    tradeable_ids: list[str] = []
    locked_weight = Decimal("0")
    for i_id in eligible_targets:
        attrs = shelf_attrs_by_id.get(i_id)
        if attrs is None or attrs.get(attr_key) != attr_val:
            continue
        if i_id in indexed_tradeable:
            tradeable_ids.append(i_id)
        else:
            locked_weight += eligible_targets[i_id]
    return SolverGroupMembers(
        tradeable_ids=tradeable_ids,
        locked_weight=locked_weight,
    )


def _solver_model_weight_array(
    *,
    np: Any,
    model: Any,
    tradeable_ids: list[str],
) -> Any:
    model_weights = {target.instrument_id: target.weight for target in model.targets}
    return np.array(
        [float(model_weights.get(instrument_id, Decimal("0.0"))) for instrument_id in tradeable_ids]
    )


def _append_solver_group_constraints(
    *,
    cp: Any,
    w: Any,
    constraints: list[Any],
    options: EngineOptions,
    eligible_targets: dict[str, Decimal],
    shelf: list[ShelfEntry],
    tradeable_ids: list[str],
    diagnostics: DiagnosticsData,
) -> None:
    shelf_attrs_by_id = {shelf_entry.instrument_id: shelf_entry.attributes for shelf_entry in shelf}
    known_attr_keys = {key for attrs in shelf_attrs_by_id.values() for key in attrs}
    indexed_tradeable = {instrument_id: idx for idx, instrument_id in enumerate(tradeable_ids)}

    for constraint_key in sorted(options.group_constraints.keys()):
        _append_solver_group_constraint(
            cp=cp,
            w=w,
            constraints=constraints,
            constraint_key=constraint_key,
            constraint=options.group_constraints[constraint_key],
            eligible_targets=eligible_targets,
            shelf_attrs_by_id=shelf_attrs_by_id,
            known_attr_keys=known_attr_keys,
            indexed_tradeable=indexed_tradeable,
            diagnostics=diagnostics,
        )


def _append_solver_group_constraint(
    *,
    cp: Any,
    w: Any,
    constraints: list[Any],
    constraint_key: str,
    constraint: Any,
    eligible_targets: dict[str, Decimal],
    shelf_attrs_by_id: dict[str, dict[str, str]],
    known_attr_keys: set[str],
    indexed_tradeable: dict[str, int],
    diagnostics: DiagnosticsData,
) -> None:
    attr_key, attr_val = constraint_key.split(":", 1)
    if attr_key not in known_attr_keys:
        diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
        return

    group_members = _solver_group_members(
        attr_key=attr_key,
        attr_val=attr_val,
        eligible_targets=eligible_targets,
        shelf_attrs_by_id=shelf_attrs_by_id,
        indexed_tradeable=indexed_tradeable,
    )
    if not group_members.tradeable_ids and group_members.locked_weight == Decimal("0"):
        return

    group_expr = cp.sum(
        [w[indexed_tradeable[instrument_id]] for instrument_id in group_members.tradeable_ids]
    ) + float(group_members.locked_weight)
    constraints.append(group_expr <= float(constraint.max_weight))


def _apply_solver_values(
    *,
    values: Any,
    tradeable_ids: list[str],
    eligible_targets: dict[str, Decimal],
    diagnostics: DiagnosticsData,
) -> bool:
    if values is None:
        diagnostics.warnings.append("SOLVER_ERROR")
        return False

    for idx, instrument_id in enumerate(tradeable_ids):
        raw_weight = Decimal(str(values[idx]))
        solved_weight = max(raw_weight, Decimal("0")).quantize(Decimal("0.0001"))
        eligible_targets[instrument_id] = solved_weight
    return True


def _load_solver_modules(diagnostics: DiagnosticsData) -> tuple[Any, Any] | None:
    if not has_solver_dependencies():
        diagnostics.warnings.append("SOLVER_ERROR")
        return None
    try:
        cp, np = _import_solver_modules()
    except ImportError:
        diagnostics.warnings.append("SOLVER_ERROR")
        return None
    return cp, np


def _import_solver_modules() -> tuple[Any, Any]:
    import cvxpy
    import numpy

    return cvxpy, numpy


def build_target_trace(
    model: Any,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    total_val: Decimal,
    base_ccy: str,
) -> list[TargetInstrument]:
    trace: list[TargetInstrument] = []
    buy_set = set(buy_list)
    model_target_ids = {t.instrument_id for t in model.targets}
    for t in model.targets:
        final_w = eligible_targets.get(t.instrument_id, Decimal("0.0"))
        tags = ["CAPPED_BY_MAX_WEIGHT"] if t.weight > final_w else []

        if final_w > t.weight:
            tags.append("REDISTRIBUTED_RECIPIENT")
        trace.append(
            TargetInstrument(
                instrument_id=t.instrument_id,
                model_weight=t.weight,
                final_weight=final_w,
                final_value=Money(amount=total_val * final_w, currency=base_ccy),
                tags=tags,
            )
        )

    for i_id, final_w in eligible_targets.items():
        if i_id not in model_target_ids:
            tag = (
                "IMPLICIT_SELL_TO_ZERO" if (i_id in buy_set or final_w == 0) else "LOCKED_POSITION"
            )
            trace.append(
                TargetInstrument(
                    instrument_id=i_id,
                    model_weight=Decimal("0.0"),
                    final_weight=final_w,
                    final_value=Money(amount=total_val * final_w, currency=base_ccy),
                    tags=[tag],
                )
            )

    return trace


def generate_targets_solver(
    model: Any,
    eligible_targets: dict[str, Decimal],
    buy_list: list[str],
    sell_only_excess: Decimal,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    total_val: Decimal,
    base_ccy: str,
    diagnostics: DiagnosticsData,
) -> tuple[list[TargetInstrument], str]:
    solver_modules = _load_solver_modules(diagnostics)
    if solver_modules is None:
        return [], "BLOCKED"
    cp, np = solver_modules

    status = redistribute_sell_only_excess(
        eligible_targets=eligible_targets,
        buy_set=set(buy_list),
        sell_only_excess=sell_only_excess,
    )

    universe = _solver_target_universe(
        eligible_targets=eligible_targets,
        buy_list=buy_list,
    )
    tradeable_ids = universe.tradeable_ids
    locked_weight = universe.locked_weight

    if not tradeable_ids:
        return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status

    w_model = _solver_model_weight_array(np=np, model=model, tradeable_ids=tradeable_ids)
    w = cp.Variable(len(tradeable_ids))

    objective = cp.Minimize(cp.sum_squares(w - w_model))
    constraints = [w >= 0]

    invested_bounds = _solver_invested_bounds(
        locked_weight=locked_weight,
        options=options,
    )
    constraints.append(cp.sum(w) >= float(invested_bounds.minimum))
    constraints.append(cp.sum(w) <= float(invested_bounds.maximum))

    if options.single_position_max_weight is not None:
        constraints.append(w <= float(options.single_position_max_weight))

    _append_solver_group_constraints(
        cp=cp,
        w=w,
        constraints=constraints,
        options=options,
        eligible_targets=eligible_targets,
        shelf=shelf,
        tradeable_ids=tradeable_ids,
        diagnostics=diagnostics,
    )

    prob = cp.Problem(objective, constraints)
    solved, latest_status = _solve_with_fallbacks(prob, cp)

    if not solved:
        reason = _solver_failure_reason(latest_status)
        diagnostics.warnings.append(reason)
        if reason.startswith("INFEASIBLE_"):
            diagnostics.warnings.extend(
                _collect_infeasibility_hints(
                    tradeable_ids=tradeable_ids,
                    locked_weight=locked_weight,
                    options=options,
                    eligible_targets=eligible_targets,
                    shelf=shelf,
                )
            )
        return [], "BLOCKED"

    if not _apply_solver_values(
        values=w.value,
        tradeable_ids=tradeable_ids,
        eligible_targets=eligible_targets,
        diagnostics=diagnostics,
    ):
        return [], "BLOCKED"
    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status
