"""
FILE: tests/engine/test_engine_target_generation.py
"""

import subprocess
import sys
from decimal import Decimal
from importlib.util import find_spec

import pytest

from src.core.dpm_engine import _generate_targets
from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GroupConstraint,
    ModelTarget,
    ShelfEntry,
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


def test_target_gen_applies_group_cap_and_redistributes():
    """
    Scenario:
    - Tech_A: 30% (Sector: TECH)
    - Bond_B: 70% (Sector: FI)
    - Constraint: Sector:TECH <= 20%

    Result:
    - Tech_A scaled to 20%
    - 10% excess redistributed to Bond_B
    - Final: Tech_A=20%, Bond_B=80%
    """
    targets = [
        ModelTarget(instrument_id="Tech_A", weight=Decimal("0.3")),
        ModelTarget(instrument_id="Bond_B", weight=Decimal("0.7")),
    ]
    eligible = {"Tech_A": Decimal("0.3"), "Bond_B": Decimal("0.7")}
    buy_list = ["Tech_A", "Bond_B"]
    shelf = [
        ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="Bond_B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.2"))}
    )

    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    trace, status = _generate_targets(
        model=type("M", (), {"targets": targets})(),
        eligible_targets=eligible,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diag,
    )

    assert status == "READY"
    assert eligible["Tech_A"] == Decimal("0.2")
    assert eligible["Bond_B"] == Decimal("0.8")
    assert "CAPPED_BY_GROUP_LIMIT_sector:TECH" in diag.warnings


def test_target_gen_blocks_if_redistribution_impossible():
    """
    Scenario:
    - Tech_A: 30% (Sector: TECH)
    - Cash: 70% (Implicit, not in buy_list for this test setup)
    - Constraint: Sector:TECH <= 20%

    If there are no other BUYABLE assets to take the 10%, it should BLOCK.
    (Note: In real engine, if cash is not explicitly a target, it's just 'unallocated',
     but _generate_targets logic requires a destination in 'eligible' to accept weight).
    """
    targets = [ModelTarget(instrument_id="Tech_A", weight=Decimal("0.3"))]
    eligible = {"Tech_A": Decimal("0.3")}
    buy_list = ["Tech_A"]  # Only Tech_A is buyable
    shelf = [ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"})]

    options = EngineOptions(
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.2"))}
    )

    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    trace, status = _generate_targets(
        model=type("M", (), {"targets": targets})(),
        eligible_targets=eligible,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diag,
    )

    assert status == "BLOCKED"
    assert "NO_ELIGIBLE_REDISTRIBUTION_DESTINATION" in diag.warnings
    assert len(diag.group_constraint_events) == 1
    assert diag.group_constraint_events[0].status == "BLOCKED"


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_target_gen_feasible_allocates_with_hard_constraints():
    targets = [
        ModelTarget(instrument_id="Tech_A", weight=Decimal("1.0")),
        ModelTarget(instrument_id="Bond_B", weight=Decimal("0.0")),
    ]
    eligible = {"Tech_A": Decimal("1.0"), "Bond_B": Decimal("0.0")}
    buy_list = ["Tech_A", "Bond_B"]
    shelf = [
        ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="Bond_B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        single_position_max_weight=Decimal("0.4"),
        cash_band_min_weight=Decimal("0.5"),
        cash_band_max_weight=Decimal("0.5"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.3"))},
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    trace, status = _generate_targets(
        model=type("M", (), {"targets": targets})(),
        eligible_targets=eligible,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diag,
    )

    assert status == "READY"
    assert eligible["Tech_A"] == Decimal("0.3")
    assert eligible["Bond_B"] == Decimal("0.2")
    assert len(trace) == 2


@pytest.mark.skipif(not _CVXPY_RUNTIME_AVAILABLE, reason="cvxpy runtime unavailable")
def test_solver_target_gen_blocks_on_infeasible_constraints():
    targets = [ModelTarget(instrument_id="Tech_A", weight=Decimal("1.0"))]
    eligible = {"Tech_A": Decimal("1.0")}
    buy_list = ["Tech_A"]
    shelf = [ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"})]
    options = EngineOptions(
        target_method="SOLVER",
        single_position_max_weight=Decimal("0.4"),
        cash_band_min_weight=Decimal("0.5"),
        cash_band_max_weight=Decimal("0.5"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.3"))},
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    trace, status = _generate_targets(
        model=type("M", (), {"targets": targets})(),
        eligible_targets=eligible,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diag,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert any(w.startswith("INFEASIBLE_") for w in diag.warnings)
