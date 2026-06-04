from dataclasses import dataclass

from src.api.services import (
    construction_execution_source_context,
    construction_transaction_cost_source_context,
    construction_treasury_source_context,
)
from src.api.services.construction_authority_context_updates import (
    AuthorityContextUpdate,
    collect_authority_context_updates,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import (
    DpmCoreExecutionContext,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
)


@dataclass(frozen=True)
class CurrencyOverlaySourceInputs:
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None


def transaction_cost_curve_context_update(
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


def currency_overlay_context_update(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> AuthorityContextUpdate | None:
    if authority_context.currency_overlay_context is not None:
        return None
    source_inputs = currency_overlay_source_inputs(source_context)
    currency_context = (
        construction_treasury_source_context.external_treasury_currency_overlay_context(
            hedge_readiness=source_inputs.hedge_readiness,
            currency_exposure=source_inputs.currency_exposure,
            hedge_policy=source_inputs.hedge_policy,
            eligible_hedge_instruments=source_inputs.eligible_hedge_instruments,
            fx_forward_curve=source_inputs.fx_forward_curve,
        )
    )
    if currency_context is None:
        return None
    return ("currency_overlay_context", currency_context)


def currency_overlay_source_inputs(
    source_context: DpmCoreExecutionContext,
) -> CurrencyOverlaySourceInputs:
    return CurrencyOverlaySourceInputs(
        hedge_readiness=getattr(source_context, "external_hedge_execution_readiness", None),
        currency_exposure=getattr(source_context, "external_currency_exposure", None),
        hedge_policy=getattr(source_context, "external_hedge_policy", None),
        eligible_hedge_instruments=getattr(
            source_context, "external_eligible_hedge_instruments", None
        ),
        fx_forward_curve=getattr(source_context, "external_fx_forward_curve", None),
    )


def execution_acknowledgement_context_update(
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
    return ("execution_acknowledgement_context", acknowledgement_context)


def source_financial_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return collect_authority_context_updates(
        source_context=source_context,
        authority_context=authority_context,
        update_builders=(
            transaction_cost_curve_context_update,
            currency_overlay_context_update,
            execution_acknowledgement_context_update,
        ),
    )


__all__ = [
    "CurrencyOverlaySourceInputs",
    "currency_overlay_context_update",
    "currency_overlay_source_inputs",
    "execution_acknowledgement_context_update",
    "source_financial_context_updates",
    "transaction_cost_curve_context_update",
]
