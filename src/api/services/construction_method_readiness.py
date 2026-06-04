from src.api.request_models import RebalanceRequest
from src.api.services.construction_esg_supportability import (
    esg_restriction_reason_codes,
    esg_restriction_status,
)
from src.api.services.construction_method_supportability import (
    currency_overlay_status,
    liquidity_reason_codes,
    liquidity_status,
    missing_currency_overlay_pairs,
    regime_stress_status,
)
from src.api.services.construction_transaction_cost_supportability import (
    transaction_cost_reason_codes,
    transaction_cost_status,
)
from src.core.construction.models import (
    ConstructionAuthorityContext,
    ConstructionEnrichmentSummary,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.models import RebalanceResult


def method_specific_status(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    if method == ConstructionMethod.ESG_AWARE:
        return esg_restriction_status(
            request=request,
            result=result,
            authority_context=authority_context,
        )
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        return regime_stress_status(authority_context.regime_stress_context)
    if method == ConstructionMethod.CURRENCY_OVERLAY and not result.diagnostics.missing_fx_pairs:
        return currency_overlay_status(
            request=request,
            context=authority_context.currency_overlay_context,
        )
    if method == ConstructionMethod.RISK_AWARE:
        return enrichment.risk_status
    if method == ConstructionMethod.COST_AWARE:
        return transaction_cost_status(
            result=result,
            context=authority_context.transaction_cost_context,
        )
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        return liquidity_status(
            result=result,
            context=authority_context.liquidity_context,
        )
    return ConstructionMethodStatus.READY


def method_specific_reason_codes(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    reason_codes: list[str] = []
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        reason_codes.extend(solver_reason_codes(result=result))
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        reason_codes.append("SETTLEMENT_AWARENESS_ENABLED")
        reason_codes.extend(
            liquidity_reason_codes(result=result, context=authority_context.liquidity_context)
        )
    if method == ConstructionMethod.RISK_AWARE:
        if authority_context.risk_context is None:
            reason_codes.append("RISK_AUTHORITY_NOT_CONNECTED")
        else:
            reason_codes.extend(authority_context.risk_context.reason_codes)
    if method == ConstructionMethod.COST_AWARE:
        reason_codes.extend(
            transaction_cost_reason_codes(
                result=result,
                context=authority_context.transaction_cost_context,
            )
        )
    if method == ConstructionMethod.ESG_AWARE:
        reason_codes.extend(
            esg_restriction_reason_codes(
                request=request,
                result=result,
                authority_context=authority_context,
            )
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        reason_codes.extend(
            currency_overlay_reason_codes(
                request=request,
                result=result,
                authority_context=authority_context,
            )
        )
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        if authority_context.regime_stress_context is None:
            reason_codes.append("REGIME_SCENARIO_PACK_UNAVAILABLE")
        else:
            reason_codes.extend(authority_context.regime_stress_context.reason_codes)
    return sorted(set(reason_codes))


def solver_reason_codes(*, result: RebalanceResult) -> list[str]:
    reason_codes = [
        warning
        for warning in result.diagnostics.warnings
        if warning.startswith(("SOLVER_", "INFEASIBLE_", "UNBOUNDED_"))
    ]
    if result.explanation.get("target_method_comparison"):
        reason_codes.append("TARGET_METHOD_COMPARISON_AVAILABLE")
    return reason_codes


def currency_overlay_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    reason_codes: list[str] = []
    missing_pairs = missing_currency_overlay_pairs(request=request)
    overlay_status = currency_overlay_status(
        request=request,
        context=authority_context.currency_overlay_context,
    )
    if result.diagnostics.missing_fx_pairs or missing_pairs:
        reason_codes.append("CURRENCY_OVERLAY_FX_SOURCE_MISSING")
    elif overlay_status == ConstructionMethodStatus.BLOCKED:
        reason_codes.append("CURRENCY_OVERLAY_CONTEXT_BLOCKED")
    elif overlay_status == ConstructionMethodStatus.DEGRADED:
        reason_codes.append("CURRENCY_OVERLAY_NO_NON_BASE_EXPOSURE")
    else:
        reason_codes.append("CURRENCY_OVERLAY_FX_SOURCE_READY")
    if authority_context.currency_overlay_context is None:
        reason_codes.append("CURRENCY_OVERLAY_POLICY_CONTEXT_MISSING")
    else:
        reason_codes.extend(authority_context.currency_overlay_context.reason_codes)
    return reason_codes


__all__ = [
    "currency_overlay_reason_codes",
    "method_specific_reason_codes",
    "method_specific_status",
    "solver_reason_codes",
]
