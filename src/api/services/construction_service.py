from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import re
from typing import Optional

from src.api.services.construction_idempotency import (
    construction_request_hash,
    resolve_existing_construction_alternative_set,
)
from src.api.services.construction_method_supportability import (
    cashflow_projection_reason_codes,
    currency_overlay_status,
    derive_currency_overlay_context,
    derive_liquidity_context,
    liquidity_reason_codes,
    liquidity_status,
    missing_currency_overlay_pairs,
    post_trade_cash_weight,
    regime_stress_status,
)
from src.api.services.construction_esg_supportability import (
    client_restriction_reason_codes,
    client_restriction_status,
    esg_restriction_reason_codes,
    esg_restriction_status,
    restriction_matches_intent,
    sustainability_allocation_breaches,
    sustainability_classification_review_required,
    sustainability_preference_reason_codes,
    sustainability_preference_status,
    violated_client_restrictions,
    with_esg_restriction_constraints,
)
from src.api.services.construction_transaction_cost_supportability import (
    observed_transaction_cost_estimate,
    transaction_cost_reason_codes,
    transaction_cost_status,
    with_observed_transaction_cost_estimate,
)
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
    AuthoritativeExecutionAcknowledgementContext,
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
    ConstructionEnrichmentSummary,
    ConstructionMethodPlan,
)
from src.core.construction.repository import (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionRepository,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    FIRST_WAVE_CONSTRUCTION_METHODS,
)
from src.core.dpm_source_context import (
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmResolvedSourceContext,
)
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
    request_hash = construction_request_hash(
        request=request,
        methods=method_set,
        source_context=source_context,
    )
    existing = resolve_existing_construction_alternative_set(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if existing is not None:
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
                "source_analytics_posture": _source_analytics_posture(
                    method=method,
                    authority_context=authority_context,
                ),
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


def _source_analytics_posture(
    *,
    method: ConstructionMethod,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return {
        "product_family": "CONSTRUCTION_ALTERNATIVE_RISK_PERFORMANCE_CONTEXT",
        "risk_context_preservation": "SUPPORTED_WHEN_SUPPLIED",
        "performance_context_preservation": "SUPPORTED_WHEN_SUPPLIED",
        "risk_context_supplied": authority_context.risk_context is not None,
        "performance_context_supplied": authority_context.performance_context is not None,
        "risk_required_for_method": method == ConstructionMethod.RISK_AWARE,
        "performance_required_for_method": False,
        "required_source_products": [
            {
                "source_system": "lotus-risk",
                "source_product_name": "RiskMetricsReport",
                "source_product_version": "v1",
                "required_for_ready": method == ConstructionMethod.RISK_AWARE,
            },
            {
                "source_system": "lotus-risk",
                "source_product_name": "DrawdownAnalyticsReport",
                "source_product_version": "v1",
                "required_for_ready": False,
            },
            {
                "source_system": "lotus-risk",
                "source_product_name": "HistoricalRiskAttribution",
                "source_product_version": "v1",
                "required_for_ready": False,
            },
            {
                "source_system": "lotus-risk",
                "source_product_name": "RegimeScenarioPackEvaluation",
                "source_product_version": "v1",
                "required_for_ready": method == ConstructionMethod.REGIME_STRESS_AWARE,
            },
            {
                "source_system": "lotus-performance",
                "source_product_name": "BenchmarkExposureContext",
                "source_product_version": "v1",
                "required_for_ready": False,
            },
            {
                "source_system": "lotus-performance",
                "source_product_name": "ContributionAnalytics",
                "source_product_version": "v1",
                "required_for_ready": False,
            },
            {
                "source_system": "lotus-performance",
                "source_product_name": "AttributionAnalytics",
                "source_product_version": "v1",
                "required_for_ready": False,
            },
        ],
        "blocked_capabilities": [
            "LOCAL_TRACKING_ERROR_CALCULATION",
            "LOCAL_VOLATILITY_CALCULATION",
            "LOCAL_DRAWDOWN_CALCULATION",
            "LOCAL_STRESS_CONTRIBUTION_CALCULATION",
            "LOCAL_PERFORMANCE_ATTRIBUTION_CALCULATION",
            "LOCAL_BENCHMARK_RELATIVE_PERFORMANCE_CALCULATION",
        ],
        "reason_codes": [
            "SOURCE_ANALYTICS_CONTEXT_PRESERVED_WHEN_SUPPLIED",
            "RISK_PERFORMANCE_METHODOLOGY_REMAINS_SOURCE_OWNED",
        ],
    }


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
        execution_acknowledgement_context=authority_context.execution_acknowledgement_context,
        regime_stress_context=regime_context,
        client_restriction_context=authority_context.client_restriction_context,
        sustainability_preference_context=authority_context.sustainability_preference_context,
    )


def _external_treasury_currency_overlay_context(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> AuthoritativeCurrencyOverlayContext | None:
    if (
        hedge_readiness is None
        and currency_exposure is None
        and hedge_policy is None
        and eligible_hedge_instruments is None
        and fx_forward_curve is None
    ):
        return None

    readiness_payload = (
        hedge_readiness.model_dump(mode="json", exclude_none=True)
        if hedge_readiness is not None
        else None
    )
    exposure_payload = (
        currency_exposure.model_dump(mode="json", exclude_none=True)
        if currency_exposure is not None
        else None
    )
    hedge_policy_payload = (
        hedge_policy.model_dump(mode="json", exclude_none=True)
        if hedge_policy is not None
        else None
    )
    eligible_hedge_instruments_payload = (
        eligible_hedge_instruments.model_dump(mode="json", exclude_none=True)
        if eligible_hedge_instruments is not None
        else None
    )
    fx_forward_curve_payload = (
        fx_forward_curve.model_dump(mode="json", exclude_none=True)
        if fx_forward_curve is not None
        else None
    )
    source_hash = hash_canonical_payload(
        {
            "external_hedge_execution_readiness": readiness_payload,
            "external_currency_exposure": exposure_payload,
            "external_hedge_policy": hedge_policy_payload,
            "external_eligible_hedge_instruments": eligible_hedge_instruments_payload,
            "external_fx_forward_curve": fx_forward_curve_payload,
        }
    )
    if hedge_readiness is not None:
        supportability_state = hedge_readiness.supportability.state
        supportability_reason = hedge_readiness.supportability.reason
        exposure_currencies = hedge_readiness.exposure_currencies
    elif currency_exposure is not None:
        assert currency_exposure is not None
        supportability_state = currency_exposure.supportability.state
        supportability_reason = currency_exposure.supportability.reason
        exposure_currencies = currency_exposure.exposure_currencies
    elif hedge_policy is not None:
        assert hedge_policy is not None
        supportability_state = hedge_policy.supportability.state
        supportability_reason = hedge_policy.supportability.reason
        exposure_currencies = hedge_policy.exposure_currencies
    elif eligible_hedge_instruments is not None:
        assert eligible_hedge_instruments is not None
        supportability_state = eligible_hedge_instruments.supportability.state
        supportability_reason = eligible_hedge_instruments.supportability.reason
        exposure_currencies = eligible_hedge_instruments.exposure_currencies
    else:
        assert fx_forward_curve is not None
        supportability_state = fx_forward_curve.supportability.state
        supportability_reason = fx_forward_curve.supportability.reason
        exposure_currencies = fx_forward_curve.exposure_currencies

    exposure_source_hash = (
        hash_canonical_payload(exposure_payload) if exposure_payload is not None else None
    )
    hedge_policy_source_hash = (
        hash_canonical_payload(hedge_policy_payload) if hedge_policy_payload is not None else None
    )
    eligible_hedge_instruments_source_hash = (
        hash_canonical_payload(eligible_hedge_instruments_payload)
        if eligible_hedge_instruments_payload is not None
        else None
    )
    fx_forward_curve_source_hash = (
        hash_canonical_payload(fx_forward_curve_payload)
        if fx_forward_curve_payload is not None
        else None
    )
    readiness_missing = (
        hedge_readiness.supportability.missing_data_families if hedge_readiness is not None else []
    )
    exposure_missing = (
        currency_exposure.supportability.missing_data_families
        if currency_exposure is not None
        else []
    )
    hedge_policy_missing = (
        hedge_policy.supportability.missing_data_families if hedge_policy is not None else []
    )
    eligible_hedge_instruments_missing = (
        eligible_hedge_instruments.supportability.missing_data_families
        if eligible_hedge_instruments is not None
        else []
    )
    fx_forward_curve_missing = (
        fx_forward_curve.supportability.missing_data_families
        if fx_forward_curve is not None
        else []
    )
    readiness_blocked = (
        hedge_readiness.supportability.blocked_capabilities if hedge_readiness is not None else []
    )
    exposure_blocked = (
        currency_exposure.supportability.blocked_capabilities
        if currency_exposure is not None
        else []
    )
    hedge_policy_blocked = (
        hedge_policy.supportability.blocked_capabilities if hedge_policy is not None else []
    )
    eligible_hedge_instruments_blocked = (
        eligible_hedge_instruments.supportability.blocked_capabilities
        if eligible_hedge_instruments is not None
        else []
    )
    fx_forward_curve_blocked = (
        fx_forward_curve.supportability.blocked_capabilities if fx_forward_curve is not None else []
    )
    reason_codes: list[str] = [supportability_reason]
    if hedge_readiness is not None:
        reason_codes.append("EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED")
    if currency_exposure is not None:
        reason_codes.append("EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED")
    if hedge_policy is not None:
        reason_codes.append("EXTERNAL_HEDGE_POLICY_FAIL_CLOSED")
    if eligible_hedge_instruments is not None:
        reason_codes.append("EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED")
    if fx_forward_curve is not None:
        reason_codes.append("EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED")

    return AuthoritativeCurrencyOverlayContext(
        supportability_status=_source_status_to_method_status(supportability_state),
        source_system="lotus-core",
        policy_id="external-hedge-execution-readiness.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("0.00"),
        eligible_currencies=exposure_currencies,
        source_product_name=hedge_readiness.product_name if hedge_readiness is not None else None,
        source_product_version=(
            hedge_readiness.product_version if hedge_readiness is not None else None
        ),
        source_id=(
            hedge_readiness.source_batch_fingerprint
            or hedge_readiness.lineage.get("source_batch_fingerprint")
            or source_hash
            if hedge_readiness is not None
            else source_hash
        ),
        content_hash=source_hash,
        missing_data_families=sorted(
            {
                *readiness_missing,
                *exposure_missing,
                *hedge_policy_missing,
                *eligible_hedge_instruments_missing,
                *fx_forward_curve_missing,
            }
        ),
        blocked_capabilities=sorted(
            {
                *readiness_blocked,
                *exposure_blocked,
                *hedge_policy_blocked,
                *eligible_hedge_instruments_blocked,
                *fx_forward_curve_blocked,
            }
        ),
        readiness_checks=hedge_readiness.readiness_checks if hedge_readiness is not None else [],
        external_currency_exposure_source_product_name=(
            currency_exposure.product_name if currency_exposure is not None else None
        ),
        external_currency_exposure_source_product_version=(
            currency_exposure.product_version if currency_exposure is not None else None
        ),
        external_currency_exposure_source_id=(
            currency_exposure.source_batch_fingerprint
            or currency_exposure.lineage.get("source_batch_fingerprint")
            or exposure_source_hash
            if currency_exposure is not None
            else None
        ),
        external_currency_exposure_content_hash=exposure_source_hash,
        external_currency_exposure_count=(
            currency_exposure.supportability.exposure_count if currency_exposure is not None else 0
        ),
        external_currency_exposure_rows=(
            currency_exposure.exposures if currency_exposure is not None else []
        ),
        external_hedge_policy_source_product_name=(
            hedge_policy.product_name if hedge_policy is not None else None
        ),
        external_hedge_policy_source_product_version=(
            hedge_policy.product_version if hedge_policy is not None else None
        ),
        external_hedge_policy_source_id=(
            hedge_policy.source_batch_fingerprint
            or hedge_policy.lineage.get("source_batch_fingerprint")
            or hedge_policy_source_hash
            if hedge_policy is not None
            else None
        ),
        external_hedge_policy_content_hash=hedge_policy_source_hash,
        external_hedge_policy_rule_count=(
            hedge_policy.supportability.policy_rule_count if hedge_policy is not None else 0
        ),
        external_hedge_policy_rules=(hedge_policy.policy_rules if hedge_policy is not None else []),
        external_eligible_hedge_instrument_source_product_name=(
            eligible_hedge_instruments.product_name
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_source_product_version=(
            eligible_hedge_instruments.product_version
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_source_id=(
            eligible_hedge_instruments.source_batch_fingerprint
            or eligible_hedge_instruments.lineage.get("source_batch_fingerprint")
            or eligible_hedge_instruments_source_hash
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_content_hash=(eligible_hedge_instruments_source_hash),
        external_eligible_hedge_instrument_count=(
            eligible_hedge_instruments.supportability.instrument_count
            if eligible_hedge_instruments is not None
            else 0
        ),
        external_eligible_hedge_instruments=(
            eligible_hedge_instruments.eligible_instruments
            if eligible_hedge_instruments is not None
            else []
        ),
        external_fx_forward_curve_source_product_name=(
            fx_forward_curve.product_name if fx_forward_curve is not None else None
        ),
        external_fx_forward_curve_source_product_version=(
            fx_forward_curve.product_version if fx_forward_curve is not None else None
        ),
        external_fx_forward_curve_source_id=(
            fx_forward_curve.source_batch_fingerprint
            or fx_forward_curve.lineage.get("source_batch_fingerprint")
            or fx_forward_curve_source_hash
            if fx_forward_curve is not None
            else None
        ),
        external_fx_forward_curve_content_hash=fx_forward_curve_source_hash,
        external_fx_forward_curve_point_count=(
            fx_forward_curve.supportability.curve_point_count if fx_forward_curve is not None else 0
        ),
        external_fx_forward_curve_points=(
            fx_forward_curve.curve_points if fx_forward_curve is not None else []
        ),
        reason_codes=reason_codes,
    )


def _external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    if acknowledgement is None:
        return None
    payload = acknowledgement.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeExecutionAcknowledgementContext(
        supportability_status=_source_status_to_method_status(acknowledgement.supportability.state),
        source_system="lotus-core",
        source_product_name=acknowledgement.product_name,
        source_product_version=acknowledgement.product_version,
        source_id=(
            acknowledgement.source_batch_fingerprint
            or acknowledgement.lineage.get("source_batch_fingerprint")
            or source_hash
        ),
        content_hash=source_hash,
        acknowledgement_count=acknowledgement.supportability.acknowledgement_count,
        missing_data_families=acknowledgement.supportability.missing_data_families,
        blocked_capabilities=acknowledgement.supportability.blocked_capabilities,
        acknowledgements=acknowledgement.acknowledgements,
        reason_codes=[
            acknowledgement.supportability.reason,
            "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        ],
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
        currency_exposure = getattr(
            source_context.context,
            "external_currency_exposure",
            None,
        )
        hedge_policy = getattr(
            source_context.context,
            "external_hedge_policy",
            None,
        )
        eligible_hedge_instruments = getattr(
            source_context.context,
            "external_eligible_hedge_instruments",
            None,
        )
        fx_forward_curve = getattr(
            source_context.context,
            "external_fx_forward_curve",
            None,
        )
        currency_context = _external_treasury_currency_overlay_context(
            hedge_readiness=hedge_readiness,
            currency_exposure=currency_exposure,
            hedge_policy=hedge_policy,
            eligible_hedge_instruments=eligible_hedge_instruments,
            fx_forward_curve=fx_forward_curve,
        )
        if currency_context is not None:
            context_updates["currency_overlay_context"] = currency_context
    if authority_context.execution_acknowledgement_context is None:
        acknowledgement = getattr(
            source_context.context,
            "external_order_execution_acknowledgement",
            None,
        )
        acknowledgement_context = _external_order_execution_acknowledgement_context(acknowledgement)
        if acknowledgement_context is not None:
            context_updates["execution_acknowledgement_context"] = acknowledgement_context
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
    return with_observed_transaction_cost_estimate(
        alternative=alternative,
        result=result,
        context=context,
    )


def _observed_transaction_cost_estimate(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> Money | None:
    return observed_transaction_cost_estimate(result=result, context=context)


def _transaction_cost_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> ConstructionMethodStatus:
    return transaction_cost_status(result=result, context=context)


def _transaction_cost_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> list[str]:
    return transaction_cost_reason_codes(result=result, context=context)


def _with_esg_restriction_constraints(
    *,
    request: RebalanceRequest,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    return with_esg_restriction_constraints(
        request=request,
        alternative=alternative,
        result=result,
        authority_context=authority_context,
    )


def _esg_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    return esg_restriction_status(
        request=request,
        result=result,
        authority_context=authority_context,
    )


def _esg_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    return esg_restriction_reason_codes(
        request=request,
        result=result,
        authority_context=authority_context,
    )


def _client_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> ConstructionMethodStatus:
    return client_restriction_status(request=request, result=result, context=context)


def _client_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> list[str]:
    return client_restriction_reason_codes(request=request, result=result, context=context)


def _violated_client_restrictions(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext,
) -> list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]]:
    return violated_client_restrictions(request=request, result=result, context=context)


def _restriction_matches_intent(
    *,
    intent: SecurityTradeIntent,
    shelf: ShelfEntry | None,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    return restriction_matches_intent(intent=intent, shelf=shelf, restriction=restriction)


def _sustainability_preference_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> ConstructionMethodStatus:
    return sustainability_preference_status(result=result, context=context)


def _sustainability_preference_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> list[str]:
    return sustainability_preference_reason_codes(result=result, context=context)


def _sustainability_allocation_breaches(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> list[AuthoritativeSustainabilityPreference]:
    return sustainability_allocation_breaches(result=result, context=context)


def _sustainability_classification_review_required(
    *,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> bool:
    return sustainability_classification_review_required(context=context)


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
    return liquidity_status(result=result, context=context)


def _liquidity_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext | None,
) -> list[str]:
    return liquidity_reason_codes(result=result, context=context)


def _cashflow_projection_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
) -> list[str]:
    return cashflow_projection_reason_codes(result=result, context=context)


def _post_trade_cash_weight(*, result: RebalanceResult) -> Decimal | None:
    return post_trade_cash_weight(result=result)


def _derive_liquidity_context(*, result: RebalanceResult) -> AuthoritativeLiquidityContext:
    return derive_liquidity_context(result=result)


def _derive_currency_overlay_context(
    *,
    result: RebalanceResult,
) -> AuthoritativeCurrencyOverlayContext:
    return derive_currency_overlay_context(result=result)


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
    return currency_overlay_status(request=request, context=context)


def _regime_stress_status(
    context: AuthoritativeRegimeStressContext | None,
) -> ConstructionMethodStatus:
    return regime_stress_status(context)


def _missing_currency_overlay_pairs(*, request: RebalanceRequest) -> list[str]:
    return missing_currency_overlay_pairs(request=request)


def _lowest_status(statuses: list[ConstructionMethodStatus]) -> ConstructionMethodStatus:
    status_order = {
        ConstructionMethodStatus.BLOCKED: 0,
        ConstructionMethodStatus.DEGRADED: 1,
        ConstructionMethodStatus.PENDING_REVIEW: 2,
        ConstructionMethodStatus.READY: 3,
    }
    return min(statuses, key=lambda item: status_order[item])
