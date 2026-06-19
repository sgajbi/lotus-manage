from decimal import Decimal
import sys

import pytest

from src.core.models import DiagnosticsData, EngineOptions, ModelPortfolio, ModelTarget, ShelfEntry
from src.core.target_generation import (
    _available_solver_attempts,
    _installed_solver_names,
    _load_solver_modules,
    _record_solver_failure,
    _solve_attempt_status,
    _solve_with_fallbacks,
    _solver_is_available,
    _solver_status_is_optimal,
    build_target_trace,
    generate_targets_solver,
)


class _SolverError(Exception):
    pass


class _CpFallbackStub:
    OSQP = "OSQP"
    SCS = "SCS"
    SolverError = _SolverError

    @staticmethod
    def installed_solvers() -> list[str]:
        return ["SCS"]


class _ProblemStub:
    def __init__(self) -> None:
        self.status = "optimal"
        self.calls: list[tuple[str, dict]] = []

    def solve(self, *, solver: str, verbose: bool, warm_start: bool, **kwargs) -> None:
        _ = verbose
        _ = warm_start
        self.calls.append((solver, kwargs))
        if "time_limit_secs" in kwargs:
            raise TypeError("unsupported kwarg")


class _FakeExpr:
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


class _FakeVariable(_FakeExpr):
    def __init__(self, size: int) -> None:
        self.value = [0.8 for _ in range(size)]

    def __getitem__(self, _index):
        return _FakeExpr()


class _FakeProblem:
    def __init__(self, _objective, _constraints) -> None:
        self.status = "optimal"

    def solve(self, **_kwargs) -> None:
        self.status = "optimal"


class _FakeProblemInfeasible:
    def __init__(self, _objective, _constraints) -> None:
        self.status = "infeasible"

    def solve(self, **_kwargs) -> None:
        self.status = "infeasible"


class _FakeCp:
    OSQP = "OSQP"
    SCS = "SCS"
    SolverError = _SolverError

    @staticmethod
    def installed_solvers() -> list[str]:
        return ["OSQP", "SCS"]

    @staticmethod
    def Variable(size: int) -> _FakeVariable:
        return _FakeVariable(size)

    @staticmethod
    def Minimize(_expr):
        return _FakeExpr()

    @staticmethod
    def sum_squares(_expr):
        return _FakeExpr()

    @staticmethod
    def sum(_expr):
        return _FakeExpr()

    Problem = _FakeProblem


class _FakeVariableWithNoValue(_FakeVariable):
    def __init__(self, size: int) -> None:
        super().__init__(size)
        self.value = None


class _FakeCpInfeasible(_FakeCp):
    Problem = _FakeProblemInfeasible


class _FakeCpNoValue(_FakeCp):
    @staticmethod
    def Variable(size: int) -> _FakeVariableWithNoValue:
        return _FakeVariableWithNoValue(size)


class _FakeNp:
    @staticmethod
    def array(values):
        return list(values)


def _install_fake_solver_modules(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "cvxpy", _FakeCp)
    monkeypatch.setitem(sys.modules, "numpy", _FakeNp)


def _install_fake_solver_modules_with_cp(monkeypatch, cp_module) -> None:
    monkeypatch.setitem(sys.modules, "cvxpy", cp_module)
    monkeypatch.setitem(sys.modules, "numpy", _FakeNp)


def test_build_target_trace_marks_non_model_positions() -> None:
    targets = build_target_trace(
        model=ModelPortfolio(targets=[ModelTarget(instrument_id="MODEL", weight=Decimal("0.4"))]),
        eligible_targets={
            "MODEL": Decimal("0.4"),
            "SELL_TO_ZERO": Decimal("0"),
            "LOCKED": Decimal("0.2"),
        },
        buy_list=["SELL_TO_ZERO"],
        total_val=Decimal("100"),
        base_ccy="USD",
    )

    tags_by_id = {target.instrument_id: target.tags for target in targets}
    assert tags_by_id["SELL_TO_ZERO"] == ["IMPLICIT_SELL_TO_ZERO"]
    assert tags_by_id["LOCKED"] == ["LOCKED_POSITION"]


def test_solve_with_fallbacks_skips_uninstalled_solver_and_tries_compatibility_kwargs() -> None:
    problem = _ProblemStub()

    solved, latest_status = _solve_with_fallbacks(problem, _CpFallbackStub)

    assert solved is True
    assert latest_status == "optimal"
    assert [solver for solver, _ in problem.calls] == ["SCS", "SCS"]


def test_installed_solver_helper_returns_empty_set_when_discovery_is_unavailable() -> None:
    class _CpWithoutInstalledSolvers:
        pass

    assert _installed_solver_names(_CpFallbackStub) == {"SCS"}
    assert _installed_solver_names(_CpWithoutInstalledSolvers) == set()


def test_solver_availability_helper_treats_empty_installed_set_as_try_all() -> None:
    assert _solver_is_available(solver_name="OSQP", installed=set())
    assert _solver_is_available(solver_name="SCS", installed={"SCS"})
    assert _solver_is_available(solver_name="OSQP", installed={"SCS"}) is False


def test_available_solver_attempts_filter_installed_solver_profiles() -> None:
    attempts = _available_solver_attempts(cp=_CpFallbackStub, installed={"SCS"})

    assert [solver_name for solver_name, _kwargs_attempts in attempts] == ["SCS"]
    assert len(attempts[0][1]) == 4


def test_solve_attempt_status_handles_success_and_compatibility_failures() -> None:
    problem = _ProblemStub()

    rejected = _solve_attempt_status(
        prob=problem,
        cp=_CpFallbackStub,
        solver_name="SCS",
        solve_kwargs={"time_limit_secs": 0.5},
    )
    solved = _solve_attempt_status(
        prob=problem,
        cp=_CpFallbackStub,
        solver_name="SCS",
        solve_kwargs={},
    )

    assert rejected is None
    assert solved == "optimal"
    assert _solver_status_is_optimal(solved)


def test_load_solver_modules_records_error_when_dependencies_are_absent(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: False)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    assert _load_solver_modules(diagnostics) is None
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_load_solver_modules_records_error_when_import_fails(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    monkeypatch.setitem(sys.modules, "cvxpy", None)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    assert _load_solver_modules(diagnostics) is None
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_load_solver_modules_does_not_hide_non_import_failures(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)

    def broken_import() -> tuple[object, object]:
        raise RuntimeError("solver import side effect failed")

    monkeypatch.setattr("src.core.target_generation._import_solver_modules", broken_import)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    with pytest.raises(RuntimeError, match="solver import side effect failed"):
        _load_solver_modules(diagnostics)
    assert diagnostics.warnings == []


def test_record_solver_failure_adds_infeasibility_hints() -> None:
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    _record_solver_failure(
        latest_status="infeasible",
        tradeable_ids=["BUY_1", "BUY_2"],
        locked_weight=Decimal("0.4"),
        options=EngineOptions(
            cash_band_max_weight=Decimal("0.20"),
            single_position_max_weight=Decimal("0.10"),
            group_constraints={"sector:TECH": {"max_weight": Decimal("0.3")}},
        ),
        eligible_targets={
            "BUY_1": Decimal("0.3"),
            "BUY_2": Decimal("0.3"),
            "LOCKED_TECH": Decimal("0.4"),
        },
        shelf=[
            ShelfEntry(instrument_id="BUY_1", status="APPROVED", attributes={"sector": "FIN"}),
            ShelfEntry(instrument_id="BUY_2", status="APPROVED", attributes={"sector": "FIN"}),
            ShelfEntry(
                instrument_id="LOCKED_TECH",
                status="SELL_ONLY",
                attributes={"sector": "TECH"},
            ),
        ],
        diagnostics=diagnostics,
    )

    assert diagnostics.warnings == [
        "INFEASIBLE_INFEASIBLE",
        "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY",
        "INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_sector:TECH",
    ]


def test_generate_targets_solver_reports_pending_review_when_sell_excess_has_no_recipient(
    monkeypatch,
) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    _install_fake_solver_modules(monkeypatch)

    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    targets, status = generate_targets_solver(
        model=ModelPortfolio(targets=[ModelTarget(instrument_id="LOCKED", weight=Decimal("1.0"))]),
        eligible_targets={"LOCKED": Decimal("1.0")},
        buy_list=[],
        sell_only_excess=Decimal("0.1"),
        shelf=[],
        options=EngineOptions(),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "PENDING_REVIEW"
    assert targets[0].instrument_id == "LOCKED"


def test_generate_targets_solver_uses_fake_solver_and_group_constraints(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    _install_fake_solver_modules(monkeypatch)

    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    targets, status = generate_targets_solver(
        model=ModelPortfolio(
            targets=[
                ModelTarget(instrument_id="BUY", weight=Decimal("0.7")),
                ModelTarget(instrument_id="LOCKED", weight=Decimal("0.3")),
            ]
        ),
        eligible_targets={"BUY": Decimal("0.7"), "LOCKED": Decimal("0.3")},
        buy_list=["BUY"],
        sell_only_excess=Decimal("0.05"),
        shelf=[
            ShelfEntry(
                instrument_id="BUY",
                status="APPROVED",
                asset_class="EQUITY",
                attributes={"sector": "technology"},
            )
        ],
        options=EngineOptions(
            single_position_max_weight=Decimal("0.9"),
            group_constraints={"sector:technology": {"max_weight": Decimal("0.9")}},
        ),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert diagnostics.warnings == []
    assert any(
        target.instrument_id == "BUY" and target.final_weight == Decimal("0.8000")
        for target in targets
    )


def test_generate_targets_solver_blocks_when_dependencies_are_absent(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: False)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    targets, status = generate_targets_solver(
        model=ModelPortfolio(targets=[]),
        eligible_targets={},
        buy_list=[],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=EngineOptions(),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert targets == []
    assert status == "BLOCKED"
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_generate_targets_solver_blocks_when_solver_import_fails(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    monkeypatch.setitem(sys.modules, "cvxpy", None)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    targets, status = generate_targets_solver(
        model=ModelPortfolio(targets=[]),
        eligible_targets={},
        buy_list=[],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=EngineOptions(),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert targets == []
    assert status == "BLOCKED"
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_generate_targets_solver_reports_unknown_group_attribute(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    _install_fake_solver_modules(monkeypatch)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    targets, status = generate_targets_solver(
        model=ModelPortfolio(targets=[ModelTarget(instrument_id="BUY", weight=Decimal("0.8"))]),
        eligible_targets={"BUY": Decimal("0.8")},
        buy_list=["BUY"],
        sell_only_excess=Decimal("0"),
        shelf=[ShelfEntry(instrument_id="BUY", status="APPROVED", attributes={"sector": "TECH"})],
        options=EngineOptions(group_constraints={"region:APAC": {"max_weight": Decimal("0.5")}}),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert diagnostics.warnings == ["UNKNOWN_CONSTRAINT_ATTRIBUTE_region"]
    assert targets


def test_generate_targets_solver_blocks_with_infeasibility_hints(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    _install_fake_solver_modules_with_cp(monkeypatch, _FakeCpInfeasible)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    targets, status = generate_targets_solver(
        model=ModelPortfolio(
            targets=[
                ModelTarget(instrument_id="BUY_1", weight=Decimal("0.4")),
                ModelTarget(instrument_id="BUY_2", weight=Decimal("0.4")),
                ModelTarget(instrument_id="LOCKED_TECH", weight=Decimal("0.4")),
            ]
        ),
        eligible_targets={
            "BUY_1": Decimal("0.3"),
            "BUY_2": Decimal("0.3"),
            "LOCKED_TECH": Decimal("0.4"),
        },
        buy_list=["BUY_1", "BUY_2"],
        sell_only_excess=Decimal("0"),
        shelf=[
            ShelfEntry(instrument_id="BUY_1", status="APPROVED", attributes={"sector": "FIN"}),
            ShelfEntry(instrument_id="BUY_2", status="APPROVED", attributes={"sector": "FIN"}),
            ShelfEntry(
                instrument_id="LOCKED_TECH",
                status="SELL_ONLY",
                attributes={"sector": "TECH"},
            ),
        ],
        options=EngineOptions(
            cash_band_max_weight=Decimal("0.20"),
            single_position_max_weight=Decimal("0.10"),
            group_constraints={"sector:TECH": {"max_weight": Decimal("0.3")}},
        ),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert targets == []
    assert status == "BLOCKED"
    assert "INFEASIBLE_INFEASIBLE" in diagnostics.warnings
    assert "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY" in diagnostics.warnings
    assert "INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_sector:TECH" in diagnostics.warnings


def test_generate_targets_solver_blocks_when_solver_returns_no_values(monkeypatch) -> None:
    monkeypatch.setattr("src.core.target_generation.has_solver_dependencies", lambda: True)
    _install_fake_solver_modules_with_cp(monkeypatch, _FakeCpNoValue)
    diagnostics = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    targets, status = generate_targets_solver(
        model=ModelPortfolio(targets=[ModelTarget(instrument_id="BUY", weight=Decimal("0.8"))]),
        eligible_targets={"BUY": Decimal("0.8")},
        buy_list=["BUY"],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=EngineOptions(),
        total_val=Decimal("100"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert targets == []
    assert status == "BLOCKED"
    assert diagnostics.warnings == ["SOLVER_ERROR"]
