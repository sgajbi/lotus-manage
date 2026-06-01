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
from src.api.services.construction_method_execution import (
    options_for_construction_method,
    run_construction_method,
)
from src.api.services.construction_method_authority import authority_context_for_method
from src.api.services.construction_method_readiness import (
    method_specific_reason_codes,
    method_specific_status,
)
from src.api.services.construction_solver_supportability import (
    solver_method_status,
    with_method_reason_codes,
)
from src.api.services.construction_source_analytics_posture import source_analytics_posture
from src.api.services.construction_source_product_context import (
    external_order_execution_acknowledgement_context,
    external_treasury_currency_overlay_context,
    source_status_to_method_status,
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
from src.core.construction.method_registry import resolve_method_plan
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
from src.core.models import EngineOptions, RebalanceResult
from src.core.models import Money, SecurityTradeIntent, ShelfEntry
from src.core.rebalance_runs.service import DpmRunSupportService
from src.api.request_models import RebalanceRequest
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
)

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
    return run_construction_method(
        request=request,
        method=method,
        correlation_id=correlation_id,
        request_hash=request_hash,
        run_service=run_service,
    )


def _options_for_method(
    *,
    options: EngineOptions,
    method: ConstructionMethod,
) -> EngineOptions:
    return options_for_construction_method(options=options, method=method)


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
    return method_specific_status(
        request=request,
        method=method,
        result=result,
        enrichment=enrichment,
        authority_context=authority_context,
    )


def _method_specific_reason_codes(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    enrichment: ConstructionEnrichmentSummary,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    return method_specific_reason_codes(
        request=request,
        method=method,
        result=result,
        authority_context=authority_context,
    )


def _source_analytics_posture(
    *,
    method: ConstructionMethod,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return source_analytics_posture(method=method, authority_context=authority_context)


def _authority_context_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    correlation_id: str | None,
) -> ConstructionAuthorityContext:
    return authority_context_for_method(
        request=request,
        method=method,
        result=result,
        authority_context=authority_context,
        risk_authority_client=risk_authority_client,
        correlation_id=correlation_id,
        as_of_date=_construction_as_of_date(request=request),
    )


def _external_treasury_currency_overlay_context(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> AuthoritativeCurrencyOverlayContext | None:
    return external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )


def _external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    return external_order_execution_acknowledgement_context(acknowledgement)


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
    return source_status_to_method_status(status)


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
    return with_method_reason_codes(enrichment=enrichment, reason_codes=reason_codes)


def _solver_method_status(*, result: RebalanceResult) -> ConstructionMethodStatus:
    return solver_method_status(result=result)


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
