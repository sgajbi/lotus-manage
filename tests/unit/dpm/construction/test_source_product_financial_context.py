from src.api.services import construction_source_product_financial_context
from src.api.services.construction_source_product_financial_context import (
    source_financial_context_updates,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.api.services.construction_execution_source_context import (
    external_order_execution_acknowledgement_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext
from typing import Any, cast
from tests.unit.dpm.construction.source_product_context_fixtures import (
    external_order_acknowledgement_response,
    transaction_cost_curve_response,
    hedge_readiness_response,
)


def test_source_product_financial_context_exports_only_orchestration_surface() -> None:
    assert construction_source_product_financial_context.__all__ == [
        "source_financial_context_updates",
    ]


def _source_execution_context(**overrides: object) -> DpmCoreExecutionContext:
    payload = cast(
        dict[str, Any],
        {
            "transaction_cost_curve": None,
            "external_hedge_execution_readiness": None,
            "external_currency_exposure": None,
            "external_hedge_policy": None,
            "external_eligible_hedge_instruments": None,
            "external_fx_forward_curve": None,
            "external_order_execution_acknowledgement": None,
            **overrides,
        },
    )
    return DpmCoreExecutionContext.model_construct(**payload)


def test_source_financial_context_updates_collects_cost_currency_and_acknowledgement() -> None:
    updates = source_financial_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            external_hedge_execution_readiness=hedge_readiness_response(),
            external_currency_exposure=None,
            external_hedge_policy=None,
            external_eligible_hedge_instruments=None,
            external_fx_forward_curve=None,
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert sorted(updates) == [
        "currency_overlay_context",
        "execution_acknowledgement_context",
        "transaction_cost_context",
    ]
    assert updates["transaction_cost_context"] == transaction_cost_context_from_curve(
        transaction_cost_curve_response()
    )
    assert updates["currency_overlay_context"] == external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=None,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )
    assert updates[
        "execution_acknowledgement_context"
    ] == external_order_execution_acknowledgement_context(external_order_acknowledgement_response())


def test_source_financial_context_updates_preserves_existing_contexts() -> None:
    existing_context = ConstructionAuthorityContext(
        transaction_cost_context=transaction_cost_context_from_curve(
            transaction_cost_curve_response()
        ),
        currency_overlay_context=external_treasury_currency_overlay_context(
            hedge_readiness=hedge_readiness_response(),
            currency_exposure=None,
            hedge_policy=None,
            eligible_hedge_instruments=None,
            fx_forward_curve=None,
        ),
        execution_acknowledgement_context=external_order_execution_acknowledgement_context(
            external_order_acknowledgement_response()
        ),
    )

    updates = source_financial_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            external_hedge_execution_readiness=hedge_readiness_response(),
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
        ),
        authority_context=existing_context,
    )

    assert updates == {}
