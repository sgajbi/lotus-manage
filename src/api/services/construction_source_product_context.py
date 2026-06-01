from src.api.services import construction_client_profile_source_context
from src.api.services import construction_execution_source_context
from src.api.services import construction_liquidity_source_context
from src.api.services import construction_transaction_cost_source_context
from src.api.services import construction_treasury_source_context
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext, DpmResolvedSourceContext

AuthorityContextUpdate = tuple[str, object]


def _transaction_cost_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.transaction_cost_context is not None:
        return None
    curve = getattr(source_context, "transaction_cost_curve", None)
    if curve is None:
        return None
    return (
        "transaction_cost_context",
        construction_transaction_cost_source_context.transaction_cost_context_from_curve(curve),
    )


def _liquidity_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.liquidity_context is not None:
        return None
    liquidity_context = construction_liquidity_source_context.source_liquidity_context(
        cashflow_projection=getattr(source_context, "portfolio_cashflow_projection", None),
        income_needs=getattr(source_context, "client_income_needs_schedule", None),
        reserve_requirement=getattr(source_context, "liquidity_reserve_requirement", None),
        planned_withdrawals=getattr(source_context, "planned_withdrawal_schedule", None),
    )
    if liquidity_context is None:
        return None
    return "liquidity_context", liquidity_context


def _currency_overlay_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.currency_overlay_context is not None:
        return None
    currency_context = (
        construction_treasury_source_context.external_treasury_currency_overlay_context(
            hedge_readiness=getattr(source_context, "external_hedge_execution_readiness", None),
            currency_exposure=getattr(source_context, "external_currency_exposure", None),
            hedge_policy=getattr(source_context, "external_hedge_policy", None),
            eligible_hedge_instruments=getattr(
                source_context, "external_eligible_hedge_instruments", None
            ),
            fx_forward_curve=getattr(source_context, "external_fx_forward_curve", None),
        )
    )
    if currency_context is None:
        return None
    return "currency_overlay_context", currency_context


def _execution_acknowledgement_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.execution_acknowledgement_context is not None:
        return None
    acknowledgement_context = (
        construction_execution_source_context.external_order_execution_acknowledgement_context(
            getattr(source_context, "external_order_execution_acknowledgement", None)
        )
    )
    if acknowledgement_context is None:
        return None
    return "execution_acknowledgement_context", acknowledgement_context


def _client_restriction_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.client_restriction_context is not None:
        return None
    restriction_profile = getattr(source_context, "client_restriction_profile", None)
    if restriction_profile is None:
        return None
    return (
        "client_restriction_context",
        construction_client_profile_source_context.client_restriction_profile_context(
            restriction_profile
        ),
    )


def _sustainability_preference_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.sustainability_preference_context is not None:
        return None
    sustainability_profile = getattr(source_context, "sustainability_preference_profile", None)
    if sustainability_profile is None:
        return None
    return (
        "sustainability_preference_context",
        construction_client_profile_source_context.sustainability_preference_profile_context(
            sustainability_profile
        ),
    )


def source_product_authority_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    for update_builder in (
        _transaction_cost_context_update,
        _liquidity_context_update,
        _currency_overlay_context_update,
        _execution_acknowledgement_context_update,
        _client_restriction_context_update,
        _sustainability_preference_context_update,
    ):
        update = update_builder(source_context=source_context, authority_context=authority_context)
        if update is not None:
            context_key, context_value = update
            context_updates[context_key] = context_value
    return context_updates


def authority_context_with_source_products(
    *,
    authority_context: ConstructionAuthorityContext,
    source_context: DpmResolvedSourceContext | None,
) -> ConstructionAuthorityContext:
    if source_context is None:
        return authority_context
    context_updates = source_product_authority_context_updates(
        source_context=source_context.context,
        authority_context=authority_context,
    )
    if not context_updates:
        return authority_context
    return authority_context.model_copy(update=context_updates)


__all__ = [
    "authority_context_with_source_products",
    "source_product_authority_context_updates",
]
