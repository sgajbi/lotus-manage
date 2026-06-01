from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_supportability import (
    currency_overlay_status,
    derive_liquidity_context,
    liquidity_reason_codes,
    liquidity_status,
    missing_currency_overlay_pairs,
    regime_stress_status,
)
from src.core.construction.models import (
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeRegimeStressContext,
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
            portfolio_id="pf_method_support_1",
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
        request_hash="hash-method-support",
        correlation_id="corr-method-support",
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


def test_currency_overlay_supportability_blocks_missing_required_fx_pair() -> None:
    request = RebalanceRequest(
        portfolio_snapshot=portfolio_snapshot(
            portfolio_id="pf_fx_1",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "100")],
        ),
        market_data_snapshot=market_data_snapshot(
            prices=[price("SG_EQ", "100", "SGD")],
            fx_rates=[],
        ),
        model_portfolio=model_portfolio(targets=[target("SG_EQ", "1.0")]),
        shelf_entries=[shelf_entry("SG_EQ", status="APPROVED", asset_class="EQUITY")],
        options=EngineOptions(),
    )
    context = AuthoritativeCurrencyOverlayContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-fx-policy",
        policy_id="fx-policy",
        hedge_ratio_min=Decimal("0"),
        hedge_ratio_max=Decimal("1"),
        eligible_currencies=["SGD"],
        reason_codes=["CURRENCY_OVERLAY_READY"],
    )

    assert missing_currency_overlay_pairs(request=request) == ["SGD/USD"]
    assert (
        currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.BLOCKED
    )


def test_regime_stress_supportability_marks_threshold_breach_pending_review() -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-risk",
        scenario_pack_id="regime_pack_1",
        worst_case_loss_pct=Decimal("0.12"),
        maximum_allowed_loss_pct=Decimal("0.10"),
        reason_codes=["SCENARIO_PACK_READY"],
    )

    assert regime_stress_status(context) == ConstructionMethodStatus.PENDING_REVIEW
