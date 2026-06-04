from decimal import Decimal

from src.api.services.construction_solver_supportability import (
    solver_method_status,
    solver_warning_codes,
    with_method_reason_codes,
)
from src.core.construction.models import ConstructionEnrichmentSummary
from src.core.construction.vocabulary import ConstructionMethodStatus
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


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_solver_support_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(max_turnover_pct=Decimal("1.00")),
        request_hash="hash-solver-support",
        correlation_id="corr-solver-support",
    )


def test_with_method_reason_codes_deduplicates_and_sorts_codes() -> None:
    enrichment = ConstructionEnrichmentSummary(
        tax_status=ConstructionMethodStatus.READY,
        turnover_status=ConstructionMethodStatus.READY,
        liquidity_status=ConstructionMethodStatus.READY,
        cost_status=ConstructionMethodStatus.DEGRADED,
        fx_status=ConstructionMethodStatus.READY,
        reason_codes=["SOLVER_AVAILABLE", "AUTHORITY_CONTEXT_READY"],
    )

    updated = with_method_reason_codes(
        enrichment=enrichment,
        reason_codes=["AUTHORITY_CONTEXT_READY", "SOLVER_NON_OPTIMAL_USER_LIMIT"],
    )

    assert updated.reason_codes == [
        "AUTHORITY_CONTEXT_READY",
        "SOLVER_AVAILABLE",
        "SOLVER_NON_OPTIMAL_USER_LIMIT",
    ]
    assert enrichment.reason_codes == ["SOLVER_AVAILABLE", "AUTHORITY_CONTEXT_READY"]


def test_solver_method_status_is_ready_without_solver_warnings() -> None:
    assert solver_method_status(result=_trade_result()) == ConstructionMethodStatus.READY


def test_solver_method_status_uses_lowest_solver_warning_posture() -> None:
    result = _trade_result().model_copy(deep=True)
    result.diagnostics.warnings.extend(
        [
            "NON_SOLVER_DIAGNOSTIC",
            "SOLVER_NON_OPTIMAL_USER_LIMIT",
            "INFEASIBLE_INFEASIBLE",
        ]
    )

    assert solver_method_status(result=result) == ConstructionMethodStatus.BLOCKED


def test_solver_warning_codes_filters_solver_diagnostics_only() -> None:
    result = _trade_result().model_copy(deep=True)
    result.diagnostics.warnings.extend(
        [
            "NON_SOLVER_DIAGNOSTIC",
            "SOLVER_NON_OPTIMAL_USER_LIMIT",
            "INFEASIBLE_INFEASIBLE",
            "UNBOUNDED_MODEL",
        ]
    )

    assert solver_warning_codes(result=result) == [
        "SOLVER_NON_OPTIMAL_USER_LIMIT",
        "INFEASIBLE_INFEASIBLE",
        "UNBOUNDED_MODEL",
    ]
