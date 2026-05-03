from decimal import Decimal

from src.core.models import DiagnosticsData, EngineOptions, ModelPortfolio, ModelTarget
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

    if diagnostics.warnings == ["SOLVER_ERROR"]:
        assert status == "BLOCKED"
        assert targets == []
    else:
        assert status == "PENDING_REVIEW"
        assert targets[0].instrument_id == "LOCKED"


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
