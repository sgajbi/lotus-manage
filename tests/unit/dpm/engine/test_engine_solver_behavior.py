import subprocess
import sys
from decimal import Decimal
from importlib.util import find_spec

import pytest

from src.core.dpm_engine import _generate_targets, run_simulation
from src.core.models import DiagnosticsData, EngineOptions, GroupConstraint, ShelfEntry
from src.core.target_generation import _solver_failure_reason
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    target,
)


def _cvxpy_runtime_available(timeout_seconds: float = 3.0) -> bool:
    if find_spec("cvxpy") is None:
        return False
    try:
        subprocess.run(
            [sys.executable, "-c", "import cvxpy"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


_CVXPY_RUNTIME_AVAILABLE = _cvxpy_runtime_available()


def _diag():
    return DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_counts_locked_group_weight_in_group_constraint():
    model = model_portfolio(targets=[target("TECH_BUY", "1.0"), target("BOND", "0.0")])
    eligible_targets = {
        "TECH_BUY": Decimal("0.20"),
        "TECH_LOCKED": Decimal("0.20"),
        "BOND": Decimal("0.60"),
    }
    buy_list = ["TECH_BUY", "BOND"]
    shelf = [
        ShelfEntry(instrument_id="TECH_BUY", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="TECH_LOCKED", status="SUSPENDED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="BOND", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.25"))},
    )

    trace, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert len(trace) == 3
    assert eligible_targets["TECH_BUY"] <= Decimal("0.0500")
    assert eligible_targets["TECH_LOCKED"] == Decimal("0.20")
    assert eligible_targets["BOND"] >= Decimal("0.7500")


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_warns_unknown_attribute_and_continues():
    model = model_portfolio(targets=[target("A", "0.6"), target("B", "0.4")])
    eligible_targets = {"A": Decimal("0.6"), "B": Decimal("0.4")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    diagnostics = _diag()
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"region:EMEA": GroupConstraint(max_weight=Decimal("0.10"))},
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert "UNKNOWN_CONSTRAINT_ATTRIBUTE_region" in diagnostics.warnings


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_handles_sell_only_excess_with_buy_recipients():
    model = model_portfolio(targets=[target("A", "0.7"), target("B", "0.3")])
    eligible_targets = {"A": Decimal("0.7"), "B": Decimal("0.3")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0.2"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert eligible_targets["A"] == Decimal("0.7000")
    assert eligible_targets["B"] == Decimal("0.3000")


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_skips_group_constraint_when_value_not_present():
    model = model_portfolio(targets=[target("A", "0.7"), target("B", "0.3")])
    eligible_targets = {"A": Decimal("0.7"), "B": Decimal("0.3")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    diagnostics = _diag()
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"sector:HEALTH": GroupConstraint(max_weight=Decimal("0.10"))},
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert diagnostics.warnings == []


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_falls_back_to_secondary_solver_when_primary_errors(monkeypatch):
    import cvxpy as cp

    model = model_portfolio(targets=[target("A", "0.5"), target("B", "0.5")])
    eligible_targets = {"A": Decimal("0.5"), "B": Decimal("0.5")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
    )

    original_solve = cp.Problem.solve
    attempted = []

    def solve_with_primary_failure(self, *args, **kwargs):
        solver = kwargs.get("solver")
        attempted.append(str(solver))
        if solver == cp.OSQP:
            raise cp.SolverError("forced primary solver failure")
        return original_solve(self, *args, **kwargs)

    monkeypatch.setattr(cp.Problem, "solve", solve_with_primary_failure)

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert str(cp.OSQP) in attempted
    assert str(cp.SCS) in attempted


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_retries_primary_solver_with_compatibility_kwargs(monkeypatch):
    import cvxpy as cp

    model = model_portfolio(targets=[target("A", "0.5"), target("B", "0.5")])
    eligible_targets = {"A": Decimal("0.5"), "B": Decimal("0.5")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
    )

    original_solve = cp.Problem.solve
    osqp_attempts = []

    def solve_rejecting_osqp_time_limit(self, *args, **kwargs):
        solver = kwargs.get("solver")
        if solver == cp.OSQP:
            osqp_attempts.append(dict(kwargs))
            if "time_limit" in kwargs:
                raise ValueError("time_limit unsupported in this binding")
        return original_solve(self, *args, **kwargs)

    monkeypatch.setattr(cp.Problem, "solve", solve_rejecting_osqp_time_limit)

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert any("time_limit" in attempt for attempt in osqp_attempts)
    assert any("time_limit" not in attempt for attempt in osqp_attempts)


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_run_simulation_solver_preserves_pending_review_when_no_recipients():
    pf = portfolio_snapshot(
        portfolio_id="pf_solver_pending",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    mkt = market_data_snapshot(prices=[price("SELL_ONLY_ASSET", "10", "USD")], fx_rates=[])
    model = model_portfolio(targets=[target("SELL_ONLY_ASSET", "1.0")])
    shelf = [ShelfEntry(instrument_id="SELL_ONLY_ASSET", status="SELL_ONLY")]
    options = EngineOptions(target_method="SOLVER")

    result = run_simulation(pf, mkt, model, shelf, options)

    assert result.status == "PENDING_REVIEW"
    assert result.intents == []


def test_solver_returns_blocked_when_solver_dependencies_unavailable(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_without_cvxpy(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cvxpy":
            raise ImportError("cvxpy unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_cvxpy)

    model = model_portfolio(targets=[target("A", "1.0")])
    diagnostics = _diag()
    trace, status = _generate_targets(
        model=model,
        eligible_targets={"A": Decimal("1.0")},
        buy_list=["A"],
        sell_only_excess=Decimal("0"),
        shelf=[ShelfEntry(instrument_id="A", status="APPROVED")],
        options=EngineOptions(target_method="SOLVER"),
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert "SOLVER_ERROR" in diagnostics.warnings


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_infeasible_emits_cash_band_and_capacity_hints():
    model = model_portfolio(targets=[target("A", "1.0")])
    diagnostics = _diag()
    trace, status = _generate_targets(
        model=model,
        eligible_targets={"A": Decimal("1.0")},
        buy_list=["A"],
        sell_only_excess=Decimal("0"),
        shelf=[ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"})],
        options=EngineOptions(
            target_method="SOLVER",
            cash_band_min_weight=Decimal("0.7"),
            cash_band_max_weight=Decimal("0.1"),
            single_position_max_weight=Decimal("0.2"),
        ),
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert any(w.startswith("INFEASIBLE_") for w in diagnostics.warnings)
    assert "INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION" in diagnostics.warnings
    assert "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY" in diagnostics.warnings


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_infeasible_emits_locked_group_hint():
    model = model_portfolio(targets=[target("TECH_BUY", "0.0"), target("BOND", "1.0")])
    diagnostics = _diag()
    trace, status = _generate_targets(
        model=model,
        eligible_targets={
            "TECH_BUY": Decimal("0.0"),
            "TECH_LOCKED": Decimal("0.4"),
            "BOND": Decimal("0.6"),
        },
        buy_list=["TECH_BUY", "BOND"],
        sell_only_excess=Decimal("0"),
        shelf=[
            ShelfEntry(instrument_id="TECH_BUY", status="APPROVED", attributes={"sector": "TECH"}),
            ShelfEntry(
                instrument_id="TECH_LOCKED", status="SUSPENDED", attributes={"sector": "TECH"}
            ),
            ShelfEntry(instrument_id="BOND", status="APPROVED", attributes={"sector": "FI"}),
        ],
        options=EngineOptions(
            target_method="SOLVER",
            cash_band_min_weight=Decimal("0"),
            cash_band_max_weight=Decimal("0"),
            group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.3"))},
        ),
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert any(w.startswith("INFEASIBLE_") for w in diagnostics.warnings)
    assert "INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_sector:TECH" in diagnostics.warnings


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_infeasible_skips_non_matching_group_hint():
    model = model_portfolio(targets=[target("A", "1.0")])
    diagnostics = _diag()
    trace, status = _generate_targets(
        model=model,
        eligible_targets={"A": Decimal("1.0")},
        buy_list=["A"],
        sell_only_excess=Decimal("0"),
        shelf=[ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"})],
        options=EngineOptions(
            target_method="SOLVER",
            cash_band_min_weight=Decimal("0.7"),
            cash_band_max_weight=Decimal("0.1"),
            group_constraints={"sector:HEALTH": GroupConstraint(max_weight=Decimal("0.2"))},
        ),
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert "INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION" in diagnostics.warnings
    assert not any(
        warning.startswith("INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_")
        for warning in diagnostics.warnings
    )


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_compare_target_methods_emits_divergence_warnings_and_payload():
    pf = portfolio_snapshot(
        portfolio_id="pf_solver_compare",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    mkt = market_data_snapshot(
        prices=[price("Tech_A", "100", "USD"), price("Bond_B", "100", "USD")], fx_rates=[]
    )
    model = model_portfolio(targets=[target("Tech_A", "1.0"), target("Bond_B", "0.0")])
    shelf = [
        ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="Bond_B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        compare_target_methods=True,
        cash_band_min_weight=Decimal("0.5"),
        cash_band_max_weight=Decimal("0.5"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.3"))},
    )

    result = run_simulation(pf, mkt, model, shelf, options)

    assert result.status == "READY"
    assert "TARGET_METHOD_STATUS_DIVERGENCE" in result.diagnostics.warnings
    assert "TARGET_METHOD_WEIGHT_DIVERGENCE" in result.diagnostics.warnings
    comparison = result.explanation["target_method_comparison"]
    assert comparison["primary_method"] == "SOLVER"
    assert comparison["alternate_method"] == "HEURISTIC"
    assert comparison["primary_status"] == "READY"
    assert comparison["alternate_status"] == "BLOCKED"
    assert comparison["differing_instruments"] != []


def test_solver_failure_reason_classification():
    assert _solver_failure_reason(None) == "SOLVER_ERROR"
    assert _solver_failure_reason("infeasible") == "INFEASIBLE_INFEASIBLE"
    assert _solver_failure_reason("infeasible_inaccurate") == "INFEASIBLE_INFEASIBLE_INACCURATE"
    assert _solver_failure_reason("unbounded") == "UNBOUNDED_UNBOUNDED"
    assert _solver_failure_reason("optimal") == "SOLVER_NON_OPTIMAL_OPTIMAL"
