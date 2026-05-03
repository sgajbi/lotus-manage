from decimal import Decimal
import sys

from src.core.models import DiagnosticsData, EngineOptions, ModelPortfolio, ModelTarget, ShelfEntry
from src.core.target_generation import _solve_with_fallbacks, generate_targets_solver


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


class _FakeNp:
    @staticmethod
    def array(values):
        return list(values)


def _install_fake_solver_modules(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "cvxpy", _FakeCp)
    monkeypatch.setitem(sys.modules, "numpy", _FakeNp)


def test_solve_with_fallbacks_skips_uninstalled_solver_and_tries_compatibility_kwargs() -> None:
    problem = _ProblemStub()

    solved, latest_status = _solve_with_fallbacks(problem, _CpFallbackStub)

    assert solved is True
    assert latest_status == "optimal"
    assert [solver for solver, _ in problem.calls] == ["SCS", "SCS"]


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
