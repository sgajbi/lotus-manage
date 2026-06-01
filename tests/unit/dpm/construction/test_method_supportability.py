from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_supportability import (
    currency_overlay_status,
    missing_currency_overlay_pairs,
    regime_stress_status,
)
from src.core.construction.models import (
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeRegimeStressContext,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import EngineOptions
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
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
