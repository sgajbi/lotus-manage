from datetime import date

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_supportability import (
    derive_currency_overlay_context,
    derive_liquidity_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)


def authority_context_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    correlation_id: str | None,
    as_of_date: date,
) -> ConstructionAuthorityContext:
    risk_context = authority_context.risk_context
    if method == ConstructionMethod.RISK_AWARE and risk_context is None and risk_authority_client:
        try:
            risk_context = risk_authority_client.concentration_context(
                result=result,
                correlation_id=correlation_id,
            )
        except LotusRiskAuthorityUnavailableError:
            risk_context = None

    liquidity_context = authority_context.liquidity_context
    if method == ConstructionMethod.LIQUIDITY_AWARE and liquidity_context is None:
        liquidity_context = derive_liquidity_context(result=result)

    currency_context = authority_context.currency_overlay_context
    if method == ConstructionMethod.CURRENCY_OVERLAY and currency_context is None:
        currency_context = derive_currency_overlay_context(result=result)

    regime_context = authority_context.regime_stress_context
    if (
        method == ConstructionMethod.REGIME_STRESS_AWARE
        and regime_context is None
        and risk_authority_client
    ):
        try:
            regime_context = risk_authority_client.regime_scenario_context(
                result=result,
                portfolio_id=request.portfolio_snapshot.portfolio_id,
                as_of_date=as_of_date,
                correlation_id=correlation_id,
            )
        except LotusRiskAuthorityUnavailableError:
            regime_context = None

    return ConstructionAuthorityContext(
        risk_context=risk_context,
        performance_context=authority_context.performance_context,
        transaction_cost_context=authority_context.transaction_cost_context,
        liquidity_context=liquidity_context,
        currency_overlay_context=currency_context,
        execution_acknowledgement_context=authority_context.execution_acknowledgement_context,
        regime_stress_context=regime_context,
        client_restriction_context=authority_context.client_restriction_context,
        sustainability_preference_context=authority_context.sustainability_preference_context,
    )


__all__ = ["authority_context_for_method"]
