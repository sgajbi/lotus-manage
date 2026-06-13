from typing import Callable

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
    ConstructionEnrichmentSummary,
    ConstructionMethodPlan,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.models import RebalanceResult

_EnrichmentStatusSelector = Callable[
    [ConstructionEnrichmentSummary],
    ConstructionMethodStatus,
]

_METHOD_ENRICHMENT_STATUS_SELECTORS: dict[
    ConstructionMethod,
    _EnrichmentStatusSelector,
] = {
    ConstructionMethod.TAX_AWARE: lambda enrichment: enrichment.tax_status,
    ConstructionMethod.MIN_TURNOVER: lambda enrichment: enrichment.turnover_status,
    ConstructionMethod.COST_AWARE: lambda enrichment: enrichment.cost_status,
    ConstructionMethod.LIQUIDITY_AWARE: lambda enrichment: enrichment.liquidity_status,
    ConstructionMethod.CURRENCY_OVERLAY: lambda enrichment: enrichment.fx_status,
    ConstructionMethod.RISK_AWARE: lambda enrichment: enrichment.risk_status,
}


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
    status = supportability_status(
        request=request,
        method=method,
        alternative=alternative,
        result=result,
        plan=plan,
        enrichment=enrichment,
        authority_context=authority_context,
    )
    return alternative.model_copy(
        update={
            "method_status": status,
            "diagnostics": supportability_diagnostics(
                method=method,
                alternative=alternative,
                plan=plan,
                enrichment=enrichment,
                method_reason_codes=method_reason_codes,
                authority_context=authority_context,
            ),
        }
    )


def supportability_diagnostics(
    *,
    method: ConstructionMethod,
    alternative: ConstructionAlternative,
    plan: ConstructionMethodPlan,
    enrichment: ConstructionEnrichmentSummary,
    method_reason_codes: list[str],
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return {
        **alternative.diagnostics,
        "method_plan": method_plan_diagnostics(plan=plan),
        "enrichment_summary": enrichment_summary_diagnostics(
            enrichment=enrichment,
            method_reason_codes=method_reason_codes,
        ),
        "authority_context": authority_context.model_dump(mode="json", exclude_none=True),
        "source_analytics_posture": source_analytics_posture(
            method=method,
            authority_context=authority_context,
        ),
    }


def method_plan_diagnostics(*, plan: ConstructionMethodPlan) -> dict[str, object]:
    return plan.model_dump(mode="json")


def enrichment_summary_diagnostics(
    *,
    enrichment: ConstructionEnrichmentSummary,
    method_reason_codes: list[str],
) -> dict[str, object]:
    return with_method_reason_codes(
        enrichment=enrichment,
        reason_codes=method_reason_codes,
    ).model_dump(mode="json")


def supportability_status(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    plan: ConstructionMethodPlan,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    statuses = [
        alternative.method_status,
        plan.method_status,
        method_specific_status(
            request=request,
            method=method,
            result=result,
            enrichment=enrichment,
            authority_context=authority_context,
        ),
        *method_enrichment_statuses(
            method=method,
            result=result,
            enrichment=enrichment,
        ),
    ]
    authority_status = authority_context_status(
        method=method,
        authority_context=authority_context,
    )
    if authority_status is not None:
        statuses.append(authority_status)
    return lowest_construction_status(statuses)


def method_enrichment_statuses(
    *,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
) -> list[ConstructionMethodStatus]:
    selector = _METHOD_ENRICHMENT_STATUS_SELECTORS.get(method)
    if selector is not None:
        return [selector(enrichment)]
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        return [solver_method_status(result=result)]
    return []


def authority_context_status(
    *,
    method: ConstructionMethod,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus | None:
    if method == ConstructionMethod.LIQUIDITY_AWARE and authority_context.liquidity_context:
        return authority_context.liquidity_context.supportability_status
    if method == ConstructionMethod.CURRENCY_OVERLAY and authority_context.currency_overlay_context:
        return authority_context.currency_overlay_context.supportability_status
    if method == ConstructionMethod.REGIME_STRESS_AWARE and authority_context.regime_stress_context:
        return authority_context.regime_stress_context.supportability_status
    return None


__all__ = [
    "apply_construction_supportability",
    "authority_context_status",
    "enrichment_summary_diagnostics",
    "method_plan_diagnostics",
    "method_enrichment_statuses",
    "supportability_diagnostics",
    "supportability_status",
]
