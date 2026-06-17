from decimal import Decimal

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GroupConstraint,
    ModelPortfolio,
    ModelTarget,
    ShelfEntry,
)
from src.core.rebalance.targets import (
    _apply_group_constraint,
    _heuristic_target_control_status,
    _target_generation_status,
    _target_weight_posture,
)
from src.core.target_generation import (
    _apply_solver_values,
    _build_solver_problem,
    _build_solver_attempts,
    _collect_infeasibility_hints,
    _infeasibility_capacity_hints,
    _model_target_trace_row,
    _non_model_target_trace_row,
    _non_model_target_trace_tag,
    _solver_model_weight_array,
    _solver_group_members,
    _solver_invested_bounds,
    _solver_failure_reason,
    _solver_target_universe,
)


class _CpStub:
    OSQP = "OSQP"
    SCS = "SCS"


class _NpStub:
    @staticmethod
    def array(values):
        return list(values)


class _ExprStub:
    def __add__(self, _other):
        return self

    def __radd__(self, _other):
        return self

    def __sub__(self, _other):
        return self

    def __ge__(self, _other):
        return self

    def __le__(self, _other):
        return self


class _VariableStub(_ExprStub):
    value = [0.5]

    def __init__(self, size: int) -> None:
        self.size = size

    def __getitem__(self, _index):
        return _ExprStub()


class _ProblemRecorder:
    def __init__(self, objective, constraints) -> None:
        self.objective = objective
        self.constraints = constraints


class _CpProblemStub:
    @staticmethod
    def Variable(size: int) -> _VariableStub:
        return _VariableStub(size)

    @staticmethod
    def Minimize(expr):
        return ("minimize", expr)

    @staticmethod
    def sum_squares(_expr):
        return _ExprStub()

    @staticmethod
    def sum(_expr):
        return _ExprStub()

    Problem = _ProblemRecorder


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


def test_solver_target_universe_splits_tradeable_and_locked_weights() -> None:
    universe = _solver_target_universe(
        eligible_targets={
            "BUY_1": Decimal("0.25"),
            "LOCKED_1": Decimal("0.35"),
            "BUY_2": Decimal("0.15"),
            "LOCKED_2": Decimal("0.05"),
        },
        buy_list=["BUY_1", "BUY_2"],
    )

    assert universe.tradeable_ids == ["BUY_1", "BUY_2"]
    assert universe.locked_ids == ["LOCKED_1", "LOCKED_2"]
    assert universe.locked_weight == Decimal("0.40")


def test_solver_invested_bounds_subtract_locked_weight_from_cash_band() -> None:
    bounds = _solver_invested_bounds(
        locked_weight=Decimal("0.35"),
        options=EngineOptions(
            cash_band_min_weight=Decimal("0.05"),
            cash_band_max_weight=Decimal("0.15"),
        ),
    )

    assert bounds.minimum == Decimal("0.50")
    assert bounds.maximum == Decimal("0.60")


def test_solver_group_members_splits_tradeable_members_from_locked_weight() -> None:
    members = _solver_group_members(
        attr_key="sector",
        attr_val="TECH",
        eligible_targets={
            "TRADEABLE_1": Decimal("0.25"),
            "LOCKED_1": Decimal("0.35"),
            "TRADEABLE_2": Decimal("0.15"),
            "NON_MATCH": Decimal("0.05"),
            "MISSING_ATTRS": Decimal("0.20"),
        },
        shelf_attrs_by_id={
            "TRADEABLE_1": {"sector": "TECH"},
            "LOCKED_1": {"sector": "TECH"},
            "TRADEABLE_2": {"sector": "TECH"},
            "NON_MATCH": {"sector": "HEALTH"},
        },
        indexed_tradeable={"TRADEABLE_1": 0, "TRADEABLE_2": 1},
    )

    assert members.tradeable_ids == ["TRADEABLE_1", "TRADEABLE_2"]
    assert members.locked_weight == Decimal("0.35")


def test_solver_model_weight_array_projects_tradeable_model_weights() -> None:
    weights = _solver_model_weight_array(
        np=_NpStub,
        model=ModelPortfolio(
            targets=[
                ModelTarget(instrument_id="BUY_1", weight=Decimal("0.25")),
                ModelTarget(instrument_id="LOCKED", weight=Decimal("0.35")),
            ]
        ),
        tradeable_ids=["BUY_1", "BUY_2"],
    )

    assert weights == [0.25, 0.0]


def test_build_solver_problem_collects_cash_position_and_group_constraints() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    problem_spec = _build_solver_problem(
        cp=_CpProblemStub,
        np=_NpStub,
        model=ModelPortfolio(targets=[ModelTarget(instrument_id="BUY_1", weight=Decimal("0.25"))]),
        tradeable_ids=["BUY_1"],
        locked_weight=Decimal("0.20"),
        eligible_targets={"BUY_1": Decimal("0.25"), "LOCKED": Decimal("0.20")},
        shelf=[
            ShelfEntry(
                instrument_id="BUY_1",
                status="APPROVED",
                attributes={"sector": "TECH"},
            )
        ],
        options=EngineOptions(
            cash_band_min_weight=Decimal("0.05"),
            cash_band_max_weight=Decimal("0.15"),
            single_position_max_weight=Decimal("0.60"),
            group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.60"))},
        ),
        diagnostics=diagnostics,
    )

    assert isinstance(problem_spec.problem, _ProblemRecorder)
    assert problem_spec.weights.size == 1
    assert len(problem_spec.problem.constraints) == 5
    assert diagnostics.warnings == []


def test_apply_group_constraint_caps_and_redistributes_matching_group() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    eligible_targets = {"TECH": Decimal("0.60"), "FI": Decimal("0.40")}

    status = _apply_group_constraint(
        constraint_key="sector:TECH",
        max_weight=Decimal("0.20"),
        eligible_targets=eligible_targets,
        buy_set={"TECH", "FI"},
        shelf_attrs_by_id={"TECH": {"sector": "TECH"}, "FI": {"sector": "FI"}},
        known_attr_keys={"sector"},
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert eligible_targets["TECH"] == Decimal("0.20")
    assert eligible_targets["FI"] == Decimal("0.80")
    assert diagnostics.group_constraint_events[0].status == "CAPPED"


def test_apply_group_constraint_skips_unknown_or_within_limit_group() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    eligible_targets = {"TECH": Decimal("0.20001"), "FI": Decimal("0.79999")}

    status = _apply_group_constraint(
        constraint_key="sector:TECH",
        max_weight=Decimal("0.20"),
        eligible_targets=eligible_targets,
        buy_set={"TECH", "FI"},
        shelf_attrs_by_id={"TECH": {"sector": "TECH"}, "FI": {"sector": "FI"}},
        known_attr_keys={"sector"},
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert eligible_targets["TECH"] == Decimal("0.20001")
    assert diagnostics.warnings == []
    assert diagnostics.group_constraint_events == []


def test_apply_group_constraint_blocks_when_no_redistribution_recipient() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    eligible_targets = {"TECH": Decimal("0.60"), "LOCKED": Decimal("0.40")}

    status = _apply_group_constraint(
        constraint_key="sector:TECH",
        max_weight=Decimal("0.20"),
        eligible_targets=eligible_targets,
        buy_set={"TECH"},
        shelf_attrs_by_id={"TECH": {"sector": "TECH"}, "LOCKED": {"sector": "FI"}},
        known_attr_keys={"sector"},
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert "NO_ELIGIBLE_REDISTRIBUTION_DESTINATION" in diagnostics.warnings
    assert diagnostics.group_constraint_events[0].status == "BLOCKED"


def test_target_weight_posture_separates_tradeable_and_locked_capacity() -> None:
    posture = _target_weight_posture(
        eligible_targets={
            "BUY_1": Decimal("0.45"),
            "BUY_2": Decimal("0.25"),
            "LOCKED": Decimal("0.20"),
        },
        buy_set={"BUY_1", "BUY_2"},
    )

    assert posture.total_weight == Decimal("0.90")
    assert posture.locked_weight == Decimal("0.20")
    assert posture.tradeable_weight == Decimal("0.70")
    assert posture.available_tradeable_weight == Decimal("0.80")


def test_target_generation_status_preserves_worst_target_posture() -> None:
    assert _target_generation_status("READY", "PENDING_REVIEW") == "PENDING_REVIEW"
    assert _target_generation_status("PENDING_REVIEW", "READY") == "PENDING_REVIEW"
    assert _target_generation_status("READY", "BLOCKED") == "BLOCKED"
    assert _target_generation_status("BLOCKED", "READY") == "BLOCKED"


def test_heuristic_target_control_status_scales_overweight_tradeable_targets() -> None:
    eligible_targets = {
        "BUY_1": Decimal("0.80"),
        "BUY_2": Decimal("0.40"),
        "LOCKED": Decimal("0.20"),
    }

    status = _heuristic_target_control_status(
        eligible_targets=eligible_targets,
        buy_set={"BUY_1", "BUY_2"},
        options=EngineOptions(),
    )

    assert status == "PENDING_REVIEW"
    assert eligible_targets["LOCKED"] == Decimal("0.20")
    assert abs(eligible_targets["BUY_1"] - Decimal("0.5333333333333333333333333333")) < Decimal(
        "0.000000000000000000000000001"
    )
    assert abs(eligible_targets["BUY_2"] - Decimal("0.2666666666666666666666666667")) < Decimal(
        "0.000000000000000000000000001"
    )


def test_heuristic_target_control_status_preserves_pending_review_for_caps_and_cash_buffer() -> (
    None
):
    eligible_targets = {
        "BUY_1": Decimal("0.80"),
        "BUY_2": Decimal("0.15"),
        "LOCKED": Decimal("0.04"),
    }

    status = _heuristic_target_control_status(
        eligible_targets=eligible_targets,
        buy_set={"BUY_1", "BUY_2"},
        options=EngineOptions(
            single_position_max_weight=Decimal("0.50"),
            min_cash_buffer_pct=Decimal("0.10"),
        ),
    )

    assert status == "PENDING_REVIEW"
    assert eligible_targets["BUY_1"] <= Decimal("0.50")
    assert (
        sum(
            (
                weight
                for instrument_id, weight in eligible_targets.items()
                if instrument_id in {"BUY_1", "BUY_2"}
            ),
            Decimal("0.0"),
        )
        - Decimal("0.86")
    ) < Decimal("0.000000000000000000000000001")


def test_apply_solver_values_quantizes_and_fails_closed_without_values() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    eligible_targets = {"BUY_1": Decimal("0.0"), "BUY_2": Decimal("0.0")}

    assert _apply_solver_values(
        values=[0.123456, -0.01],
        tradeable_ids=["BUY_1", "BUY_2"],
        eligible_targets=eligible_targets,
        diagnostics=diagnostics,
    )
    assert eligible_targets == {"BUY_1": Decimal("0.1235"), "BUY_2": Decimal("0.0000")}
    assert diagnostics.warnings == []

    assert not _apply_solver_values(
        values=None,
        tradeable_ids=["BUY_1"],
        eligible_targets=eligible_targets,
        diagnostics=diagnostics,
    )
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_model_target_trace_row_marks_capped_and_redistributed_targets() -> None:
    capped = _model_target_trace_row(
        target=ModelTarget(instrument_id="EQ_CAPPED", weight=Decimal("0.30")),
        final_weight=Decimal("0.20"),
        total_val=Decimal("1000"),
        base_ccy="USD",
    )
    redistributed = _model_target_trace_row(
        target=ModelTarget(instrument_id="EQ_REDISTRIBUTED", weight=Decimal("0.20")),
        final_weight=Decimal("0.30"),
        total_val=Decimal("1000"),
        base_ccy="USD",
    )

    assert capped.final_value.amount == Decimal("200")
    assert capped.tags == ["CAPPED_BY_MAX_WEIGHT"]
    assert redistributed.final_value.amount == Decimal("300")
    assert redistributed.tags == ["REDISTRIBUTED_RECIPIENT"]


def test_non_model_target_trace_row_classifies_sell_to_zero_and_locked_positions() -> None:
    sell_to_zero = _non_model_target_trace_row(
        instrument_id="EQ_SELL",
        final_weight=Decimal("0"),
        buy_set=set(),
        total_val=Decimal("1000"),
        base_ccy="USD",
    )
    locked = _non_model_target_trace_row(
        instrument_id="EQ_LOCKED",
        final_weight=Decimal("0.15"),
        buy_set=set(),
        total_val=Decimal("1000"),
        base_ccy="USD",
    )

    assert sell_to_zero.tags == ["IMPLICIT_SELL_TO_ZERO"]
    assert sell_to_zero.final_value.amount == Decimal("0")
    assert locked.tags == ["LOCKED_POSITION"]
    assert locked.final_value.amount == Decimal("150.00")
    assert _non_model_target_trace_tag("EQ_BUY", Decimal("0.10"), {"EQ_BUY"}) == (
        "IMPLICIT_SELL_TO_ZERO"
    )


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


def test_infeasibility_capacity_hints_reports_cash_band_and_single_position_limits() -> None:
    assert _infeasibility_capacity_hints(
        tradeable_count=2,
        locked_weight=Decimal("0.20"),
        options=EngineOptions(
            cash_band_min_weight=Decimal("0.30"),
            cash_band_max_weight=Decimal("0.10"),
            single_position_max_weight=Decimal("0.10"),
        ),
    ) == [
        "INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION",
        "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY",
    ]

    assert (
        _infeasibility_capacity_hints(
            tradeable_count=3,
            locked_weight=Decimal("0.10"),
            options=EngineOptions(
                cash_band_min_weight=Decimal("0.05"),
                cash_band_max_weight=Decimal("0.20"),
                single_position_max_weight=Decimal("0.40"),
            ),
        )
        == []
    )
