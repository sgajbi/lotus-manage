from src.api.services import construction_source_product_profile_context
from src.api.services.construction_source_product_profile_context import (
    client_restriction_profile_context_update,
    liquidity_context_update,
    source_profile_context_updates,
    sustainability_preference_profile_context_update,
)
from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.api.services.construction_liquidity_source_context import source_liquidity_context
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeLiquidityContext,
    AuthoritativeSustainabilityPreferenceContext,
    ConstructionAuthorityContext,
)
from src.core.dpm_source_context import DpmCoreExecutionContext
from typing import Any, cast
from tests.unit.dpm.construction.source_product_context_fixtures import (
    client_restriction_profile_response,
    liquidity_reserve_requirement_response,
    planned_withdrawal_schedule_response,
    client_income_needs_schedule_response,
    cashflow_projection_response,
    sustainability_preference_profile_response,
)


def test_source_product_profile_context_exports_expected_public_api() -> None:
    assert construction_source_product_profile_context.__all__ == [
        "liquidity_context_update",
        "source_profile_context_updates",
        "client_restriction_profile_context_update",
        "sustainability_preference_profile_context_update",
    ]


def _source_execution_context(**overrides: object) -> DpmCoreExecutionContext:
    payload = cast(
        dict[str, Any],
        {
            "portfolio_cashflow_projection": None,
            "client_income_needs_schedule": None,
            "liquidity_reserve_requirement": None,
            "planned_withdrawal_schedule": None,
            "client_restriction_profile": None,
            "sustainability_preference_profile": None,
            **overrides,
        },
    )
    return DpmCoreExecutionContext.model_construct(**payload)


def test_profile_context_updates_returns_all_expected_contexts() -> None:
    updates = source_profile_context_updates(
        source_context=_source_execution_context(
            portfolio_cashflow_projection=cashflow_projection_response(),
            client_income_needs_schedule=client_income_needs_schedule_response(),
            liquidity_reserve_requirement=liquidity_reserve_requirement_response(),
            planned_withdrawal_schedule=planned_withdrawal_schedule_response(),
            client_restriction_profile=client_restriction_profile_response(),
            sustainability_preference_profile=sustainability_preference_profile_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert sorted(updates) == [
        "client_restriction_context",
        "liquidity_context",
        "sustainability_preference_context",
    ]
    assert updates["liquidity_context"] == source_liquidity_context(
        cashflow_projection=cashflow_projection_response(),
        income_needs=client_income_needs_schedule_response(),
        reserve_requirement=liquidity_reserve_requirement_response(),
        planned_withdrawals=planned_withdrawal_schedule_response(),
    )
    assert updates["client_restriction_context"] == client_restriction_profile_context(
        client_restriction_profile_response()
    )
    assert updates[
        "sustainability_preference_context"
    ] == sustainability_preference_profile_context(sustainability_preference_profile_response())


def test_liquidity_context_update_lifts_reserve_and_withdrawal_sources() -> None:
    update = liquidity_context_update(
        source_context=_source_execution_context(
            liquidity_reserve_requirement=liquidity_reserve_requirement_response(),
            planned_withdrawal_schedule=planned_withdrawal_schedule_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert update is not None
    context_key, liquidity_context = update
    liquidity_context = cast(AuthoritativeLiquidityContext, liquidity_context)

    assert context_key == "liquidity_context"
    assert liquidity_context.cashflow_projection is None
    assert liquidity_context.client_income_needs_schedule is None
    assert liquidity_context.liquidity_reserve_requirement is not None
    assert liquidity_context.liquidity_reserve_requirement.source_id == "reserve-lineage"
    assert liquidity_context.planned_withdrawal_schedule is not None
    assert liquidity_context.planned_withdrawal_schedule.source_id == "withdrawal-lineage"
    assert liquidity_context.reason_codes == [
        "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES",
        "CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT",
        "LIQUIDITY_RESERVE_SOURCE_PRESENT",
        "PLANNED_WITHDRAWAL_SOURCE_PRESENT",
    ]


def test_client_restriction_profile_context_update_lifts_source_profile() -> None:
    update = client_restriction_profile_context_update(
        source_context=_source_execution_context(
            client_restriction_profile=client_restriction_profile_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert update is not None
    context_key, restriction_context = update
    restriction_context = cast(AuthoritativeClientRestrictionContext, restriction_context)

    assert context_key == "client_restriction_context"
    assert restriction_context == client_restriction_profile_context(
        client_restriction_profile_response()
    )


def test_sustainability_preference_profile_context_update_lifts_source_profile() -> None:
    update = sustainability_preference_profile_context_update(
        source_context=_source_execution_context(
            sustainability_preference_profile=sustainability_preference_profile_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert update is not None
    context_key, sustainability_context = update
    sustainability_context = cast(
        AuthoritativeSustainabilityPreferenceContext,
        sustainability_context,
    )

    assert context_key == "sustainability_preference_context"
    assert sustainability_context == sustainability_preference_profile_context(
        sustainability_preference_profile_response()
    )


def test_profile_update_builders_preserve_existing_context() -> None:
    authority_context = ConstructionAuthorityContext(
        liquidity_context=source_liquidity_context(
            cashflow_projection=cashflow_projection_response(),
            income_needs=client_income_needs_schedule_response(),
            reserve_requirement=liquidity_reserve_requirement_response(),
            planned_withdrawals=planned_withdrawal_schedule_response(),
        ),
        client_restriction_context=client_restriction_profile_context(
            client_restriction_profile_response()
        ),
        sustainability_preference_context=sustainability_preference_profile_context(
            sustainability_preference_profile_response()
        ),
    )
    source_context = _source_execution_context(
        portfolio_cashflow_projection=cashflow_projection_response(),
        client_income_needs_schedule=client_income_needs_schedule_response(),
        liquidity_reserve_requirement=liquidity_reserve_requirement_response(),
        planned_withdrawal_schedule=planned_withdrawal_schedule_response(),
        client_restriction_profile=client_restriction_profile_response(),
        sustainability_preference_profile=sustainability_preference_profile_response(),
    )

    assert (
        liquidity_context_update(
            source_context=source_context,
            authority_context=authority_context,
        )
        is None
    )
    assert (
        client_restriction_profile_context_update(
            source_context=source_context,
            authority_context=authority_context,
        )
        is None
    )
    assert (
        sustainability_preference_profile_context_update(
            source_context=source_context,
            authority_context=authority_context,
        )
        is None
    )
