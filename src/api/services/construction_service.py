from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import re
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
    AuthoritativeClientIncomeNeedsSchedule,
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
    AuthoritativeLiquidityReserveRequirement,
    AuthoritativePlannedWithdrawalSchedule,
    AuthoritativeRegimeStressContext,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
    ConstructionAuthorityContext,
    ConstructionConstraintTrace,
    ConstructionEnrichmentSummary,
    ConstructionMethodPlan,
    ConstructionObjectiveTerm,
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
    ConstructionSourceFamily,
    ConstructionTraceTerm,
    FIRST_WAVE_CONSTRUCTION_METHODS,
)
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import EngineOptions, RebalanceResult, TargetMethod
from src.core.models import Money, SecurityTradeIntent, ShelfEntry
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.service import DpmRunSupportService
from src.api.request_models import RebalanceRequest
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)

_MIN_TURNOVER_DEFAULT = Decimal("0.10")
_DATE_PATTERN = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")
_MONEY_QUANT = Decimal("0.0001")


def generate_construction_alternative_set(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    repository: ConstructionRepository,
    methods: list[ConstructionMethod] | None = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
    authority_context: ConstructionAuthorityContext | None = None,
    risk_authority_client: LotusRiskAuthorityClient | None = None,
    run_service: DpmRunSupportService | None = None,
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
        request_hash=f"{request_hash}:{ConstructionMethod.HEURISTIC_EXPLAINABLE.value}",
        run_service=run_service,
    )
    resolved_authority_context = _authority_context_with_source_products(
        authority_context=authority_context or ConstructionAuthorityContext(),
        source_context=source_context,
    )
    alternatives = _build_alternatives(
        request=request,
        method_set=method_set,
        base_result=base_result,
        correlation_id=correlation_id,
        request_hash=request_hash,
        authority_context=resolved_authority_context,
        risk_authority_client=risk_authority_client,
        run_service=run_service,
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
    request_hash: str,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    run_service: DpmRunSupportService | None,
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
                request_hash=f"{request_hash}:{plan.effective_method.value}",
                run_service=run_service,
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
                authority_context=_authority_context_for_method(
                    request=request,
                    method=method,
                    result=result,
                    authority_context=authority_context,
                    risk_authority_client=risk_authority_client,
                    correlation_id=correlation_id,
                ),
            )
        )
    return alternatives


def _run_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    correlation_id: Optional[str],
    request_hash: str,
    run_service: DpmRunSupportService | None,
) -> RebalanceResult:
    options = _options_for_method(options=request.options, method=method)
    run_correlation_id = (
        f"{correlation_id}:{method.value.lower()}"
        if correlation_id
        else f"corr_construction_{method.value.lower()}_{uuid.uuid4().hex[:10]}"
    )
    result = run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=options,
        request_hash=request_hash,
        correlation_id=run_correlation_id,
    )
    if run_service is not None:
        run_service.record_run(
            result=result,
            request_hash=request_hash,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
            idempotency_key=None,
        )
    return result


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
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    enrichment = summarize_enrichment_posture(
        result=result,
        tax_required=method == ConstructionMethod.TAX_AWARE,
        risk_required=method == ConstructionMethod.RISK_AWARE,
        risk_context=(
            authority_context.risk_context if method == ConstructionMethod.RISK_AWARE else None
        ),
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
        alternative = _with_observed_transaction_cost_estimate(
            alternative=alternative,
            result=result,
            context=authority_context.transaction_cost_context,
        )
    if method == ConstructionMethod.ESG_AWARE:
        alternative = _with_esg_restriction_constraints(
            request=request,
            alternative=alternative,
            result=result,
            authority_context=authority_context,
        )
    method_reason_codes = _method_specific_reason_codes(
        request=request,
        method=method,
        result=result,
        enrichment=enrichment,
        authority_context=authority_context,
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
                authority_context=authority_context,
            ),
        ]
    )
    if method == ConstructionMethod.TAX_AWARE:
        status = _lowest_status([status, enrichment.tax_status])
    if method == ConstructionMethod.MIN_TURNOVER:
        status = _lowest_status([status, enrichment.turnover_status])
    if method == ConstructionMethod.COST_AWARE:
        status = _lowest_status([status, enrichment.cost_status])
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        status = _lowest_status([status, _solver_method_status(result=result)])
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        status = _lowest_status([status, enrichment.liquidity_status])
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        status = _lowest_status([status, enrichment.fx_status])
    if method == ConstructionMethod.RISK_AWARE:
        status = _lowest_status([status, enrichment.risk_status])
    if method == ConstructionMethod.LIQUIDITY_AWARE and authority_context.liquidity_context:
        status = _lowest_status([status, authority_context.liquidity_context.supportability_status])
    if method == ConstructionMethod.CURRENCY_OVERLAY and authority_context.currency_overlay_context:
        status = _lowest_status(
            [status, authority_context.currency_overlay_context.supportability_status]
        )
    if method == ConstructionMethod.REGIME_STRESS_AWARE and authority_context.regime_stress_context:
        status = _lowest_status(
            [status, authority_context.regime_stress_context.supportability_status]
        )
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
                "authority_context": authority_context.model_dump(mode="json", exclude_none=True),
            },
        }
    )


def _method_specific_status(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    if method == ConstructionMethod.ESG_AWARE:
        return _esg_restriction_status(
            request=request,
            result=result,
            authority_context=authority_context,
        )
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        return _regime_stress_status(authority_context.regime_stress_context)
    if method == ConstructionMethod.CURRENCY_OVERLAY and not result.diagnostics.missing_fx_pairs:
        return _currency_overlay_status(
            request=request,
            context=authority_context.currency_overlay_context,
        )
    if method == ConstructionMethod.RISK_AWARE:
        return enrichment.risk_status
    if method == ConstructionMethod.COST_AWARE:
        return _transaction_cost_status(
            result=result,
            context=authority_context.transaction_cost_context,
        )
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        return _liquidity_status(
            result=result,
            context=authority_context.liquidity_context,
        )
    return ConstructionMethodStatus.READY


def _method_specific_reason_codes(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
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
        reason_codes.extend(
            _liquidity_reason_codes(result=result, context=authority_context.liquidity_context)
        )
    if method == ConstructionMethod.RISK_AWARE:
        if authority_context.risk_context is None:
            reason_codes.append("RISK_AUTHORITY_NOT_CONNECTED")
        else:
            reason_codes.extend(authority_context.risk_context.reason_codes)
    if method == ConstructionMethod.COST_AWARE:
        reason_codes.extend(
            _transaction_cost_reason_codes(
                result=result,
                context=authority_context.transaction_cost_context,
            )
        )
    if method == ConstructionMethod.ESG_AWARE:
        reason_codes.extend(
            _esg_restriction_reason_codes(
                request=request,
                result=result,
                authority_context=authority_context,
            )
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        missing_pairs = _missing_currency_overlay_pairs(request=request)
        overlay_status = _currency_overlay_status(
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
    if method == ConstructionMethod.REGIME_STRESS_AWARE:
        if authority_context.regime_stress_context is None:
            reason_codes.append("REGIME_SCENARIO_PACK_UNAVAILABLE")
        else:
            reason_codes.extend(authority_context.regime_stress_context.reason_codes)
    return sorted(set(reason_codes))


def _authority_context_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    correlation_id: str | None,
) -> ConstructionAuthorityContext:
    risk_context = authority_context.risk_context
    if method == ConstructionMethod.RISK_AWARE and risk_context is None and risk_authority_client:
        try:
            risk_context = risk_authority_client.concentration_context(
                result=result,
                correlation_id=correlation_id,
            )
        except LotusRiskAuthorityUnavailableError:
            risk_context = None
    liquidity_context = authority_context.liquidity_context
    if method == ConstructionMethod.LIQUIDITY_AWARE and liquidity_context is None:
        liquidity_context = _derive_liquidity_context(result=result)
    currency_context = authority_context.currency_overlay_context
    if method == ConstructionMethod.CURRENCY_OVERLAY and currency_context is None:
        currency_context = _derive_currency_overlay_context(result=result)
    regime_context = authority_context.regime_stress_context
    if (
        method == ConstructionMethod.REGIME_STRESS_AWARE
        and regime_context is None
        and risk_authority_client
    ):
        try:
            regime_context = risk_authority_client.regime_scenario_context(
                result=result,
                portfolio_id=request.portfolio_snapshot.portfolio_id,
                as_of_date=_construction_as_of_date(request=request),
                correlation_id=correlation_id,
            )
        except LotusRiskAuthorityUnavailableError:
            regime_context = None
    return ConstructionAuthorityContext(
        risk_context=risk_context,
        performance_context=authority_context.performance_context,
        transaction_cost_context=authority_context.transaction_cost_context,
        liquidity_context=liquidity_context,
        currency_overlay_context=currency_context,
        regime_stress_context=regime_context,
        client_restriction_context=authority_context.client_restriction_context,
        sustainability_preference_context=authority_context.sustainability_preference_context,
    )


def _authority_context_with_source_products(
    *,
    authority_context: ConstructionAuthorityContext,
    source_context: DpmResolvedSourceContext | None,
) -> ConstructionAuthorityContext:
    if source_context is None:
        return authority_context
    context_updates: dict[str, object] = {}
    if authority_context.transaction_cost_context is None:
        curve = source_context.context.transaction_cost_curve
        if curve is not None:
            curve_payload = curve.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(curve_payload)
            source_id = (
                curve.source_batch_fingerprint
                or curve.lineage.get("source_batch_fingerprint")
                or curve.page.request_scope_fingerprint
            )
            context_updates["transaction_cost_context"] = AuthoritativeTransactionCostContext(
                supportability_status=_source_status_to_method_status(curve.supportability.state),
                source_system="lotus-core",
                source_product_name=curve.product_name,
                source_product_version=curve.product_version,
                source_id=source_id,
                content_hash=source_hash,
                as_of_date=curve.as_of_date,
                window_start_date=curve.window.start_date,
                window_end_date=curve.window.end_date,
                returned_curve_point_count=curve.supportability.returned_curve_point_count,
                missing_security_ids=curve.supportability.missing_security_ids,
                curve_points=[
                    AuthoritativeTransactionCostPoint(
                        security_id=point.security_id,
                        transaction_type=point.transaction_type,
                        currency=point.currency,
                        observation_count=point.observation_count,
                        total_notional=point.total_notional,
                        total_cost=point.total_cost,
                        average_cost_bps=point.average_cost_bps,
                        min_cost_bps=point.min_cost_bps,
                        max_cost_bps=point.max_cost_bps,
                        first_observed_date=point.first_observed_date,
                        last_observed_date=point.last_observed_date,
                        sample_transaction_ids=point.sample_transaction_ids[:5],
                    )
                    for point in curve.curve_points[:10]
                ],
                reason_codes=[curve.supportability.reason],
            )
    if authority_context.liquidity_context is None:
        cashflow_projection = source_context.context.portfolio_cashflow_projection
        income_needs = getattr(source_context.context, "client_income_needs_schedule", None)
        reserve_requirement = getattr(source_context.context, "liquidity_reserve_requirement", None)
        planned_withdrawals = getattr(source_context.context, "planned_withdrawal_schedule", None)
        source_reason_codes = ["LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES"]
        cashflow_context = None
        income_context = None
        reserve_context = None
        withdrawal_context = None
        if (
            cashflow_projection is not None
            or income_needs is not None
            or reserve_requirement is not None
            or planned_withdrawals is not None
        ):
            source_reason_codes.append("CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT")
        if cashflow_projection is not None:
            payload = cashflow_projection.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            status = (
                cashflow_projection.data_quality_status
                if cashflow_projection.data_quality_status in {"READY", "DEGRADED", "INCOMPLETE"}
                else "READY"
            )
            cashflow_context = AuthoritativeLiquidityCashflowProjection(
                source_product_name=cashflow_projection.product_name,
                source_product_version=cashflow_projection.product_version,
                source_system="lotus-core",
                total_net_cashflow=Money(
                    amount=cashflow_projection.total_net_cashflow,
                    currency=cashflow_projection.portfolio_currency,
                ),
                projection_start=cashflow_projection.range_start_date,
                projection_end=cashflow_projection.range_end_date,
                include_projected=cashflow_projection.include_projected,
                latest_evidence_timestamp=cashflow_projection.latest_evidence_timestamp,
                source_batch_fingerprint=cashflow_projection.source_batch_fingerprint
                or cashflow_projection.lineage.get("source_batch_fingerprint")
                or source_hash,
                data_quality_status=_source_status_to_method_status(status),
                reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
            )
        if income_needs is not None:
            payload = income_needs.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            income_context = AuthoritativeClientIncomeNeedsSchedule(
                source_product_name=income_needs.product_name,
                source_product_version=income_needs.product_version,
                source_system="lotus-core",
                source_id=income_needs.source_batch_fingerprint
                or income_needs.lineage.get("source_batch_fingerprint")
                or source_hash,
                content_hash=source_hash,
                schedule_count=income_needs.supportability.schedule_count,
                currencies=sorted({entry.currency for entry in income_needs.schedules}),
                highest_priority=(
                    min(entry.priority for entry in income_needs.schedules)
                    if income_needs.schedules
                    else None
                ),
                supportability_status=_source_status_to_method_status(
                    income_needs.supportability.state
                ),
                reason_codes=[income_needs.supportability.reason, "CORE_INCOME_NEEDS_PRESENT"],
            )
            source_reason_codes.append("CLIENT_INCOME_NEEDS_SOURCE_PRESENT")
        if reserve_requirement is not None:
            payload = reserve_requirement.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            reserve_context = AuthoritativeLiquidityReserveRequirement(
                source_product_name=reserve_requirement.product_name,
                source_product_version=reserve_requirement.product_version,
                source_system="lotus-core",
                source_id=reserve_requirement.source_batch_fingerprint
                or reserve_requirement.lineage.get("source_batch_fingerprint")
                or source_hash,
                content_hash=source_hash,
                requirement_count=reserve_requirement.supportability.requirement_count,
                currencies=sorted({entry.currency for entry in reserve_requirement.requirements}),
                maximum_horizon_days=(
                    max(entry.horizon_days for entry in reserve_requirement.requirements)
                    if reserve_requirement.requirements
                    else None
                ),
                supportability_status=_source_status_to_method_status(
                    reserve_requirement.supportability.state
                ),
                reason_codes=[
                    reserve_requirement.supportability.reason,
                    "CORE_LIQUIDITY_RESERVE_PRESENT",
                ],
            )
            source_reason_codes.append("LIQUIDITY_RESERVE_SOURCE_PRESENT")
        if planned_withdrawals is not None:
            payload = planned_withdrawals.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            withdrawal_context = AuthoritativePlannedWithdrawalSchedule(
                source_product_name=planned_withdrawals.product_name,
                source_product_version=planned_withdrawals.product_version,
                source_system="lotus-core",
                source_id=planned_withdrawals.source_batch_fingerprint
                or planned_withdrawals.lineage.get("source_batch_fingerprint")
                or source_hash,
                content_hash=source_hash,
                withdrawal_count=planned_withdrawals.supportability.withdrawal_count,
                currencies=sorted({entry.currency for entry in planned_withdrawals.withdrawals}),
                horizon_days=planned_withdrawals.horizon_days,
                supportability_status=_source_status_to_method_status(
                    planned_withdrawals.supportability.state
                ),
                reason_codes=[
                    planned_withdrawals.supportability.reason,
                    "CORE_PLANNED_WITHDRAWALS_PRESENT",
                ],
            )
            source_reason_codes.append("PLANNED_WITHDRAWAL_SOURCE_PRESENT")
        if (
            cashflow_projection is not None
            or income_needs is not None
            or reserve_requirement is not None
            or planned_withdrawals is not None
        ):
            context_updates["liquidity_context"] = AuthoritativeLiquidityContext(
                supportability_status=ConstructionMethodStatus.READY,
                source_system="lotus-manage-settlement-engine",
                policy_id="manage-liquidity-policy.v1",
                minimum_cash_weight=Decimal("0.02"),
                allowed_liquidity_tiers=["L1", "L2", "L3"],
                cashflow_projection=cashflow_context,
                client_income_needs_schedule=income_context,
                liquidity_reserve_requirement=reserve_context,
                planned_withdrawal_schedule=withdrawal_context,
                reason_codes=source_reason_codes,
            )
    if authority_context.currency_overlay_context is None:
        hedge_readiness = getattr(
            source_context.context,
            "external_hedge_execution_readiness",
            None,
        )
        if hedge_readiness is not None:
            payload = hedge_readiness.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            context_updates["currency_overlay_context"] = AuthoritativeCurrencyOverlayContext(
                supportability_status=_source_status_to_method_status(
                    hedge_readiness.supportability.state
                ),
                source_system="lotus-core",
                policy_id="external-hedge-execution-readiness.v1",
                hedge_ratio_min=Decimal("0.00"),
                hedge_ratio_max=Decimal("0.00"),
                eligible_currencies=hedge_readiness.exposure_currencies,
                source_product_name=hedge_readiness.product_name,
                source_product_version=hedge_readiness.product_version,
                source_id=hedge_readiness.source_batch_fingerprint
                or hedge_readiness.lineage.get("source_batch_fingerprint")
                or source_hash,
                content_hash=source_hash,
                missing_data_families=hedge_readiness.supportability.missing_data_families,
                blocked_capabilities=hedge_readiness.supportability.blocked_capabilities,
                readiness_checks=hedge_readiness.readiness_checks,
                reason_codes=[
                    hedge_readiness.supportability.reason,
                    "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
                ],
            )
    if authority_context.client_restriction_context is None:
        restriction_profile = source_context.context.client_restriction_profile
        if restriction_profile is not None:
            payload = restriction_profile.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            context_updates["client_restriction_context"] = AuthoritativeClientRestrictionContext(
                supportability_status=_source_status_to_method_status(
                    restriction_profile.supportability.state
                ),
                source_system="lotus-core",
                source_product_name=restriction_profile.product_name,
                source_product_version=restriction_profile.product_version,
                source_id=restriction_profile.source_batch_fingerprint
                or restriction_profile.lineage.get("source_batch_fingerprint")
                or source_hash,
                content_hash=source_hash,
                portfolio_id=restriction_profile.portfolio_id,
                client_id=restriction_profile.client_id,
                mandate_id=restriction_profile.mandate_id,
                as_of_date=restriction_profile.as_of_date,
                restriction_count=restriction_profile.supportability.restriction_count,
                missing_data_families=restriction_profile.supportability.missing_data_families,
                restrictions=[
                    AuthoritativeClientRestrictionRule.model_validate(
                        rule.model_dump(mode="python")
                    )
                    for rule in restriction_profile.restrictions
                ],
                reason_codes=[restriction_profile.supportability.reason],
            )
    if authority_context.sustainability_preference_context is None:
        sustainability_profile = source_context.context.sustainability_preference_profile
        if sustainability_profile is not None:
            payload = sustainability_profile.model_dump(mode="json", exclude_none=True)
            source_hash = hash_canonical_payload(payload)
            context_updates["sustainability_preference_context"] = (
                AuthoritativeSustainabilityPreferenceContext(
                    supportability_status=_source_status_to_method_status(
                        sustainability_profile.supportability.state
                    ),
                    source_system="lotus-core",
                    source_product_name=sustainability_profile.product_name,
                    source_product_version=sustainability_profile.product_version,
                    source_id=sustainability_profile.source_batch_fingerprint
                    or sustainability_profile.lineage.get("source_batch_fingerprint")
                    or source_hash,
                    content_hash=source_hash,
                    portfolio_id=sustainability_profile.portfolio_id,
                    client_id=sustainability_profile.client_id,
                    mandate_id=sustainability_profile.mandate_id,
                    as_of_date=sustainability_profile.as_of_date,
                    preference_count=sustainability_profile.supportability.preference_count,
                    missing_data_families=sustainability_profile.supportability.missing_data_families,
                    preferences=[
                        AuthoritativeSustainabilityPreference.model_validate(
                            preference.model_dump(mode="python")
                        )
                        for preference in sustainability_profile.preferences
                    ],
                    reason_codes=[sustainability_profile.supportability.reason],
                )
            )
    if not context_updates:
        return authority_context
    return authority_context.model_copy(update=context_updates)


def _source_status_to_method_status(status: str) -> ConstructionMethodStatus:
    if status == "READY":
        return ConstructionMethodStatus.READY
    if status == "DEGRADED":
        return ConstructionMethodStatus.DEGRADED
    return ConstructionMethodStatus.BLOCKED


def _with_observed_transaction_cost_estimate(
    *,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> ConstructionAlternative:
    estimate = _observed_transaction_cost_estimate(result=result, context=context)
    if estimate is None:
        return alternative
    metrics = alternative.comparison_metrics.model_copy(
        update={"estimated_transaction_cost": estimate}
    )
    objective_trace = [
        *alternative.objective_trace,
        ConstructionObjectiveTerm(
            term=ConstructionTraceTerm.ESTIMATED_COST,
            value=estimate.amount,
            unit=estimate.currency,
            direction="lower_is_better",
            description=(
                "Source-observed transaction-cost bps applied to candidate trade notionals; "
                "not a predictive execution quote."
            ),
        ),
    ]
    constraint_trace = [
        *alternative.constraint_trace,
        ConstructionConstraintTrace(
            constraint=ConstructionTraceTerm.ESTIMATED_COST,
            status=_transaction_cost_status(result=result, context=context),
            source_family=ConstructionSourceFamily.TRANSACTION_COST,
            reason_codes=_transaction_cost_reason_codes(result=result, context=context),
            description=(
                "Observed TransactionCostCurve:v1 evidence supports cost-aware comparison only."
            ),
        ),
    ]
    return alternative.model_copy(
        update={
            "comparison_metrics": metrics,
            "objective_trace": objective_trace,
            "constraint_trace": constraint_trace,
        }
    )


def _observed_transaction_cost_estimate(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> Money | None:
    if context is None or context.supportability_status != ConstructionMethodStatus.READY:
        return None
    point_by_key = {
        (point.security_id, point.transaction_type): point for point in context.curve_points
    }
    total = Decimal("0")
    currency = result.before.total_value.currency
    matched = False
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent) or intent.notional_base is None:
            continue
        point = point_by_key.get((intent.instrument_id, intent.side))
        if point is None:
            continue
        matched = True
        total += abs(intent.notional_base.amount) * point.average_cost_bps / Decimal("10000")
    if not matched:
        return None
    return Money(amount=total.quantize(_MONEY_QUANT), currency=currency)


def _transaction_cost_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    traded_security_ids = {
        intent.instrument_id for intent in result.intents if isinstance(intent, SecurityTradeIntent)
    }
    covered_security_ids = {point.security_id for point in context.curve_points}
    if traded_security_ids and not traded_security_ids <= covered_security_ids:
        status = _lowest_status([status, ConstructionMethodStatus.DEGRADED])
    if _observed_transaction_cost_estimate(result=result, context=context) is None:
        status = _lowest_status([status, ConstructionMethodStatus.DEGRADED])
    return status


def _transaction_cost_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> list[str]:
    if context is None:
        return ["TRANSACTION_COST_CURVE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    traded_security_ids = {
        intent.instrument_id for intent in result.intents if isinstance(intent, SecurityTradeIntent)
    }
    covered_security_ids = {point.security_id for point in context.curve_points}
    missing_security_ids = sorted(traded_security_ids - covered_security_ids)
    if missing_security_ids:
        reason_codes.append("TRANSACTION_COST_CURVE_MISSING_TRADED_SECURITIES")
    if _observed_transaction_cost_estimate(result=result, context=context) is None:
        reason_codes.append("TRANSACTION_COST_ESTIMATE_UNAVAILABLE")
    else:
        reason_codes.append("TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS")
    return sorted(set(reason_codes))


def _with_esg_restriction_constraints(
    *,
    request: RebalanceRequest,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    return alternative.model_copy(
        update={
            "constraint_trace": [
                *alternative.constraint_trace,
                ConstructionConstraintTrace(
                    constraint=ConstructionTraceTerm.CLIENT_RESTRICTION,
                    status=_client_restriction_status(
                        request=request,
                        result=result,
                        context=authority_context.client_restriction_context,
                    ),
                    source_family=ConstructionSourceFamily.ESG_PROFILE,
                    reason_codes=_client_restriction_reason_codes(
                        request=request,
                        result=result,
                        context=authority_context.client_restriction_context,
                    ),
                    description=(
                        "Source-owned ClientRestrictionProfile:v1 evidence is applied to "
                        "candidate buy/sell intents when available."
                    ),
                ),
                ConstructionConstraintTrace(
                    constraint=ConstructionTraceTerm.SUSTAINABILITY_PREFERENCE,
                    status=_sustainability_preference_status(
                        result=result,
                        context=authority_context.sustainability_preference_context,
                    ),
                    source_family=ConstructionSourceFamily.ESG_PROFILE,
                    reason_codes=_sustainability_preference_reason_codes(
                        result=result,
                        context=authority_context.sustainability_preference_context,
                    ),
                    description=(
                        "Source-owned SustainabilityPreferenceProfile:v1 evidence is attached; "
                        "classification-dependent controls remain pending review when the "
                        "source profile alone is insufficient."
                    ),
                ),
            ]
        }
    )


def _esg_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    return _lowest_status(
        [
            _client_restriction_status(
                request=request,
                result=result,
                context=authority_context.client_restriction_context,
            ),
            _sustainability_preference_status(
                result=result,
                context=authority_context.sustainability_preference_context,
            ),
        ]
    )


def _esg_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    return sorted(
        set(
            _client_restriction_reason_codes(
                request=request,
                result=result,
                context=authority_context.client_restriction_context,
            )
            + _sustainability_preference_reason_codes(
                result=result,
                context=authority_context.sustainability_preference_context,
            )
        )
    )


def _client_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    if _violated_client_restrictions(request=request, result=result, context=context):
        return ConstructionMethodStatus.BLOCKED
    return status


def _client_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> list[str]:
    if context is None:
        return ["CLIENT_RESTRICTION_PROFILE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"CLIENT_RESTRICTION_PROFILE_{context.supportability_status}")
    reason_codes.extend(f"MISSING_{family.upper()}" for family in context.missing_data_families)
    violations = _violated_client_restrictions(request=request, result=result, context=context)
    if violations:
        reason_codes.extend(
            f"CLIENT_RESTRICTION_VIOLATION_{restriction.restriction_code}"
            for _, restriction in violations
        )
    else:
        reason_codes.append("CLIENT_RESTRICTION_PROFILE_APPLIED")
    return sorted(set(reason_codes))


def _violated_client_restrictions(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext,
) -> list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]]:
    shelf_by_instrument = {entry.instrument_id: entry for entry in request.shelf_entries}
    violations: list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]] = []
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent):
            continue
        for restriction in context.restrictions:
            if restriction.restriction_status.lower() != "active":
                continue
            if intent.side == "BUY" and not restriction.applies_to_buy:
                continue
            if intent.side == "SELL" and not restriction.applies_to_sell:
                continue
            if _restriction_matches_intent(
                intent=intent,
                shelf=shelf_by_instrument.get(intent.instrument_id),
                restriction=restriction,
            ):
                violations.append((intent, restriction))
    return violations


def _restriction_matches_intent(
    *,
    intent: SecurityTradeIntent,
    shelf: ShelfEntry | None,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    scoped_values = (
        restriction.instrument_ids
        or restriction.asset_classes
        or restriction.issuer_ids
        or restriction.country_codes
    )
    if not scoped_values:
        return True
    if intent.instrument_id in restriction.instrument_ids:
        return True
    if shelf is None:
        return False
    if shelf.asset_class in restriction.asset_classes:
        return True
    if shelf.issuer_id and shelf.issuer_id in restriction.issuer_ids:
        return True
    country_of_risk = shelf.attributes.get("country_of_risk") or shelf.attributes.get("country")
    return bool(country_of_risk and country_of_risk in restriction.country_codes)


def _sustainability_preference_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    if _sustainability_allocation_breaches(result=result, context=context):
        status = _lowest_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    if _sustainability_classification_review_required(context=context):
        status = _lowest_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    return status


def _sustainability_preference_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> list[str]:
    if context is None:
        return ["SUSTAINABILITY_PREFERENCE_PROFILE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"SUSTAINABILITY_PREFERENCE_PROFILE_{context.supportability_status}")
    reason_codes.extend(f"MISSING_{family.upper()}" for family in context.missing_data_families)
    breaches = _sustainability_allocation_breaches(result=result, context=context)
    reason_codes.extend(
        f"SUSTAINABILITY_ALLOCATION_REVIEW_{preference.preference_code}" for preference in breaches
    )
    if _sustainability_classification_review_required(context=context):
        reason_codes.append("SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED")
    if not breaches and not _sustainability_classification_review_required(context=context):
        reason_codes.append("SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED")
    return sorted(set(reason_codes))


def _sustainability_allocation_breaches(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> list[AuthoritativeSustainabilityPreference]:
    weight_by_asset_class = {
        allocation.key.lower(): allocation.weight
        for allocation in result.after_simulated.allocation_by_asset_class
    }
    breaches: list[AuthoritativeSustainabilityPreference] = []
    for preference in context.preferences:
        if preference.preference_status.lower() != "active":
            continue
        if not preference.applies_to_asset_classes:
            continue
        weight = sum(
            weight_by_asset_class.get(asset_class.lower(), Decimal("0"))
            for asset_class in preference.applies_to_asset_classes
        )
        if preference.minimum_allocation is not None and weight < preference.minimum_allocation:
            breaches.append(preference)
        if preference.maximum_allocation is not None and weight > preference.maximum_allocation:
            breaches.append(preference)
    return breaches


def _sustainability_classification_review_required(
    *,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> bool:
    return any(
        preference.preference_status.lower() == "active"
        and (preference.exclusion_codes or preference.positive_tilt_codes)
        for preference in context.preferences
    )


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


def _liquidity_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    if result.diagnostics.cash_ladder_breaches or result.diagnostics.insufficient_cash:
        return ConstructionMethodStatus.BLOCKED
    cash_weight = _post_trade_cash_weight(result=result)
    if cash_weight is not None and cash_weight < context.minimum_cash_weight:
        status = _lowest_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    if context.cashflow_projection is None:
        return status
    cashflow_status = context.cashflow_projection.data_quality_status
    if not context.cashflow_projection.include_projected:
        cashflow_status = _lowest_status([cashflow_status, ConstructionMethodStatus.DEGRADED])
    if (
        context.cashflow_projection.total_net_cashflow.currency
        != result.after_simulated.total_value.currency
    ):
        cashflow_status = _lowest_status([cashflow_status, ConstructionMethodStatus.DEGRADED])
    elif result.after_simulated.total_value.amount <= Decimal("0"):
        cashflow_status = _lowest_status([cashflow_status, ConstructionMethodStatus.DEGRADED])
    elif cash_weight is not None:
        projected_cash_weight = (
            context.cashflow_projection.total_net_cashflow.amount
            / result.after_simulated.total_value.amount
        )
        if cash_weight + projected_cash_weight < context.minimum_cash_weight:
            cashflow_status = _lowest_status(
                [cashflow_status, ConstructionMethodStatus.PENDING_REVIEW]
            )
    return _lowest_status([status, cashflow_status])


def _liquidity_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext | None,
) -> list[str]:
    reason_codes: list[str] = []
    if context is None:
        reason_codes.append("LIQUIDITY_POLICY_CONTEXT_DERIVED")
    else:
        reason_codes.extend(context.reason_codes)
        reason_codes.extend(_cashflow_projection_reason_codes(result=result, context=context))
    if result.diagnostics.cash_ladder:
        reason_codes.append("SETTLEMENT_CASH_LADDER_PRESENT")
    if result.diagnostics.cash_ladder_breaches:
        reason_codes.append("SETTLEMENT_CASH_LADDER_BREACH")
    if result.diagnostics.insufficient_cash:
        reason_codes.append("LIQUIDITY_FUNDING_DEFICIT")
    return reason_codes


def _cashflow_projection_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
) -> list[str]:
    projection = context.cashflow_projection
    if projection is None:
        return []
    reason_codes = ["CASHFLOW_PROJECTION_CONTEXT_PRESENT", *projection.reason_codes]
    is_usable = True
    if projection.data_quality_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"CASHFLOW_PROJECTION_{projection.data_quality_status}_BY_SOURCE")
        is_usable = False
    if not projection.include_projected:
        reason_codes.append("CASHFLOW_PROJECTION_PROJECTED_ROWS_NOT_INCLUDED")
        is_usable = False
    if projection.total_net_cashflow.currency != result.after_simulated.total_value.currency:
        reason_codes.append("CASHFLOW_PROJECTION_CURRENCY_MISMATCH")
        return reason_codes
    if result.after_simulated.total_value.amount <= Decimal("0"):
        reason_codes.append("CASHFLOW_PROJECTION_TOTAL_VALUE_UNAVAILABLE")
        return reason_codes
    cash_weight = _post_trade_cash_weight(result=result)
    if cash_weight is None:
        return reason_codes
    projected_cash_weight = (
        projection.total_net_cashflow.amount / result.after_simulated.total_value.amount
    )
    if cash_weight + projected_cash_weight < context.minimum_cash_weight:
        reason_codes.append("CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY")
    elif is_usable:
        reason_codes.append("CASHFLOW_PROJECTION_READY")
    return reason_codes


def _post_trade_cash_weight(*, result: RebalanceResult) -> Decimal | None:
    return next(
        (
            allocation.weight
            for allocation in result.after_simulated.allocation_by_asset_class
            if allocation.key == "CASH"
        ),
        None,
    )


def _derive_liquidity_context(*, result: RebalanceResult) -> AuthoritativeLiquidityContext:
    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="manage-liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1", "L2", "L3"],
        reason_codes=["LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES"],
    )


def _derive_currency_overlay_context(
    *,
    result: RebalanceResult,
) -> AuthoritativeCurrencyOverlayContext:
    non_base_currencies = sorted(
        {
            position.instrument_currency
            for position in result.after_simulated.positions
            if position.instrument_currency != result.after_simulated.total_value.currency
        }
    )
    return AuthoritativeCurrencyOverlayContext(
        supportability_status=(
            ConstructionMethodStatus.READY
            if non_base_currencies
            else ConstructionMethodStatus.DEGRADED
        ),
        source_system="lotus-manage-fx-policy",
        policy_id="manage-currency-overlay-policy.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("1.00"),
        eligible_currencies=non_base_currencies,
        reason_codes=["CURRENCY_OVERLAY_POLICY_DERIVED_FROM_MANAGE_FX_RULES"],
    )


def _construction_as_of_date(*, request: RebalanceRequest) -> date:
    snapshot_id = getattr(request.market_data_snapshot, "snapshot_id", "")
    for candidate in (
        snapshot_id or "",
        getattr(request.portfolio_snapshot, "snapshot_id", "") or "",
    ):
        match = _DATE_PATTERN.search(candidate)
        if match is not None:
            return date(
                year=int(match.group(1)),
                month=int(match.group(2)),
                day=int(match.group(3)),
            )
        try:
            return date.fromisoformat(candidate[:10])
        except ValueError:
            continue
    return datetime.now(timezone.utc).date()


def _currency_overlay_status(
    *,
    request: RebalanceRequest,
    context: AuthoritativeCurrencyOverlayContext | None,
) -> ConstructionMethodStatus:
    if _missing_currency_overlay_pairs(request=request):
        return ConstructionMethodStatus.BLOCKED
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if context.supportability_status != ConstructionMethodStatus.READY:
        return context.supportability_status
    base_currency = request.portfolio_snapshot.base_currency
    instrument_currencies = {
        price.currency
        for price in request.market_data_snapshot.prices
        if price.currency != base_currency
    }
    if instrument_currencies - set(context.eligible_currencies):
        return ConstructionMethodStatus.PENDING_REVIEW
    return (
        ConstructionMethodStatus.READY
        if instrument_currencies
        else ConstructionMethodStatus.DEGRADED
    )


def _regime_stress_status(
    context: AuthoritativeRegimeStressContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if context.worst_case_loss_pct > context.maximum_allowed_loss_pct:
        return ConstructionMethodStatus.PENDING_REVIEW
    return context.supportability_status


def _missing_currency_overlay_pairs(*, request: RebalanceRequest) -> list[str]:
    base_currency = request.portfolio_snapshot.base_currency
    available_pairs = {fx_rate.pair for fx_rate in request.market_data_snapshot.fx_rates}
    required_pairs = {
        f"{price.currency}/{base_currency}"
        for price in request.market_data_snapshot.prices
        if price.currency != base_currency
    }
    return sorted(required_pairs - available_pairs)


def _lowest_status(statuses: list[ConstructionMethodStatus]) -> ConstructionMethodStatus:
    status_order = {
        ConstructionMethodStatus.BLOCKED: 0,
        ConstructionMethodStatus.DEGRADED: 1,
        ConstructionMethodStatus.PENDING_REVIEW: 2,
        ConstructionMethodStatus.READY: 3,
    }
    return min(statuses, key=lambda item: status_order[item])
