from datetime import date

from src.api.request_models import RebalanceRequest
from src.api.services.construction_request_dates import construction_as_of_date
from src.api.services.authority_client_service import (
    RiskAuthorityClient,
    RiskAuthorityUnavailableError,
)
from src.api.services.construction_method_supportability import (
    derive_currency_overlay_context,
    derive_liquidity_context,
)
from src.core.construction.models import (
    AuthoritativeRegimeStressContext,
    AuthoritativeRiskContext,
    ConstructionAuthorityContext,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult


def risk_context_for_method(
    *,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    correlation_id: str | None,
) -> AuthoritativeRiskContext | None:
    if authority_context.risk_context is not None:
        return authority_context.risk_context
    if method != ConstructionMethod.RISK_AWARE or risk_authority_client is None:
        return None
    try:
        return risk_authority_client.concentration_context(
            result=result,
            correlation_id=correlation_id,
        )
    except RiskAuthorityUnavailableError:
        return None


def regime_context_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    correlation_id: str | None,
    as_of_date: date,
) -> AuthoritativeRegimeStressContext | None:
    if authority_context.regime_stress_context is not None:
        return authority_context.regime_stress_context
    if method != ConstructionMethod.REGIME_STRESS_AWARE or risk_authority_client is None:
        return None
    try:
        return risk_authority_client.regime_scenario_context(
            result=result,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
            as_of_date=as_of_date,
            correlation_id=correlation_id,
        )
    except RiskAuthorityUnavailableError:
        return None


def authority_context_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    correlation_id: str | None,
    as_of_date: date,
) -> ConstructionAuthorityContext:
    risk_context = risk_context_for_method(
        method=method,
        result=result,
        authority_context=authority_context,
        risk_authority_client=risk_authority_client,
        correlation_id=correlation_id,
    )

    liquidity_context = authority_context.liquidity_context
    if method == ConstructionMethod.LIQUIDITY_AWARE and liquidity_context is None:
        liquidity_context = derive_liquidity_context(result=result)

    currency_context = authority_context.currency_overlay_context
    if method == ConstructionMethod.CURRENCY_OVERLAY and currency_context is None:
        currency_context = derive_currency_overlay_context(result=result)

    regime_context = regime_context_for_method(
        request=request,
        method=method,
        result=result,
        authority_context=authority_context,
        risk_authority_client=risk_authority_client,
        correlation_id=correlation_id,
        as_of_date=as_of_date,
    )

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


def authority_context_for_request_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    correlation_id: str | None,
) -> ConstructionAuthorityContext:
    return authority_context_for_method(
        request=request,
        method=method,
        result=result,
        authority_context=authority_context,
        risk_authority_client=risk_authority_client,
        correlation_id=correlation_id,
        as_of_date=construction_as_of_date(request=request),
    )


__all__ = [
    "authority_context_for_method",
    "authority_context_for_request_method",
    "regime_context_for_method",
    "risk_context_for_method",
]
