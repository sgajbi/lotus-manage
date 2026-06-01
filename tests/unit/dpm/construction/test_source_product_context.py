from src.api.services.construction_liquidity_source_context import (
    source_liquidity_context,
)
from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.api.services.construction_execution_source_context import (
    external_order_execution_acknowledgement_context,
)
from src.api.services.construction_source_product_context import (
    authority_context_with_source_products,
    source_product_authority_context_updates,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext, DpmResolvedSourceContext
from tests.unit.dpm.construction.source_product_context_fixtures import (
    cashflow_projection_response,
    client_income_needs_schedule_response,
    client_restriction_profile_response,
    external_order_acknowledgement_response,
    hedge_readiness_response,
    liquidity_reserve_requirement_response,
    planned_withdrawal_schedule_response,
    sustainability_preference_profile_response,
    transaction_cost_curve_response,
)


def _source_execution_context(**overrides: object) -> DpmCoreExecutionContext:
    source_products = {
        "transaction_cost_curve": None,
        "portfolio_cashflow_projection": None,
        "client_income_needs_schedule": None,
        "liquidity_reserve_requirement": None,
        "planned_withdrawal_schedule": None,
        "external_hedge_execution_readiness": None,
        "external_currency_exposure": None,
        "external_hedge_policy": None,
        "external_eligible_hedge_instruments": None,
        "external_fx_forward_curve": None,
        "external_order_execution_acknowledgement": None,
        "client_restriction_profile": None,
        "sustainability_preference_profile": None,
    }
    source_products.update(overrides)
    return DpmCoreExecutionContext.model_construct(**source_products)


def test_authority_context_with_source_products_returns_existing_context_without_source() -> None:
    authority_context = ConstructionAuthorityContext()

    resolved_context = authority_context_with_source_products(
        authority_context=authority_context,
        source_context=None,
    )

    assert resolved_context is authority_context


def test_source_product_authority_context_updates_empty_without_source_products() -> None:
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(),
        authority_context=ConstructionAuthorityContext(),
    )

    assert updates == {}


def test_source_product_authority_context_updates_lifts_all_source_families() -> None:
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            portfolio_cashflow_projection=cashflow_projection_response(),
            client_income_needs_schedule=client_income_needs_schedule_response(),
            liquidity_reserve_requirement=liquidity_reserve_requirement_response(),
            planned_withdrawal_schedule=planned_withdrawal_schedule_response(),
            external_hedge_execution_readiness=hedge_readiness_response(),
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
            client_restriction_profile=client_restriction_profile_response(),
            sustainability_preference_profile=sustainability_preference_profile_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert sorted(updates) == [
        "client_restriction_context",
        "currency_overlay_context",
        "execution_acknowledgement_context",
        "liquidity_context",
        "sustainability_preference_context",
        "transaction_cost_context",
    ]
    assert updates["transaction_cost_context"].source_id == "curve-lineage"
    assert updates["liquidity_context"].planned_withdrawal_schedule is not None
    assert updates["currency_overlay_context"].source_id == "core-hedge-readiness"
    assert updates["execution_acknowledgement_context"].source_id == "core-ack-fingerprint"
    assert updates["client_restriction_context"].source_id == "restriction-lineage"
    assert updates["sustainability_preference_context"].source_id == "sustainability-lineage"


def test_source_product_authority_context_updates_preserves_existing_contexts() -> None:
    existing_liquidity_context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response(),
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )
    assert existing_liquidity_context is not None
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            portfolio_cashflow_projection=cashflow_projection_response(),
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
        ),
        authority_context=ConstructionAuthorityContext(
            transaction_cost_context=transaction_cost_context_from_curve(
                transaction_cost_curve_response()
            ),
            liquidity_context=existing_liquidity_context,
        ),
    )

    assert "transaction_cost_context" not in updates
    assert "liquidity_context" not in updates
    assert sorted(updates) == ["execution_acknowledgement_context"]


def test_source_product_authority_context_updates_preserves_all_existing_source_contexts() -> None:
    existing_liquidity_context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response(),
        income_needs=client_income_needs_schedule_response(),
        reserve_requirement=liquidity_reserve_requirement_response(),
        planned_withdrawals=planned_withdrawal_schedule_response(),
    )
    existing_currency_context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=None,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )
    existing_execution_context = external_order_execution_acknowledgement_context(
        external_order_acknowledgement_response()
    )
    assert existing_liquidity_context is not None
    assert existing_currency_context is not None
    assert existing_execution_context is not None
    authority_context = ConstructionAuthorityContext(
        transaction_cost_context=transaction_cost_context_from_curve(
            transaction_cost_curve_response()
        ),
        liquidity_context=existing_liquidity_context,
        currency_overlay_context=existing_currency_context,
        execution_acknowledgement_context=existing_execution_context,
        client_restriction_context=client_restriction_profile_context(
            client_restriction_profile_response()
        ),
        sustainability_preference_context=sustainability_preference_profile_context(
            sustainability_preference_profile_response()
        ),
    )
    source_context = _source_execution_context(
        transaction_cost_curve=transaction_cost_curve_response(),
        portfolio_cashflow_projection=cashflow_projection_response(),
        client_income_needs_schedule=client_income_needs_schedule_response(),
        liquidity_reserve_requirement=liquidity_reserve_requirement_response(),
        planned_withdrawal_schedule=planned_withdrawal_schedule_response(),
        external_hedge_execution_readiness=hedge_readiness_response(),
        external_order_execution_acknowledgement=external_order_acknowledgement_response(),
        client_restriction_profile=client_restriction_profile_response(),
        sustainability_preference_profile=sustainability_preference_profile_response(),
    )

    updates = source_product_authority_context_updates(
        source_context=source_context,
        authority_context=authority_context,
    )
    resolved_context = authority_context_with_source_products(
        authority_context=authority_context,
        source_context=DpmResolvedSourceContext.model_construct(context=source_context),
    )

    assert updates == {}
    assert resolved_context is authority_context
