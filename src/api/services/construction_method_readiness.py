from collections.abc import Callable
from dataclasses import dataclass

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


@dataclass(frozen=True)
class _MethodStatusContext:
    request: RebalanceRequest
    result: RebalanceResult
    enrichment: ConstructionEnrichmentSummary
    authority_context: ConstructionAuthorityContext


@dataclass(frozen=True)
class _MethodReasonCodeContext:
    request: RebalanceRequest
    result: RebalanceResult
    authority_context: ConstructionAuthorityContext


_MethodStatusBuilder = Callable[[_MethodStatusContext], ConstructionMethodStatus]
_MethodReasonCodeBuilder = Callable[[_MethodReasonCodeContext], list[str]]


def method_specific_status(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    builder = _status_builder_for_method(method=method, result=result)
    if builder is None:
        return ConstructionMethodStatus.READY
    return builder(
        _MethodStatusContext(
            request=request,
            result=result,
            enrichment=enrichment,
            authority_context=authority_context,
        )
    )


def method_specific_reason_codes(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    builder = _reason_code_builder_for_method(method)
    if builder is None:
        return []
    return _sorted_unique_reason_codes(
        builder(
            _MethodReasonCodeContext(
                request=request,
                result=result,
                authority_context=authority_context,
            )
        )
    )


def _status_builder_for_method(
    *,
    method: ConstructionMethod,
    result: RebalanceResult,
) -> _MethodStatusBuilder | None:
    if method == ConstructionMethod.CURRENCY_OVERLAY and result.diagnostics.missing_fx_pairs:
        return None
    return _METHOD_STATUS_BUILDERS.get(method)


def _reason_code_builder_for_method(
    method: ConstructionMethod,
) -> _MethodReasonCodeBuilder | None:
    return _METHOD_REASON_CODE_BUILDERS.get(method)


def _esg_aware_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return esg_restriction_status(
        request=context.request,
        result=context.result,
        authority_context=context.authority_context,
    )


def _regime_stress_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return regime_stress_status(context.authority_context.regime_stress_context)


def _currency_overlay_method_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return currency_overlay_status(
        request=context.request,
        context=context.authority_context.currency_overlay_context,
    )


def _risk_aware_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return context.enrichment.risk_status


def _cost_aware_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return transaction_cost_status(
        result=context.result,
        context=context.authority_context.transaction_cost_context,
    )


def _liquidity_aware_status(context: _MethodStatusContext) -> ConstructionMethodStatus:
    return liquidity_status(
        result=context.result,
        context=context.authority_context.liquidity_context,
    )


def _solver_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return solver_reason_codes(result=context.result)


def _liquidity_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return _liquidity_aware_reason_codes(
        result=context.result,
        authority_context=context.authority_context,
    )


def _risk_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return _risk_aware_reason_codes(context.authority_context)


def _cost_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return transaction_cost_reason_codes(
        result=context.result,
        context=context.authority_context.transaction_cost_context,
    )


def _esg_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return esg_restriction_reason_codes(
        request=context.request,
        result=context.result,
        authority_context=context.authority_context,
    )


def _currency_overlay_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return currency_overlay_reason_codes(
        request=context.request,
        result=context.result,
        authority_context=context.authority_context,
    )


def _regime_stress_method_reason_codes(context: _MethodReasonCodeContext) -> list[str]:
    return _regime_stress_reason_codes(context.authority_context)


def _liquidity_aware_reason_codes(
    *,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    return [
        "SETTLEMENT_AWARENESS_ENABLED",
        *liquidity_reason_codes(result=result, context=authority_context.liquidity_context),
    ]


def _risk_aware_reason_codes(authority_context: ConstructionAuthorityContext) -> list[str]:
    if authority_context.risk_context is None:
        return ["RISK_AUTHORITY_NOT_CONNECTED"]
    return list(authority_context.risk_context.reason_codes)


def _regime_stress_reason_codes(authority_context: ConstructionAuthorityContext) -> list[str]:
    if authority_context.regime_stress_context is None:
        return ["REGIME_SCENARIO_PACK_UNAVAILABLE"]
    return list(authority_context.regime_stress_context.reason_codes)


def _sorted_unique_reason_codes(reason_codes: list[str]) -> list[str]:
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


_METHOD_STATUS_BUILDERS: dict[ConstructionMethod, _MethodStatusBuilder] = {
    ConstructionMethod.ESG_AWARE: _esg_aware_status,
    ConstructionMethod.REGIME_STRESS_AWARE: _regime_stress_status,
    ConstructionMethod.CURRENCY_OVERLAY: _currency_overlay_method_status,
    ConstructionMethod.RISK_AWARE: _risk_aware_status,
    ConstructionMethod.COST_AWARE: _cost_aware_status,
    ConstructionMethod.LIQUIDITY_AWARE: _liquidity_aware_status,
}

_METHOD_REASON_CODE_BUILDERS: dict[ConstructionMethod, _MethodReasonCodeBuilder] = {
    ConstructionMethod.SOLVER_CONSTRAINED: _solver_method_reason_codes,
    ConstructionMethod.LIQUIDITY_AWARE: _liquidity_method_reason_codes,
    ConstructionMethod.RISK_AWARE: _risk_method_reason_codes,
    ConstructionMethod.COST_AWARE: _cost_method_reason_codes,
    ConstructionMethod.ESG_AWARE: _esg_method_reason_codes,
    ConstructionMethod.CURRENCY_OVERLAY: _currency_overlay_method_reason_codes,
    ConstructionMethod.REGIME_STRESS_AWARE: _regime_stress_method_reason_codes,
}


__all__ = [
    "currency_overlay_reason_codes",
    "method_specific_reason_codes",
    "method_specific_status",
    "solver_reason_codes",
]
