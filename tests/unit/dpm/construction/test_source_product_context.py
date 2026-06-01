from src.api.services.construction_liquidity_source_context import (
    source_liquidity_context,
)
from src.api.services.construction_source_product_context import (
    source_product_authority_context_updates,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext
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
