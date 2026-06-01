from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.api.services.construction_execution_source_context import (
    external_order_execution_acknowledgement_context,
)
from src.api.services.construction_liquidity_source_context import (
    client_income_needs_schedule_context,
    liquidity_cashflow_projection_context,
    liquidity_reserve_requirement_context,
    planned_withdrawal_schedule_context,
    source_liquidity_context,
    source_status_to_method_status,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext, DpmResolvedSourceContext


def source_product_authority_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    if authority_context.transaction_cost_context is None:
        curve = getattr(source_context, "transaction_cost_curve", None)
        if curve is not None:
            context_updates["transaction_cost_context"] = transaction_cost_context_from_curve(curve)
    if authority_context.liquidity_context is None:
        liquidity_context = source_liquidity_context(
            cashflow_projection=getattr(source_context, "portfolio_cashflow_projection", None),
            income_needs=getattr(source_context, "client_income_needs_schedule", None),
            reserve_requirement=getattr(source_context, "liquidity_reserve_requirement", None),
            planned_withdrawals=getattr(source_context, "planned_withdrawal_schedule", None),
        )
        if liquidity_context is not None:
            context_updates["liquidity_context"] = liquidity_context
    if authority_context.currency_overlay_context is None:
        currency_context = external_treasury_currency_overlay_context(
            hedge_readiness=getattr(source_context, "external_hedge_execution_readiness", None),
            currency_exposure=getattr(source_context, "external_currency_exposure", None),
            hedge_policy=getattr(source_context, "external_hedge_policy", None),
            eligible_hedge_instruments=getattr(
                source_context, "external_eligible_hedge_instruments", None
            ),
            fx_forward_curve=getattr(source_context, "external_fx_forward_curve", None),
        )
        if currency_context is not None:
            context_updates["currency_overlay_context"] = currency_context
    if authority_context.execution_acknowledgement_context is None:
        acknowledgement_context = external_order_execution_acknowledgement_context(
            getattr(source_context, "external_order_execution_acknowledgement", None)
        )
        if acknowledgement_context is not None:
            context_updates["execution_acknowledgement_context"] = acknowledgement_context
    if authority_context.client_restriction_context is None:
        restriction_profile = getattr(source_context, "client_restriction_profile", None)
        if restriction_profile is not None:
            context_updates["client_restriction_context"] = client_restriction_profile_context(
                restriction_profile
            )
    if authority_context.sustainability_preference_context is None:
        sustainability_profile = getattr(source_context, "sustainability_preference_profile", None)
        if sustainability_profile is not None:
            context_updates["sustainability_preference_context"] = (
                sustainability_preference_profile_context(sustainability_profile)
            )
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
    "client_restriction_profile_context",
    "external_order_execution_acknowledgement_context",
    "external_treasury_currency_overlay_context",
    "client_income_needs_schedule_context",
    "liquidity_cashflow_projection_context",
    "liquidity_reserve_requirement_context",
    "planned_withdrawal_schedule_context",
    "source_status_to_method_status",
    "source_liquidity_context",
    "source_product_authority_context_updates",
    "sustainability_preference_profile_context",
    "transaction_cost_context_from_curve",
]
