from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status

from src.core.common.capabilities import has_solver_dependencies
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.alternative_engine import (
    build_alternative_set,
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.construction.enrichment import summarize_enrichment_posture
from src.core.construction.method_registry import classify_solver_failure, resolve_method_plan
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
    ConstructionEnrichmentSummary,
    ConstructionMethodPlan,
)
from src.core.construction.repository import (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
    ConstructionRepository,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    FIRST_WAVE_CONSTRUCTION_METHODS,
)
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import EngineOptions, RebalanceResult, TargetMethod
from src.core.rebalance.engine import run_simulation
from src.api.request_models import RebalanceRequest

_MIN_TURNOVER_DEFAULT = Decimal("0.10")


def generate_construction_alternative_set(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    repository: ConstructionRepository,
    methods: list[ConstructionMethod] | None = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
) -> ConstructionAlternativeSet:
    method_set = list(methods or FIRST_WAVE_CONSTRUCTION_METHODS)
    request_payload = {
        "request": request.model_dump(mode="json"),
        "methods": [method.value for method in method_set],
        "source_context_hash": (
            source_context.stateful_context_hash if source_context is not None else None
        ),
    }
    request_hash = hash_canonical_payload(request_payload)
    existing = repository.get_alternative_set_by_idempotency(idempotency_key=idempotency_key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")
        return existing

    base_result = _run_method(
        request=request,
        method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        correlation_id=correlation_id,
    )
    alternatives = _build_alternatives(
        request=request,
        method_set=method_set,
        base_result=base_result,
        correlation_id=correlation_id,
    )
    alternative_set = build_alternative_set(
        alternative_set_id=f"cas_{uuid.uuid4().hex[:12]}",
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        as_of=datetime.now(timezone.utc).date().isoformat(),
        alternatives=alternatives,
    ).model_copy(
        update={
            "request_hash": request_hash,
            "input_mode": "stateful" if source_context is not None else "stateless",
            "source_supportability_state": (
                source_context.context.supportability.state if source_context is not None else None
            ),
        }
    )
    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key=idempotency_key,
    )
    return alternative_set


def get_construction_alternative_set(
    *,
    repository: ConstructionRepository,
    alternative_set_id: str,
) -> ConstructionAlternativeSet:
    alternative_set = repository.get_alternative_set(alternative_set_id=alternative_set_id)
    if alternative_set is None:
        raise ConstructionAlternativeSetNotFoundError("CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND")
    return alternative_set


def select_construction_alternative(
    *,
    repository: ConstructionRepository,
    alternative_set_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str | None,
) -> ConstructionAlternativeSelection:
    alternative_set = get_construction_alternative_set(
        repository=repository,
        alternative_set_id=alternative_set_id,
    )
    if alternative_id not in {
        alternative.alternative_id for alternative in alternative_set.alternatives
    }:
        raise ConstructionAlternativeNotFoundError("CONSTRUCTION_ALTERNATIVE_NOT_FOUND")
    selection = ConstructionAlternativeSelection(
        selection_id=f"casel_{uuid.uuid4().hex[:12]}",
        alternative_set_id=alternative_set_id,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    repository.save_selection(selection=selection)
    return selection


def to_api_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ConstructionIdempotencyConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(
        exc, (ConstructionAlternativeSetNotFoundError, ConstructionAlternativeNotFoundError)
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=type(exc).__name__
    )


def _build_alternatives(
    *,
    request: RebalanceRequest,
    method_set: list[ConstructionMethod],
    base_result: RebalanceResult,
    correlation_id: Optional[str],
) -> list[ConstructionAlternative]:
    alternatives: list[ConstructionAlternative] = []
    solver_available = has_solver_dependencies()
    for method in method_set:
        if method == ConstructionMethod.DO_NOTHING_BASELINE:
            alternatives.append(build_do_nothing_baseline(result=base_result))
            continue
        plan = resolve_method_plan(method=method, solver_available=solver_available)
        result = base_result
        if plan.effective_method != ConstructionMethod.HEURISTIC_EXPLAINABLE:
            result = _run_method(
                request=request,
                method=plan.effective_method,
                correlation_id=correlation_id,
            )
        alternative = build_rebalance_result_alternative(
            result=result,
            method=method,
            alternative_id=f"alt_{method.value.lower()}",
        )
        alternatives.append(
            _apply_supportability(
                request=request,
                method=method,
                alternative=alternative,
                result=result,
                plan=plan,
            )
        )
    return alternatives


def _run_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    correlation_id: Optional[str],
) -> RebalanceResult:
    options = _options_for_method(options=request.options, method=method)
    return run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=options,
        request_hash=f"construction:{method.value}:{uuid.uuid4().hex[:8]}",
        correlation_id=correlation_id or f"corr_construction_{uuid.uuid4().hex[:10]}",
    )


def _options_for_method(
    *,
    options: EngineOptions,
    method: ConstructionMethod,
) -> EngineOptions:
    if method == ConstructionMethod.MIN_TURNOVER:
        max_turnover_pct = options.max_turnover_pct
        if max_turnover_pct is None or max_turnover_pct > _MIN_TURNOVER_DEFAULT:
            max_turnover_pct = _MIN_TURNOVER_DEFAULT
        return options.model_copy(update={"max_turnover_pct": max_turnover_pct})
    if method == ConstructionMethod.TAX_AWARE:
        return options.model_copy(update={"enable_tax_awareness": True})
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        return options.model_copy(
            update={"target_method": TargetMethod.SOLVER, "compare_target_methods": True}
        )
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        return options.model_copy(
            update={
                "enable_settlement_awareness": True,
                "min_cash_buffer_pct": max(options.min_cash_buffer_pct, Decimal("0.03")),
            }
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        return options.model_copy(
            update={
                "block_on_missing_fx": True,
                "enable_settlement_awareness": True,
                "fx_buffer_pct": max(options.fx_buffer_pct, Decimal("0.01")),
            }
        )
    if method == ConstructionMethod.RISK_AWARE:
        max_weight = options.single_position_max_weight
        if max_weight is None or max_weight > Decimal("0.30"):
            max_weight = Decimal("0.30")
        return options.model_copy(update={"single_position_max_weight": max_weight})
    return options


def _apply_supportability(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    plan: ConstructionMethodPlan,
) -> ConstructionAlternative:
    enrichment = summarize_enrichment_posture(
        result=result,
        tax_required=method == ConstructionMethod.TAX_AWARE,
    )
    method_reason_codes = _method_specific_reason_codes(
        request=request,
        method=method,
        result=result,
        enrichment=enrichment,
    )
    status = _lowest_status(
        [
            alternative.method_status,
            plan.method_status,
            _method_specific_status(
                request=request,
                method=method,
                result=result,
                enrichment=enrichment,
            ),
        ]
    )
    if method == ConstructionMethod.TAX_AWARE:
        status = _lowest_status([status, enrichment.tax_status])
    if method == ConstructionMethod.MIN_TURNOVER:
        status = _lowest_status([status, enrichment.turnover_status])
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        status = _lowest_status([status, _solver_method_status(result=result)])
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        status = _lowest_status([status, enrichment.liquidity_status])
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        status = _lowest_status([status, enrichment.fx_status])
    if method == ConstructionMethod.RISK_AWARE:
        status = _lowest_status([status, enrichment.risk_status])
    return alternative.model_copy(
        update={
            "method_status": status,
            "diagnostics": {
                **alternative.diagnostics,
                "method_plan": plan.model_dump(mode="json"),
                "enrichment_summary": _with_method_reason_codes(
                    enrichment=enrichment,
                    reason_codes=method_reason_codes,
                ).model_dump(mode="json"),
            },
        }
    )


def _method_specific_status(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
) -> ConstructionMethodStatus:
    if method == ConstructionMethod.ESG_AWARE:
        return _esg_status(request=request)
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        return ConstructionMethodStatus.DEGRADED
    if method == ConstructionMethod.CURRENCY_OVERLAY and not result.diagnostics.missing_fx_pairs:
        return _currency_overlay_status(request=request)
    if method == ConstructionMethod.RISK_AWARE:
        return enrichment.risk_status
    return ConstructionMethodStatus.READY


def _method_specific_reason_codes(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
) -> list[str]:
    reason_codes: list[str] = []
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        reason_codes.extend(
            warning
            for warning in result.diagnostics.warnings
            if warning.startswith(("SOLVER_", "INFEASIBLE_", "UNBOUNDED_"))
        )
        if result.explanation.get("target_method_comparison"):
            reason_codes.append("TARGET_METHOD_COMPARISON_AVAILABLE")
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        reason_codes.append("SETTLEMENT_AWARENESS_ENABLED")
        if enrichment.liquidity_status != ConstructionMethodStatus.READY:
            reason_codes.append("LIQUIDITY_POSTURE_DEGRADED")
    if method == ConstructionMethod.RISK_AWARE:
        reason_codes.append("RISK_AUTHORITY_NOT_CONNECTED")
    if method == ConstructionMethod.ESG_AWARE:
        reason_codes.append(
            "ESG_PROFILE_SOURCE_PRESENT"
            if _esg_status(request=request) == ConstructionMethodStatus.READY
            else "ESG_PROFILE_UNAVAILABLE"
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        if result.diagnostics.missing_fx_pairs:
            reason_codes.append("CURRENCY_OVERLAY_FX_SOURCE_MISSING")
        elif _currency_overlay_status(request=request) == ConstructionMethodStatus.DEGRADED:
            reason_codes.append("CURRENCY_OVERLAY_NO_NON_BASE_EXPOSURE")
        else:
            reason_codes.append("CURRENCY_OVERLAY_FX_SOURCE_READY")
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        reason_codes.append("REGIME_SCENARIO_PACK_UNAVAILABLE")
    return sorted(set(reason_codes))


def _with_method_reason_codes(
    *,
    enrichment: ConstructionEnrichmentSummary,
    reason_codes: list[str],
) -> ConstructionEnrichmentSummary:
    return enrichment.model_copy(
        update={"reason_codes": sorted(set(enrichment.reason_codes) | set(reason_codes))}
    )


def _solver_method_status(*, result: RebalanceResult) -> ConstructionMethodStatus:
    solver_warnings = [
        warning
        for warning in result.diagnostics.warnings
        if warning.startswith(("SOLVER_", "INFEASIBLE_", "UNBOUNDED_"))
    ]
    if not solver_warnings:
        return ConstructionMethodStatus.READY
    return _lowest_status([classify_solver_failure(warning) for warning in solver_warnings])


def _esg_status(*, request: RebalanceRequest) -> ConstructionMethodStatus:
    for entry in request.shelf_entries:
        if "esg_profile" in entry.attributes or "sustainability_profile" in entry.attributes:
            return ConstructionMethodStatus.READY
    return ConstructionMethodStatus.DEGRADED


def _currency_overlay_status(*, request: RebalanceRequest) -> ConstructionMethodStatus:
    base_currency = request.portfolio_snapshot.base_currency
    instrument_currencies = {
        price.currency for price in request.market_data_snapshot.prices if price.currency != base_currency
    }
    return (
        ConstructionMethodStatus.READY
        if instrument_currencies
        else ConstructionMethodStatus.DEGRADED
    )


def _lowest_status(statuses: list[ConstructionMethodStatus]) -> ConstructionMethodStatus:
    status_order = {
        ConstructionMethodStatus.BLOCKED: 0,
        ConstructionMethodStatus.DEGRADED: 1,
        ConstructionMethodStatus.PENDING_REVIEW: 2,
        ConstructionMethodStatus.READY: 3,
    }
    return min(statuses, key=lambda item: status_order[item])
