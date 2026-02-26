from decimal import Decimal
from typing import Any

from src.core.models import DiagnosticsData, EngineOptions, Money, ShelfEntry, TargetInstrument

_SOLVER_STATUS_OPTIMAL = {"optimal", "optimal_inaccurate"}
_SOLVER_STATUS_INFEASIBLE = {"infeasible", "infeasible_inaccurate"}
_SOLVER_STATUS_UNBOUNDED = {"unbounded", "unbounded_inaccurate"}


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
    installed: set[str] = set()
    try:
        installed = {str(s) for s in cp.installed_solvers()}
    except (AttributeError, TypeError, ValueError):
        installed = set()

    for solver_name, kwargs_attempts in _build_solver_attempts(cp):
        if installed and str(solver_name) not in installed:
            continue

        for solve_kwargs in kwargs_attempts:
            try:
                prob.solve(
                    solver=solver_name,
                    verbose=False,
                    warm_start=False,
                    **solve_kwargs,
                )
            except TypeError:
                # Binding rejected one or more kwargs; try compatibility profile.
                continue
            except (cp.SolverError, ValueError):
                # Runtime/configuration failure; still try compatibility profile.
                continue

            latest_status = str(prob.status).lower()
            if latest_status in _SOLVER_STATUS_OPTIMAL:
                return True, latest_status

    return False, latest_status


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

    invested_min = Decimal("1.0") - options.cash_band_max_weight - locked_weight
    invested_max = Decimal("1.0") - options.cash_band_min_weight - locked_weight
    if invested_min > invested_max:
        hints.append("INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION")

    if options.single_position_max_weight is not None:
        max_capacity = options.single_position_max_weight * Decimal(len(tradeable_ids))
        if max_capacity < invested_min:
            hints.append("INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY")

    indexed_tradeable = {i_id: idx for idx, i_id in enumerate(tradeable_ids)}
    for constraint_key in sorted(options.group_constraints.keys()):
        constraint = options.group_constraints[constraint_key]
        attr_key, attr_val = constraint_key.split(":", 1)
        group_locked_weight = Decimal("0")
        group_tradeable_count = 0
        for i_id in eligible_targets:
            attrs = shelf_attrs_by_id.get(i_id)
            if attrs is None or attrs.get(attr_key) != attr_val:
                continue
            if i_id in indexed_tradeable:
                group_tradeable_count += 1
            else:
                group_locked_weight += eligible_targets[i_id]

        if group_locked_weight > constraint.max_weight:
            hints.append(f"INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_{constraint_key}")
        if group_tradeable_count == 0 and group_locked_weight == Decimal("0"):
            continue

    return hints


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
    try:
        import cvxpy as cp
        import numpy as np
    except Exception:
        diagnostics.warnings.append("SOLVER_ERROR")
        return [], "BLOCKED"

    status = "READY"
    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in buy_list}
        total_rec = sum(recs.values())
        if total_rec > Decimal("0.0"):
            for i_id, rec_weight in recs.items():
                eligible_targets[i_id] = rec_weight + (sell_only_excess * (rec_weight / total_rec))
        else:
            status = "PENDING_REVIEW"

    tradeable_ids = [i_id for i_id in eligible_targets if i_id in buy_list]
    locked_ids = [i_id for i_id in eligible_targets if i_id not in buy_list]
    locked_weight = sum((eligible_targets[i_id] for i_id in locked_ids), Decimal("0"))
    shelf_attrs_by_id = {s.instrument_id: s.attributes for s in shelf}
    known_attr_keys = {k for attrs in shelf_attrs_by_id.values() for k in attrs}

    if not tradeable_ids:
        return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status

    model_weights = {t.instrument_id: t.weight for t in model.targets}
    w_model = np.array([float(model_weights.get(i_id, Decimal("0.0"))) for i_id in tradeable_ids])
    w = cp.Variable(len(tradeable_ids))

    objective = cp.Minimize(cp.sum_squares(w - w_model))
    constraints = [w >= 0]

    invested_min = Decimal("1.0") - options.cash_band_max_weight - locked_weight
    invested_max = Decimal("1.0") - options.cash_band_min_weight - locked_weight
    constraints.append(cp.sum(w) >= float(invested_min))
    constraints.append(cp.sum(w) <= float(invested_max))

    if options.single_position_max_weight is not None:
        constraints.append(w <= float(options.single_position_max_weight))

    indexed_tradeable = {i_id: idx for idx, i_id in enumerate(tradeable_ids)}
    sorted_keys = sorted(options.group_constraints.keys())
    for constraint_key in sorted_keys:
        constraint = options.group_constraints[constraint_key]
        attr_key, attr_val = constraint_key.split(":", 1)

        if attr_key not in known_attr_keys:
            diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
            continue

        group_tradeable = []
        group_locked_weight = Decimal("0")
        for i_id in eligible_targets:
            attrs = shelf_attrs_by_id.get(i_id)
            if attrs is None or attrs.get(attr_key) != attr_val:
                continue
            if i_id in indexed_tradeable:
                group_tradeable.append(i_id)
            else:
                group_locked_weight += eligible_targets[i_id]

        if not group_tradeable and group_locked_weight == Decimal("0"):
            continue

        group_expr = cp.sum([w[indexed_tradeable[i_id]] for i_id in group_tradeable]) + float(
            group_locked_weight
        )
        constraints.append(group_expr <= float(constraint.max_weight))

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

    for idx, i_id in enumerate(tradeable_ids):
        solved_weight = Decimal(str(max(float(w.value[idx]), 0.0))).quantize(Decimal("0.0001"))
        eligible_targets[i_id] = solved_weight

    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status
