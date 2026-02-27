from decimal import Decimal

from src.core.models import EngineOptions, GroupConstraint, ShelfEntry
from src.core.target_generation import (
    _build_solver_attempts,
    _collect_infeasibility_hints,
    _solver_failure_reason,
)


class _CpStub:
    OSQP = "OSQP"
    SCS = "SCS"


def test_build_solver_attempts_order_and_profiles() -> None:
    attempts = _build_solver_attempts(_CpStub)
    assert [attempt[0] for attempt in attempts] == ["OSQP", "SCS"]
    assert attempts[0][1][0]["max_iter"] == 2_000
    assert attempts[1][1][0]["max_iters"] == 5_000


def test_solver_failure_reason_classification() -> None:
    assert _solver_failure_reason(None) == "SOLVER_ERROR"
    assert _solver_failure_reason("infeasible") == "INFEASIBLE_INFEASIBLE"
    assert _solver_failure_reason("unbounded_inaccurate") == "UNBOUNDED_UNBOUNDED_INACCURATE"
    assert _solver_failure_reason("optimal") == "SOLVER_NON_OPTIMAL_OPTIMAL"


def test_collect_infeasibility_hints_reports_capacity_and_group_lock() -> None:
    options = EngineOptions(
        cash_band_min_weight=Decimal("0.10"),
        cash_band_max_weight=Decimal("0.20"),
        single_position_max_weight=Decimal("0.10"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.30"))},
    )
    eligible_targets = {
        "EQ_TECH_LOCKED": Decimal("0.40"),
        "EQ_NON_TECH": Decimal("0.10"),
        "EQ_BUY_1": Decimal("0.25"),
        "EQ_BUY_2": Decimal("0.25"),
    }
    shelf = [
        ShelfEntry(
            instrument_id="EQ_TECH_LOCKED",
            status="SELL_ONLY",
            attributes={"sector": "TECH"},
        ),
        ShelfEntry(
            instrument_id="EQ_NON_TECH",
            status="APPROVED",
            attributes={"sector": "FIN"},
        ),
        ShelfEntry(
            instrument_id="EQ_BUY_1",
            status="APPROVED",
            attributes={"sector": "FIN"},
        ),
        ShelfEntry(
            instrument_id="EQ_BUY_2",
            status="APPROVED",
            attributes={"sector": "FIN"},
        ),
    ]

    hints = _collect_infeasibility_hints(
        tradeable_ids=["EQ_BUY_1", "EQ_BUY_2"],
        locked_weight=Decimal("0.50"),
        options=options,
        eligible_targets=eligible_targets,
        shelf=shelf,
    )

    assert "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY" in hints
    assert "INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_sector:TECH" in hints
