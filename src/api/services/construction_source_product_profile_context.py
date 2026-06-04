from __future__ import annotations

from src.api.services import (
    construction_client_profile_source_context,
    construction_liquidity_source_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext

AuthorityContextUpdate = tuple[str, object]


def liquidity_context_update(
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
    return ("liquidity_context", liquidity_context)


def client_restriction_profile_context_update(
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


def sustainability_preference_profile_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.sustainability_preference_context is not None:
        return None
    sustainability_profile = getattr(
        source_context,
        "sustainability_preference_profile",
        None,
    )
    if sustainability_profile is None:
        return None
    return (
        "sustainability_preference_context",
        construction_client_profile_source_context.sustainability_preference_profile_context(
            sustainability_profile
        ),
    )


def source_profile_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    for update_builder in (
        liquidity_context_update,
        client_restriction_profile_context_update,
        sustainability_preference_profile_context_update,
    ):
        update = update_builder(
            source_context=source_context,
            authority_context=authority_context,
        )
        if update is not None:
            context_key, context_value = update
            context_updates[context_key] = context_value
    return context_updates


__all__ = [
    "liquidity_context_update",
    "source_profile_context_updates",
    "client_restriction_profile_context_update",
    "sustainability_preference_profile_context_update",
]
