from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


def derive_currency_overlay_context(
    *,
    result: RebalanceResult,
) -> AuthoritativeCurrencyOverlayContext:
    non_base_currencies = sorted(
        {
            position.instrument_currency
            for position in result.after_simulated.positions
            if position.instrument_currency != result.after_simulated.total_value.currency
        }
    )
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
    base_currency = request.portfolio_snapshot.base_currency
    instrument_currencies = {
        price.currency
        for price in request.market_data_snapshot.prices
        if price.currency != base_currency
    }
    if instrument_currencies - set(context.eligible_currencies):
        return ConstructionMethodStatus.PENDING_REVIEW
    return (
        ConstructionMethodStatus.READY
        if instrument_currencies
        else ConstructionMethodStatus.DEGRADED
    )


def missing_currency_overlay_pairs(*, request: RebalanceRequest) -> list[str]:
    base_currency = request.portfolio_snapshot.base_currency
    available_pairs = {fx_rate.pair for fx_rate in request.market_data_snapshot.fx_rates}
    required_pairs = {
        f"{price.currency}/{base_currency}"
        for price in request.market_data_snapshot.prices
        if price.currency != base_currency
    }
    return sorted(required_pairs - available_pairs)


__all__ = [
    "currency_overlay_status",
    "derive_currency_overlay_context",
    "missing_currency_overlay_pairs",
]
