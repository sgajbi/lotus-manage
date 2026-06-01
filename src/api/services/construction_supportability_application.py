from src.api.request_models import RebalanceRequest
from src.api.services.construction_esg_supportability import with_esg_restriction_constraints
from src.api.services.construction_method_readiness import (
    method_specific_reason_codes,
    method_specific_status,
)
from src.api.services.construction_solver_supportability import (
    solver_method_status,
    with_method_reason_codes,
)
from src.api.services.construction_source_analytics_posture import source_analytics_posture
from src.api.services.construction_transaction_cost_supportability import (
    with_observed_transaction_cost_estimate,
)
from src.core.construction.enrichment import summarize_enrichment_posture
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAuthorityContext,
    ConstructionMethodPlan,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult


def apply_construction_supportability(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    plan: ConstructionMethodPlan,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    enrichment = summarize_enrichment_posture(
        result=result,
        tax_required=method == ConstructionMethod.TAX_AWARE,
        risk_required=method == ConstructionMethod.RISK_AWARE,
        risk_context=authority_context.risk_context,
        performance_context=authority_context.performance_context,
        performance_required=False,
        transaction_cost_context=authority_context.transaction_cost_context,
        liquidity_context=(
            authority_context.liquidity_context
            if method == ConstructionMethod.LIQUIDITY_AWARE
            else None
        ),
    )
    if method == ConstructionMethod.COST_AWARE:
        alternative = with_observed_transaction_cost_estimate(
            alternative=alternative,
            result=result,
            context=authority_context.transaction_cost_context,
        )
    if method == ConstructionMethod.ESG_AWARE:
        alternative = with_esg_restriction_constraints(
            request=request,
            alternative=alternative,
            result=result,
            authority_context=authority_context,
        )
    method_reason_codes = method_specific_reason_codes(
        request=request,
        method=method,
        result=result,
        authority_context=authority_context,
    )
    status = lowest_construction_status(
        [
            alternative.method_status,
            plan.method_status,
            method_specific_status(
                request=request,
                method=method,
                result=result,
                enrichment=enrichment,
                authority_context=authority_context,
            ),
        ]
    )
    if method == ConstructionMethod.TAX_AWARE:
        status = lowest_construction_status([status, enrichment.tax_status])
    if method == ConstructionMethod.MIN_TURNOVER:
        status = lowest_construction_status([status, enrichment.turnover_status])
    if method == ConstructionMethod.COST_AWARE:
        status = lowest_construction_status([status, enrichment.cost_status])
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        status = lowest_construction_status([status, solver_method_status(result=result)])
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        status = lowest_construction_status([status, enrichment.liquidity_status])
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        status = lowest_construction_status([status, enrichment.fx_status])
    if method == ConstructionMethod.RISK_AWARE:
        status = lowest_construction_status([status, enrichment.risk_status])
    if method == ConstructionMethod.LIQUIDITY_AWARE and authority_context.liquidity_context:
        status = lowest_construction_status(
            [status, authority_context.liquidity_context.supportability_status]
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY and authority_context.currency_overlay_context:
        status = lowest_construction_status(
            [status, authority_context.currency_overlay_context.supportability_status]
        )
    if method == ConstructionMethod.REGIME_STRESS_AWARE and authority_context.regime_stress_context:
        status = lowest_construction_status(
            [status, authority_context.regime_stress_context.supportability_status]
        )
    return alternative.model_copy(
        update={
            "method_status": status,
            "diagnostics": {
                **alternative.diagnostics,
                "method_plan": plan.model_dump(mode="json"),
                "enrichment_summary": with_method_reason_codes(
                    enrichment=enrichment,
                    reason_codes=method_reason_codes,
                ).model_dump(mode="json"),
                "authority_context": authority_context.model_dump(mode="json", exclude_none=True),
                "source_analytics_posture": source_analytics_posture(
                    method=method,
                    authority_context=authority_context,
                ),
            },
        }
    )


__all__ = ["apply_construction_supportability"]
