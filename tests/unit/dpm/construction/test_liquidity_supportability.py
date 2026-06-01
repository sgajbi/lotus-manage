from src.api.services.construction_liquidity_supportability import (
    derive_liquidity_context,
    liquidity_reason_codes,
    liquidity_status,
)
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
