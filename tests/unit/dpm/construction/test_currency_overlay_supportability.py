from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_currency_overlay_supportability import (
    _currency_overlay_active_currency_status,
    _currency_overlay_has_unsupported_currency,
    _currency_overlay_missing_required_fx,
    available_fx_pairs,
    currency_overlay_status,
    derive_currency_overlay_context,
    missing_currency_overlay_pairs,
    non_base_market_price_currencies,
    non_base_position_currencies,
    required_currency_overlay_pairs,
)
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
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


def _non_base_trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_fx_positions",
            base_currency="USD",
            positions=[position("SG_EQ", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[price("SG_EQ", "100", "SGD")],
            fx_rates=[fx("SGD/USD", "1.25")],
        ),
        model=model_portfolio(targets=[target("SG_EQ", "1.0")]),
        shelf=[shelf_entry("SG_EQ", status="APPROVED", asset_class="EQUITY")],
        options=EngineOptions(),
        request_hash="hash-fx",
        correlation_id="corr-fx",
    )


def test_currency_overlay_pair_helpers_preserve_required_and_available_pairs() -> None:
    request = _currency_overlay_request(fx_pairs=["SGD/USD"])

    assert available_fx_pairs(request=request) == {"SGD/USD"}
    assert non_base_market_price_currencies(request=request) == {"SGD"}
    assert required_currency_overlay_pairs(request=request) == {"SGD/USD"}
    assert missing_currency_overlay_pairs(request=request) == []


def test_non_base_position_currencies_feed_derived_context() -> None:
    result = _non_base_trade_result()

    assert non_base_position_currencies(result=result) == {"SGD"}
    assert derive_currency_overlay_context(result=result).eligible_currencies == ["SGD"]


def test_currency_overlay_supportability_blocks_missing_required_fx_pair() -> None:
    request = _currency_overlay_request(fx_pairs=[])
    context = _currency_overlay_context()

    assert missing_currency_overlay_pairs(request=request) == ["SGD/USD"]
    assert (
        currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.BLOCKED
    )


def test_currency_overlay_status_helpers_project_decision_edges() -> None:
    missing_fx_request = _currency_overlay_request(fx_pairs=[])
    covered_fx_request = _currency_overlay_request(fx_pairs=["SGD/USD"])

    assert _currency_overlay_missing_required_fx(request=missing_fx_request)
    assert not _currency_overlay_missing_required_fx(request=covered_fx_request)
    assert _currency_overlay_has_unsupported_currency(
        instrument_currencies={"SGD", "EUR"},
        eligible_currencies=["SGD"],
    )
    assert not _currency_overlay_has_unsupported_currency(
        instrument_currencies={"SGD"},
        eligible_currencies=["SGD", "EUR"],
    )
    assert _currency_overlay_active_currency_status({"SGD"}) == ConstructionMethodStatus.READY
    assert _currency_overlay_active_currency_status(set()) == ConstructionMethodStatus.DEGRADED


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
