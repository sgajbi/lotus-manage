from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


def derive_currency_overlay_context(
    *,
    result: RebalanceResult,
) -> AuthoritativeCurrencyOverlayContext:
    non_base_currencies = sorted(non_base_position_currencies(result=result))
    return AuthoritativeCurrencyOverlayContext(
        supportability_status=(
            ConstructionMethodStatus.READY
            if non_base_currencies
            else ConstructionMethodStatus.DEGRADED
        ),
        source_system="lotus-manage-fx-policy",
        policy_id="manage-currency-overlay-policy.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("1.00"),
        eligible_currencies=non_base_currencies,
        reason_codes=["CURRENCY_OVERLAY_POLICY_DERIVED_FROM_MANAGE_FX_RULES"],
    )


def currency_overlay_status(
    *,
    request: RebalanceRequest,
    context: AuthoritativeCurrencyOverlayContext | None,
) -> ConstructionMethodStatus:
    if missing_currency_overlay_pairs(request=request):
        return ConstructionMethodStatus.BLOCKED
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if context.supportability_status != ConstructionMethodStatus.READY:
        return context.supportability_status
    instrument_currencies = non_base_market_price_currencies(request=request)
    if instrument_currencies - set(context.eligible_currencies):
        return ConstructionMethodStatus.PENDING_REVIEW
    return (
        ConstructionMethodStatus.READY
        if instrument_currencies
        else ConstructionMethodStatus.DEGRADED
    )


def missing_currency_overlay_pairs(*, request: RebalanceRequest) -> list[str]:
    return sorted(
        required_currency_overlay_pairs(request=request) - available_fx_pairs(request=request)
    )


def available_fx_pairs(*, request: RebalanceRequest) -> set[str]:
    return {fx_rate.pair for fx_rate in request.market_data_snapshot.fx_rates}


def required_currency_overlay_pairs(*, request: RebalanceRequest) -> set[str]:
    base_currency = request.portfolio_snapshot.base_currency
    non_base_currencies = non_base_market_price_currencies(request=request)
    return {
        f"{price.currency}/{base_currency}"
        for price in request.market_data_snapshot.prices
        if price.currency in non_base_currencies
    }


def non_base_market_price_currencies(*, request: RebalanceRequest) -> set[str]:
    base_currency = request.portfolio_snapshot.base_currency
    return {
        price.currency
        for price in request.market_data_snapshot.prices
        if price.currency != base_currency
    }


def non_base_position_currencies(*, result: RebalanceResult) -> set[str]:
    return {
        position.instrument_currency
        for position in result.after_simulated.positions
        if position.instrument_currency != result.after_simulated.total_value.currency
    }


__all__ = [
    "available_fx_pairs",
    "currency_overlay_status",
    "derive_currency_overlay_context",
    "missing_currency_overlay_pairs",
    "non_base_market_price_currencies",
    "non_base_position_currencies",
    "required_currency_overlay_pairs",
]
