from decimal import Decimal

from src.api.services.construction_liquidity_supportability import (
    _cashflow_projection_currency_mismatch,
    _cashflow_projection_is_usable,
    _cashflow_projection_usability_reason_codes,
    _post_trade_total_value_unavailable,
    cashflow_projection_status,
    derive_liquidity_context,
    liquidity_reason_codes,
    liquidity_status,
    post_trade_cash_weight,
    projected_cashflow_weight,
)
from src.api.services.construction_liquidity_source_context import source_liquidity_context
from src.core.construction.models import AuthoritativeLiquidityCashflowProjection
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
from tests.unit.dpm.construction.source_product_context_fixtures import (
    cashflow_projection_response,
)


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_liquidity_support_1",
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
        options=EngineOptions(),
        request_hash="hash-liquidity-support",
        correlation_id="corr-liquidity-support",
    )


def test_liquidity_supportability_uses_manage_settlement_policy_context() -> None:
    result = _trade_result()
    context = derive_liquidity_context(result=result)

    assert context.policy_id == "manage-liquidity-policy.v1"
    assert (
        liquidity_status(result=result, context=context) == ConstructionMethodStatus.PENDING_REVIEW
    )
    assert "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES" in liquidity_reason_codes(
        result=result,
        context=context,
    )


def test_cashflow_projection_status_degrades_when_projection_rows_are_excluded() -> None:
    result = _trade_result()
    source_context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response().model_copy(
            update={"include_projected": False}
        ),
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )

    assert source_context is not None
    assert (
        cashflow_projection_status(
            result=result,
            context=source_context,
            cash_weight=post_trade_cash_weight(result=result),
        )
        == ConstructionMethodStatus.DEGRADED
    )


def test_projected_cashflow_weight_uses_source_projection_over_post_trade_value() -> None:
    result = _trade_result()
    source_context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response(),
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )

    assert source_context is not None
    assert source_context.cashflow_projection is not None
    assert projected_cashflow_weight(result=result, context=source_context) == (
        source_context.cashflow_projection.total_net_cashflow.amount
        / result.after_simulated.total_value.amount
    )


def test_projected_cashflow_weight_absent_for_missing_projection() -> None:
    result = _trade_result()
    source_context = source_liquidity_context(
        cashflow_projection=None,
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )

    assert source_context is None
    assert (
        projected_cashflow_weight(
            result=result,
            context=derive_liquidity_context(result=result),
        )
        is None
    )


def test_cashflow_projection_usability_helpers_project_source_posture() -> None:
    ready_projection = _cashflow_projection()
    stale_projection = ready_projection.model_copy(
        update={
            "data_quality_status": ConstructionMethodStatus.DEGRADED,
            "include_projected": False,
        }
    )

    assert _cashflow_projection_usability_reason_codes(ready_projection) == []
    assert _cashflow_projection_is_usable(ready_projection)
    assert _cashflow_projection_usability_reason_codes(stale_projection) == [
        "CASHFLOW_PROJECTION_DEGRADED_BY_SOURCE",
        "CASHFLOW_PROJECTION_PROJECTED_ROWS_NOT_INCLUDED",
    ]
    assert not _cashflow_projection_is_usable(stale_projection)


def test_cashflow_projection_guard_helpers_detect_currency_and_value_edges() -> None:
    result = _trade_result()
    matching_projection = _cashflow_projection()
    mismatched_projection = matching_projection.model_copy(
        update={
            "total_net_cashflow": matching_projection.total_net_cashflow.model_copy(
                update={"currency": "SGD"}
            )
        }
    )
    zero_value_result = result.model_copy(
        update={
            "after_simulated": result.after_simulated.model_copy(
                update={
                    "total_value": result.after_simulated.total_value.model_copy(
                        update={"amount": Decimal("0")}
                    )
                }
            )
        }
    )

    assert not _cashflow_projection_currency_mismatch(
        result=result,
        projection=matching_projection,
    )
    assert _cashflow_projection_currency_mismatch(
        result=result,
        projection=mismatched_projection,
    )
    assert not _post_trade_total_value_unavailable(result=result)
    assert _post_trade_total_value_unavailable(result=zero_value_result)


def _cashflow_projection() -> AuthoritativeLiquidityCashflowProjection:
    context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response().model_copy(
            update={"data_quality_status": "READY"}
        ),
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )
    assert context is not None
    assert context.cashflow_projection is not None
    return context.cashflow_projection
