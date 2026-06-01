from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_currency_overlay_supportability import (
    currency_overlay_status,
    missing_currency_overlay_pairs,
)
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import EngineOptions
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _currency_overlay_request(
    *,
    fx_pairs: list[str],
    price_currency: str = "SGD",
) -> RebalanceRequest:
    return RebalanceRequest(
        portfolio_snapshot=portfolio_snapshot(
            portfolio_id="pf_fx_1",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "100")],
        ),
        market_data_snapshot=market_data_snapshot(
            prices=[price("SG_EQ", "100", price_currency)],
            fx_rates=[fx(pair, "1.25") for pair in fx_pairs],
        ),
        model_portfolio=model_portfolio(targets=[target("SG_EQ", "1.0")]),
        shelf_entries=[shelf_entry("SG_EQ", status="APPROVED", asset_class="EQUITY")],
        options=EngineOptions(),
    )


def _currency_overlay_context(
    *,
    status: ConstructionMethodStatus = ConstructionMethodStatus.READY,
    eligible_currencies: list[str] | None = None,
) -> AuthoritativeCurrencyOverlayContext:
    return AuthoritativeCurrencyOverlayContext(
        supportability_status=status,
        source_system="lotus-manage-fx-policy",
        policy_id="fx-policy",
        hedge_ratio_min=Decimal("0"),
        hedge_ratio_max=Decimal("1"),
        eligible_currencies=eligible_currencies or ["SGD"],
        reason_codes=["CURRENCY_OVERLAY_READY"],
    )


def test_currency_overlay_supportability_blocks_missing_required_fx_pair() -> None:
    request = _currency_overlay_request(fx_pairs=[])
    context = _currency_overlay_context()

    assert missing_currency_overlay_pairs(request=request) == ["SGD/USD"]
    assert (
        currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.BLOCKED
    )


def test_currency_overlay_supportability_degrades_without_source_context() -> None:
    request = _currency_overlay_request(fx_pairs=["SGD/USD"])

    assert (
        currency_overlay_status(request=request, context=None) == ConstructionMethodStatus.DEGRADED
    )


def test_currency_overlay_supportability_marks_unsupported_currency_pending_review() -> None:
    request = _currency_overlay_request(fx_pairs=["SGD/USD"])
    context = _currency_overlay_context(eligible_currencies=["EUR"])

    assert (
        currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )
