from decimal import Decimal

from src.core.construction import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionTraceTerm,
    build_alternative_set,
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def _ready_rebalance_result() -> RebalanceResult:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_construct_1",
        base_currency="USD",
        positions=[position("EQ_A", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "100", "USD"),
            price("EQ_B", "100", "USD"),
        ]
    )
    model = model_portfolio(
        targets=[
            target("EQ_A", "0.50"),
            target("EQ_B", "0.50"),
        ]
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
    ]
    return run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(),
        request_hash="hash_construct_1",
        correlation_id="corr_construct_1",
    )


def test_do_nothing_baseline_has_no_trades_and_no_drift_reduction() -> None:
    result = _ready_rebalance_result()

    baseline = build_do_nothing_baseline(result=result)

    assert baseline.method == ConstructionMethod.DO_NOTHING_BASELINE
    assert baseline.method_status == ConstructionMethodStatus.READY
    assert baseline.intent_ids == []
    assert baseline.comparison_metrics.trade_count == 0
    assert baseline.comparison_metrics.turnover_weight == Decimal("0.0000")
    assert baseline.comparison_metrics.drift_before == Decimal("1.0000")
    assert baseline.comparison_metrics.drift_after == Decimal("1.0000")
    assert baseline.comparison_metrics.drift_reduction == Decimal("0.0000")


def test_rebalance_result_wraps_heuristic_as_comparable_alternative() -> None:
    result = _ready_rebalance_result()

    alternative = build_rebalance_result_alternative(result=result)

    assert alternative.method == ConstructionMethod.HEURISTIC_EXPLAINABLE
    assert alternative.method_status == ConstructionMethodStatus.READY
    assert alternative.rebalance_run_id == result.rebalance_run_id
    assert alternative.comparison_metrics.trade_count == 2
    assert alternative.comparison_metrics.turnover_weight == Decimal("1.0000")
    assert alternative.comparison_metrics.drift_after == Decimal("0.0000")
    assert alternative.comparison_metrics.drift_reduction == Decimal("1.0000")
    assert {term.term for term in alternative.objective_trace} == {
        ConstructionTraceTerm.DRIFT,
        ConstructionTraceTerm.TURNOVER,
    }


def test_alternative_set_rolls_up_conservative_status() -> None:
    result = _ready_rebalance_result()
    baseline = build_do_nothing_baseline(result=result)
    heuristic = build_rebalance_result_alternative(result=result)
    blocked = heuristic.model_copy(update={"method_status": ConstructionMethodStatus.BLOCKED})

    alternative_set = build_alternative_set(
        alternative_set_id="alts_pf_construct_1",
        portfolio_id="pf_construct_1",
        as_of="2026-04-10",
        alternatives=[baseline, heuristic, blocked],
    )

    assert alternative_set.status == ConstructionMethodStatus.BLOCKED
    assert [alternative.method for alternative in alternative_set.alternatives] == [
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
    ]
