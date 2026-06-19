from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceEntry,
    DpmCoreSustainabilityPreferenceProfileResponse,
)
from src.core.mandate_models import (
    DIMENSION_WEIGHTS,
    DigitalTwinLineageSourceProduct as _DigitalTwinLineageSourceProduct,
    DpmCommandCenterAttentionBucket,
    DpmCommandCenterRecommendedAction,
    DpmCommandCenterSummary,
    DpmCommandCenterSupportability,
    DpmMandateConstraintSet,
    DpmMandateDimensionScore,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthReason,
    DpmMandateHealthSnapshot,
    DpmMandateHealthSourceAnalyticsPosture,
    DpmMandateHealthSourceProductRequirement,
    DpmMandatePreferences,
    DpmMandateReviewPolicy,
    DpmMandateSourceHealthContext,
    DpmMonitoringException,
    DpmMonitoringRun,
    DpmSourceProductLineage,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    MandateSourceReadinessProjection as _MandateSourceReadinessProjection,
    MonitoringSeverity,
    SourceReadinessState as _SourceReadinessState,
    bounded_ratio as _bounded_ratio,
    default_source_analytics_posture as _default_source_analytics_posture,
)

__all__ = [
    "DIMENSION_WEIGHTS",
    "DpmCommandCenterAttentionBucket",
    "DpmCommandCenterRecommendedAction",
    "DpmCommandCenterSummary",
    "DpmCommandCenterSupportability",
    "DpmMandateConstraintSet",
    "DpmMandateDimensionScore",
    "DpmMandateDigitalTwin",
    "DpmMandateHealthInput",
    "DpmMandateHealthReason",
    "DpmMandateHealthSnapshot",
    "DpmMandateHealthSourceAnalyticsPosture",
    "DpmMandateHealthSourceProductRequirement",
    "DpmMandatePreferences",
    "DpmMandateReviewPolicy",
    "DpmMandateSourceHealthContext",
    "DpmMonitoringException",
    "DpmMonitoringRun",
    "DpmSourceProductLineage",
    "MandateHealthDimension",
    "MandateHealthState",
    "MandateRecommendedAction",
    "MonitoringSeverity",
    "_DigitalTwinLineageSourceProduct",
    "_MandateSourceReadinessProjection",
    "_SourceReadinessState",
    "_bounded_ratio",
    "_default_source_analytics_posture",
    "build_health_input_from_core_sources",
    "calculate_mandate_health",
    "compile_mandate_digital_twin_from_core",
    "monitoring_exceptions_from_health",
]


def _score_from_penalty(penalty: Decimal) -> int:
    bounded_penalty = min(max(penalty, Decimal("0")), Decimal("100"))
    return int((Decimal("100") - bounded_penalty).quantize(Decimal("1"), ROUND_HALF_UP))


def _mandate_twin_field_gap_codes(
    *,
    mandate: DpmCoreMandateBindingResponse,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse],
    sustainability_preference_profile: Optional[DpmCoreSustainabilityPreferenceProfileResponse],
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse],
    client_income_needs_schedule: Optional[DpmCoreClientIncomeNeedsScheduleResponse],
    liquidity_reserve_requirement: Optional[DpmCoreLiquidityReserveRequirementResponse],
    planned_withdrawal_schedule: Optional[DpmCorePlannedWithdrawalScheduleResponse],
    benchmark_assignment: Optional[DpmCoreBenchmarkAssignmentResponse],
) -> list[str]:
    field_gaps = _mandate_source_schedule_gap_codes(
        client_income_needs_schedule=client_income_needs_schedule,
        liquidity_reserve_requirement=liquidity_reserve_requirement,
        planned_withdrawal_schedule=planned_withdrawal_schedule,
    )
    field_gaps.extend(_mandate_binding_profile_gap_codes(mandate))
    field_gaps.extend(
        _mandate_optional_source_product_gap_codes(
            client_restriction_profile=client_restriction_profile,
            sustainability_preference_profile=sustainability_preference_profile,
            portfolio_cashflow_projection=portfolio_cashflow_projection,
            benchmark_assignment=benchmark_assignment,
        )
    )
    return field_gaps


def _mandate_source_schedule_gap_codes(
    *,
    client_income_needs_schedule: Optional[DpmCoreClientIncomeNeedsScheduleResponse],
    liquidity_reserve_requirement: Optional[DpmCoreLiquidityReserveRequirementResponse],
    planned_withdrawal_schedule: Optional[DpmCorePlannedWithdrawalScheduleResponse],
) -> list[str]:
    field_gaps = []
    if client_income_needs_schedule is None:
        field_gaps.append("CLIENT_INCOME_NEED_PROFILE_NOT_YET_SOURCED")
    if liquidity_reserve_requirement is None:
        field_gaps.append("LIQUIDITY_RESERVE_REQUIREMENT_NOT_YET_SOURCED")
    if planned_withdrawal_schedule is None:
        field_gaps.append("PLANNED_WITHDRAWAL_SCHEDULE_NOT_YET_SOURCED")
    return field_gaps


def _mandate_binding_profile_gap_codes(
    mandate: DpmCoreMandateBindingResponse,
) -> list[str]:
    field_gaps = []
    if not mandate.mandate_objective:
        field_gaps.append("MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED")
    if not mandate.review_cadence or mandate.next_review_due_date is None:
        field_gaps.append("MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED")
    return field_gaps


def _mandate_optional_source_product_gap_codes(
    *,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse],
    sustainability_preference_profile: Optional[DpmCoreSustainabilityPreferenceProfileResponse],
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse],
    benchmark_assignment: Optional[DpmCoreBenchmarkAssignmentResponse],
) -> list[str]:
    field_gaps = []
    if client_restriction_profile is None:
        field_gaps.append("CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED")
    if sustainability_preference_profile is None:
        field_gaps.append("SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED")
    if portfolio_cashflow_projection is None:
        field_gaps.append("PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED")
    if benchmark_assignment is None:
        field_gaps.append("BENCHMARK_ASSIGNMENT_NOT_YET_SOURCED")
    return field_gaps


def _build_digital_twin_source_lineage(
    *,
    mandate: DpmCoreMandateBindingResponse,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse] = None,
    sustainability_preference_profile: Optional[
        DpmCoreSustainabilityPreferenceProfileResponse
    ] = None,
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse] = None,
    client_income_needs_schedule: Optional[DpmCoreClientIncomeNeedsScheduleResponse] = None,
    liquidity_reserve_requirement: Optional[DpmCoreLiquidityReserveRequirementResponse] = None,
    planned_withdrawal_schedule: Optional[DpmCorePlannedWithdrawalScheduleResponse] = None,
    benchmark_assignment: Optional[DpmCoreBenchmarkAssignmentResponse] = None,
) -> list[DpmSourceProductLineage]:
    source_lineage = _required_digital_twin_source_lineage(
        mandate=mandate,
        model_targets=model_targets,
    )
    source_lineage.extend(
        _optional_digital_twin_source_lineage(
            client_restriction_profile,
            sustainability_preference_profile,
            portfolio_cashflow_projection,
            client_income_needs_schedule,
            liquidity_reserve_requirement,
            planned_withdrawal_schedule,
        )
    )
    if benchmark_assignment is not None:
        source_lineage.append(_benchmark_assignment_source_lineage(benchmark_assignment))
    return source_lineage


def _required_digital_twin_source_lineage(
    *,
    mandate: DpmCoreMandateBindingResponse,
    model_targets: DpmCoreModelPortfolioTargetResponse,
) -> list[DpmSourceProductLineage]:
    return [
        _lineage_from_core_source_product(mandate),
        _lineage_from_core_source_product(model_targets),
    ]


def _optional_digital_twin_source_lineage(
    *products: _DigitalTwinLineageSourceProduct | None,
) -> list[DpmSourceProductLineage]:
    return [
        _lineage_from_core_source_product(product) for product in products if product is not None
    ]


def _lineage_from_core_source_product(
    product: _DigitalTwinLineageSourceProduct,
) -> DpmSourceProductLineage:
    return _lineage_from_core_product(
        product_name=product.product_name,
        product_version=product.product_version,
        lineage=product.lineage,
        data_quality_status=product.data_quality_status,
        latest_evidence_timestamp=product.latest_evidence_timestamp,
    )


def _benchmark_assignment_source_lineage(
    benchmark_assignment: DpmCoreBenchmarkAssignmentResponse,
) -> DpmSourceProductLineage:
    return DpmSourceProductLineage(
        product_name=benchmark_assignment.product_name,
        product_version=benchmark_assignment.product_version,
        source_system=benchmark_assignment.source_system or "lotus-core",
        source_record_id=_benchmark_assignment_source_record_id(benchmark_assignment),
        data_quality_status=benchmark_assignment.data_quality_status,
        latest_evidence_timestamp=benchmark_assignment.latest_evidence_timestamp,
        lineage={"contract_version": benchmark_assignment.contract_version},
    )


def _benchmark_assignment_source_record_id(
    benchmark_assignment: DpmCoreBenchmarkAssignmentResponse,
) -> str:
    return (
        f"{benchmark_assignment.portfolio_id}:"
        f"{benchmark_assignment.benchmark_id}:"
        f"{benchmark_assignment.effective_from.isoformat()}:"
        f"{benchmark_assignment.assignment_version}"
    )


def _mandate_twin_constraint_set(
    *,
    mandate: DpmCoreMandateBindingResponse,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse],
) -> DpmMandateConstraintSet:
    cash_reserve_weight = mandate.rebalance_bands.cash_reserve_weight or Decimal("0")
    constraints = DpmMandateConstraintSet(
        cash_band_min_weight=cash_reserve_weight,
        cash_band_max_weight=max(cash_reserve_weight, Decimal("0.10")),
        turnover_budget=Decimal("0.15"),
    )
    if client_restriction_profile is not None:
        constraints.restricted_instruments = _active_restricted_instruments(
            client_restriction_profile
        )
    return constraints


def _active_restricted_instruments(
    client_restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> list[str]:
    return sorted(
        {
            instrument_id
            for restriction in client_restriction_profile.restrictions
            if restriction.restriction_status.upper() == "ACTIVE"
            for instrument_id in restriction.instrument_ids
        }
    )


def _mandate_twin_preferences(
    sustainability_preference_profile: Optional[DpmCoreSustainabilityPreferenceProfileResponse],
) -> DpmMandatePreferences:
    preferences = DpmMandatePreferences()
    if sustainability_preference_profile is not None:
        preferences.sustainability_strategy = _sustainability_strategy(
            sustainability_preference_profile
        )
        preferences.bespoke_notes = [
            preference.preference_code
            for preference in sustainability_preference_profile.preferences
            if preference.preference_status.upper() == "ACTIVE"
        ]
    return preferences


def compile_mandate_digital_twin_from_core(
    *,
    mandate: DpmCoreMandateBindingResponse,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    as_of_date: date,
    reference_currency: Optional[str] = None,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse] = None,
    sustainability_preference_profile: Optional[
        DpmCoreSustainabilityPreferenceProfileResponse
    ] = None,
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse] = None,
    client_income_needs_schedule: Optional[DpmCoreClientIncomeNeedsScheduleResponse] = None,
    liquidity_reserve_requirement: Optional[DpmCoreLiquidityReserveRequirementResponse] = None,
    planned_withdrawal_schedule: Optional[DpmCorePlannedWithdrawalScheduleResponse] = None,
    benchmark_assignment: Optional[DpmCoreBenchmarkAssignmentResponse] = None,
) -> DpmMandateDigitalTwin:
    """Compile the minimum viable mandate twin from current RFC-087 core products."""

    field_gaps = _mandate_twin_field_gap_codes(
        mandate=mandate,
        client_restriction_profile=client_restriction_profile,
        sustainability_preference_profile=sustainability_preference_profile,
        portfolio_cashflow_projection=portfolio_cashflow_projection,
        client_income_needs_schedule=client_income_needs_schedule,
        liquidity_reserve_requirement=liquidity_reserve_requirement,
        planned_withdrawal_schedule=planned_withdrawal_schedule,
        benchmark_assignment=benchmark_assignment,
    )
    constraints = _mandate_twin_constraint_set(
        mandate=mandate,
        client_restriction_profile=client_restriction_profile,
    )
    preferences = _mandate_twin_preferences(sustainability_preference_profile)
    source_lineage = _build_digital_twin_source_lineage(
        mandate=mandate,
        model_targets=model_targets,
        client_restriction_profile=client_restriction_profile,
        sustainability_preference_profile=sustainability_preference_profile,
        portfolio_cashflow_projection=portfolio_cashflow_projection,
        client_income_needs_schedule=client_income_needs_schedule,
        liquidity_reserve_requirement=liquidity_reserve_requirement,
        planned_withdrawal_schedule=planned_withdrawal_schedule,
        benchmark_assignment=benchmark_assignment,
    )
    return DpmMandateDigitalTwin(
        mandate_id=mandate.mandate_id,
        portfolio_id=mandate.portfolio_id,
        mandate_version=str(mandate.binding_version),
        as_of_date=as_of_date,
        base_currency=model_targets.base_currency,
        reference_currency=reference_currency or model_targets.base_currency,
        risk_profile=mandate.risk_profile.upper(),
        investment_objective=mandate.mandate_objective or "LONG_TERM_TOTAL_RETURN",
        time_horizon=mandate.investment_horizon.upper(),
        model_portfolio_id=mandate.model_portfolio_id,
        model_portfolio_version=model_targets.model_portfolio_version,
        benchmark_id=(
            benchmark_assignment.benchmark_id if benchmark_assignment is not None else None
        ),
        constraints=constraints,
        preferences=preferences,
        review_policy=DpmMandateReviewPolicy(
            review_frequency=(mandate.review_cadence or mandate.rebalance_frequency).upper(),
            last_review_date=mandate.last_review_date,
            next_review_due_date=mandate.next_review_due_date,
        ),
        source_lineage=source_lineage,
        field_gap_codes=field_gaps,
    )


def _market_data_source_readiness(
    market_data_coverage: Optional[DpmCoreMarketDataCoverageWindowResponse],
) -> _MandateSourceReadinessProjection:
    if market_data_coverage is None:
        return _MandateSourceReadinessProjection(
            state="READY",
            missing_source_families=[],
            degraded_source_families=[],
            stale_source_families=[],
        )
    supportability = market_data_coverage.supportability
    degraded_sources = ["MARKET_DATA_COVERAGE"] if supportability.state == "DEGRADED" else []
    return _MandateSourceReadinessProjection(
        state=supportability.state,
        missing_source_families=[
            *supportability.missing_instrument_ids,
            *supportability.missing_currency_pairs,
        ],
        degraded_source_families=degraded_sources,
        stale_source_families=[
            *supportability.stale_instrument_ids,
            *supportability.stale_currency_pairs,
        ],
    )


def _health_input_source_readiness(
    *,
    market_data_coverage: Optional[DpmCoreMarketDataCoverageWindowResponse],
    unavailable_source_families: Optional[list[str]],
) -> _MandateSourceReadinessProjection:
    market_data_readiness = _market_data_source_readiness(market_data_coverage)
    unavailable_families = unavailable_source_families or []
    state = market_data_readiness.state
    if unavailable_families and state == "READY":
        state = "DEGRADED"
    return _MandateSourceReadinessProjection(
        state=state,
        missing_source_families=market_data_readiness.missing_source_families,
        degraded_source_families=[
            *market_data_readiness.degraded_source_families,
            *unavailable_families,
        ],
        stale_source_families=market_data_readiness.stale_source_families,
    )


def build_health_input_from_core_sources(
    *,
    twin: DpmMandateDigitalTwin,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    market_data_coverage: Optional[DpmCoreMarketDataCoverageWindowResponse] = None,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse] = None,
    sustainability_preference_profile: Optional[
        DpmCoreSustainabilityPreferenceProfileResponse
    ] = None,
    portfolio_cashflow_projection: Optional[DpmCorePortfolioCashflowProjectionResponse] = None,
    unavailable_source_families: Optional[list[str]] = None,
) -> DpmMandateHealthInput:
    source_readiness = _health_input_source_readiness(
        market_data_coverage=market_data_coverage,
        unavailable_source_families=unavailable_source_families,
    )

    return DpmMandateHealthInput(
        twin=twin,
        target_weights={
            target.instrument_id: target.target_weight for target in model_targets.targets
        },
        source_readiness_state=source_readiness.state,
        missing_source_families=source_readiness.missing_source_families,
        degraded_source_families=source_readiness.degraded_source_families,
        stale_source_families=source_readiness.stale_source_families,
        restricted_target_instruments=_restricted_model_targets(
            model_targets=model_targets,
            client_restriction_profile=client_restriction_profile,
        ),
        sustainability_review_required=_requires_sustainability_review(
            sustainability_preference_profile
        ),
        projected_net_cashflow=(
            portfolio_cashflow_projection.total_net_cashflow
            if portfolio_cashflow_projection is not None
            else None
        ),
        projected_cashflow_currency=(
            portfolio_cashflow_projection.portfolio_currency
            if portfolio_cashflow_projection is not None
            else None
        ),
        model_effective_to=model_targets.effective_to,
    )


def calculate_mandate_health(input_: DpmMandateHealthInput) -> DpmMandateHealthSnapshot:
    dimension_scores = _mandate_health_dimension_scores(input_)
    health_state = _mandate_health_state(dimension_scores)
    top_reasons = _top_mandate_health_reasons(dimension_scores)
    recommended_action = _overall_recommended_action(health_state, top_reasons)
    return DpmMandateHealthSnapshot(
        health_snapshot_id=_mandate_health_snapshot_id(input_),
        mandate_id=input_.twin.mandate_id,
        portfolio_id=input_.twin.portfolio_id,
        as_of_date=input_.twin.as_of_date,
        calculated_at=datetime.now(timezone.utc),
        health_score=_weighted_mandate_health_score(dimension_scores),
        health_state=health_state,
        dimension_scores=dimension_scores,
        top_reasons=top_reasons,
        recommended_action=recommended_action,
        source_readiness_state=input_.source_readiness_state,
        evidence_refs=_mandate_health_evidence_refs(input_),
        source_analytics_posture=_source_analytics_posture(input_),
    )


def _mandate_health_dimension_scores(
    input_: DpmMandateHealthInput,
) -> list[DpmMandateDimensionScore]:
    return [
        _score_source_readiness(input_),
        _score_allocation_drift(input_),
        _score_risk_drift(input_),
        _score_cash_liquidity(input_),
        _score_tax_turnover(input_),
        _score_eligibility_restrictions(input_),
        _score_performance_attention(input_),
        _score_workflow_readiness(input_),
        _score_review_cadence(input_),
        _score_model_freshness(input_),
    ]


def _weighted_mandate_health_score(
    dimension_scores: list[DpmMandateDimensionScore],
) -> int:
    weighted = sum(
        Decimal(score.score) * Decimal(score.weight) for score in dimension_scores
    ) / Decimal("100")
    return int(weighted.quantize(Decimal("1"), ROUND_HALF_UP))


def _mandate_health_state(
    dimension_scores: list[DpmMandateDimensionScore],
) -> MandateHealthState:
    if any(score.state == MandateHealthState.BLOCKED for score in dimension_scores):
        return MandateHealthState.BLOCKED
    if any(score.state == MandateHealthState.PENDING_REVIEW for score in dimension_scores):
        return MandateHealthState.PENDING_REVIEW
    return MandateHealthState.READY


def _top_mandate_health_reasons(
    dimension_scores: list[DpmMandateDimensionScore],
) -> list[DpmMandateHealthReason]:
    reasons = [_reason_from_score(score) for score in dimension_scores if score.score < 100]
    reasons.sort(key=lambda reason: _severity_rank(reason.severity), reverse=True)
    return reasons[:5]


def _mandate_health_snapshot_id(input_: DpmMandateHealthInput) -> str:
    as_of = input_.twin.as_of_date.strftime("%Y%m%d")
    return f"mh_{as_of}_{input_.twin.portfolio_id.lower()}"


def _mandate_health_evidence_refs(input_: DpmMandateHealthInput) -> list[str]:
    return [
        lineage.source_record_id
        for lineage in input_.twin.source_lineage
        if lineage.source_record_id
    ]


def _source_analytics_posture(
    input_: DpmMandateHealthInput,
) -> DpmMandateHealthSourceAnalyticsPosture:
    source_context_refs = []
    reason_codes = list(_default_source_analytics_posture().reason_codes)
    if input_.risk_health_context is not None:
        source_context_refs.append(_source_health_context_ref(input_.risk_health_context))
        reason_codes.append("MANDATE_RISK_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED")
    if input_.performance_health_context is not None:
        source_context_refs.append(_source_health_context_ref(input_.performance_health_context))
        reason_codes.append("MANDATE_PERFORMANCE_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED")
    return _default_source_analytics_posture().model_copy(
        update={
            "risk_tracking_error_supplied": input_.tracking_error is not None
            or input_.risk_health_context is not None,
            "performance_attention_signal_supplied": input_.performance_under_review
            or input_.performance_health_context is not None,
            "risk_health_context_supplied": input_.risk_health_context is not None,
            "performance_health_context_supplied": input_.performance_health_context is not None,
            "source_context_refs": source_context_refs,
            "reason_codes": reason_codes,
        }
    )


def _source_health_context_ref(context: DpmMandateSourceHealthContext) -> str:
    return (
        f"{context.source_system}:{context.source_product_name}:"
        f"{context.source_product_version}:{context.request_fingerprint}"
    )


def monitoring_exceptions_from_health(
    snapshot: DpmMandateHealthSnapshot,
    *,
    source_lineage: list[DpmSourceProductLineage],
) -> list[DpmMonitoringException]:
    detected_at = snapshot.calculated_at
    exceptions: list[DpmMonitoringException] = []
    for reason in snapshot.top_reasons:
        exceptions.append(
            DpmMonitoringException(
                exception_id=(
                    f"me_{snapshot.as_of_date.strftime('%Y%m%d')}_"
                    f"{snapshot.portfolio_id.lower()}_{reason.dimension.value.lower()}"
                ),
                mandate_id=snapshot.mandate_id,
                portfolio_id=snapshot.portfolio_id,
                detected_at=detected_at,
                as_of_date=snapshot.as_of_date,
                dimension=reason.dimension,
                severity=reason.severity,
                reason_code=reason.reason_code,
                recommended_action=reason.recommended_action,
                source_lineage=source_lineage,
            )
        )
    return exceptions


def _lineage_from_core_product(
    *,
    product_name: str,
    product_version: str,
    lineage: dict[str, str],
    data_quality_status: Optional[str],
    latest_evidence_timestamp: Optional[datetime],
) -> DpmSourceProductLineage:
    return DpmSourceProductLineage(
        product_name=product_name,
        product_version=product_version,
        source_record_id=lineage.get("source_record_id") or lineage.get("contract_version"),
        lineage=lineage,
        data_quality_status=data_quality_status,
        latest_evidence_timestamp=latest_evidence_timestamp,
    )


def _sustainability_strategy(
    profile: DpmCoreSustainabilityPreferenceProfileResponse,
) -> Optional[str]:
    active_frameworks = sorted(
        {
            preference.preference_framework
            for preference in profile.preferences
            if preference.preference_status.upper() == "ACTIVE"
        }
    )
    if not active_frameworks:
        return None
    return "+".join(active_frameworks)


def _restricted_model_targets(
    *,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    client_restriction_profile: Optional[DpmCoreClientRestrictionProfileResponse],
) -> list[str]:
    if client_restriction_profile is None:
        return []
    restricted_instruments = _restricted_buy_instrument_ids(client_restriction_profile)
    active_targets = _active_model_target_instrument_ids(model_targets)
    return sorted(active_targets.intersection(restricted_instruments))


def _restricted_buy_instrument_ids(
    client_restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> set[str]:
    return {
        instrument_id
        for restriction in client_restriction_profile.restrictions
        if _active_buy_restriction_applies(restriction)
        for instrument_id in restriction.instrument_ids
    }


def _active_buy_restriction_applies(restriction: DpmCoreClientRestrictionEntry) -> bool:
    return restriction.restriction_status.upper() == "ACTIVE" and restriction.applies_to_buy


def _active_model_target_instrument_ids(
    model_targets: DpmCoreModelPortfolioTargetResponse,
) -> set[str]:
    return {
        target.instrument_id
        for target in model_targets.targets
        if target.target_status.lower() == "active"
    }


def _requires_sustainability_review(
    profile: Optional[DpmCoreSustainabilityPreferenceProfileResponse],
) -> bool:
    if profile is None:
        return False
    return any(
        _active_sustainability_preference_requires_review(preference)
        for preference in profile.preferences
    )


def _active_sustainability_preference_requires_review(
    preference: DpmCoreSustainabilityPreferenceEntry,
) -> bool:
    return _sustainability_preference_is_active(
        preference
    ) and _sustainability_preference_has_review_controls(preference)


def _sustainability_preference_is_active(
    preference: DpmCoreSustainabilityPreferenceEntry,
) -> bool:
    return preference.preference_status.upper() == "ACTIVE"


def _sustainability_preference_has_review_controls(
    preference: DpmCoreSustainabilityPreferenceEntry,
) -> bool:
    return (
        preference.minimum_allocation is not None
        or preference.maximum_allocation is not None
        or bool(preference.exclusion_codes)
        or bool(preference.positive_tilt_codes)
    )


def _ready_score(dimension: MandateHealthDimension) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=100,
        state=MandateHealthState.READY,
        reason_code=f"{dimension.value}_READY",
    )


def _attention_score(
    *,
    dimension: MandateHealthDimension,
    score: int,
    state: MandateHealthState,
    reason_code: str,
    measured_value: Optional[Decimal | str | int] = None,
    threshold_value: Optional[Decimal | str | int] = None,
    evidence_refs: Optional[list[str]] = None,
) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=max(0, min(score, 100)),
        state=state,
        reason_code=reason_code,
        measured_value=measured_value,
        threshold_value=threshold_value,
        evidence_refs=evidence_refs or [],
    )


def _score_source_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if (
        input_.source_readiness_state in {"INCOMPLETE", "UNAVAILABLE"}
        or input_.missing_source_families
    ):
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="DPM_SOURCE_INCOMPLETE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    if input_.source_readiness_state == "DEGRADED" or input_.stale_source_families:
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="DPM_SOURCE_STALE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    return _ready_score(MandateHealthDimension.SOURCE_READINESS)


def _score_allocation_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if not input_.current_weights or not input_.target_weights:
        return _attention_score(
            dimension=MandateHealthDimension.ALLOCATION_DRIFT,
            score=85,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="ALLOCATION_DRIFT_NOT_ASSESSED",
        )
    default_band = Decimal("0.025")
    max_drift = max(
        (
            abs(input_.current_weights.get(instrument_id, Decimal("0")) - target_weight)
            for instrument_id, target_weight in input_.target_weights.items()
        ),
        default=Decimal("0"),
    )
    if max_drift <= default_band:
        return _ready_score(MandateHealthDimension.ALLOCATION_DRIFT)
    score = _score_from_penalty((max_drift - default_band) * Decimal("1000"))
    return _attention_score(
        dimension=MandateHealthDimension.ALLOCATION_DRIFT,
        score=score,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="ALLOCATION_DRIFT",
        measured_value=max_drift,
        threshold_value=default_band,
    )


def _score_risk_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    source_score = _score_source_health_context(
        context=input_.risk_health_context,
        dimension=MandateHealthDimension.RISK_DRIFT,
        attention_reason_code="SOURCE_RISK_HEALTH_ATTENTION",
        unavailable_reason_code="SOURCE_RISK_HEALTH_UNAVAILABLE",
    )
    if source_score is not None:
        return source_score
    if input_.tracking_error is None or input_.twin.constraints.max_tracking_error is None:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    if input_.tracking_error <= input_.twin.constraints.max_tracking_error:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    return _attention_score(
        dimension=MandateHealthDimension.RISK_DRIFT,
        score=65,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="TRACKING_ERROR_ABOVE_LIMIT",
        measured_value=input_.tracking_error,
        threshold_value=input_.twin.constraints.max_tracking_error,
    )


def _score_cash_liquidity(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    constraints = input_.twin.constraints
    if input_.cash_weight < constraints.cash_band_min_weight:
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=60,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_BELOW_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_min_weight,
        )
    if input_.cash_weight > constraints.cash_band_max_weight:
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=75,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_ABOVE_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_max_weight,
        )
    if input_.projected_net_cashflow is not None and input_.projected_net_cashflow < Decimal("0"):
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="PROJECTED_CASHFLOW_PRESSURE",
            measured_value=input_.projected_net_cashflow,
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.CASH_LIQUIDITY)


def _score_tax_turnover(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.tax_lot_missing_security_ids:
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=40,
            state=MandateHealthState.BLOCKED,
            reason_code="TAX_LOTS_INCOMPLETE",
            measured_value=len(input_.tax_lot_missing_security_ids),
            threshold_value=0,
        )
    if (
        input_.turnover_budget_used is not None
        and input_.twin.constraints.turnover_budget is not None
        and input_.turnover_budget_used >= input_.twin.constraints.turnover_budget * Decimal("0.8")
    ):
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="TURNOVER_BUDGET_NEAR_LIMIT",
            measured_value=input_.turnover_budget_used,
            threshold_value=input_.twin.constraints.turnover_budget,
        )
    return _ready_score(MandateHealthDimension.TAX_TURNOVER)


def _score_eligibility_restrictions(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    restricted = set(input_.restricted_held_instruments)
    restricted.update(input_.restricted_target_instruments)
    restricted.update(
        instrument_id
        for instrument_id in input_.current_weights
        if instrument_id in set(input_.twin.constraints.restricted_instruments)
    )
    if restricted:
        return _attention_score(
            dimension=MandateHealthDimension.ELIGIBILITY_RESTRICTIONS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="RESTRICTED_INSTRUMENT_HELD",
            measured_value=len(restricted),
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.ELIGIBILITY_RESTRICTIONS)


def _score_performance_attention(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    source_score = _score_source_health_context(
        context=input_.performance_health_context,
        dimension=MandateHealthDimension.PERFORMANCE_ATTENTION,
        attention_reason_code="SOURCE_PERFORMANCE_HEALTH_ATTENTION",
        unavailable_reason_code="SOURCE_PERFORMANCE_HEALTH_UNAVAILABLE",
    )
    if source_score is not None:
        return source_score
    if input_.performance_under_review:
        return _attention_score(
            dimension=MandateHealthDimension.PERFORMANCE_ATTENTION,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="PERFORMANCE_UNDER_REVIEW",
        )
    return _ready_score(MandateHealthDimension.PERFORMANCE_ATTENTION)


def _score_source_health_context(
    *,
    context: Optional[DpmMandateSourceHealthContext],
    dimension: MandateHealthDimension,
    attention_reason_code: str,
    unavailable_reason_code: str,
) -> Optional[DpmMandateDimensionScore]:
    if context is None:
        return None
    context_ref = _source_health_context_ref(context)
    if context.health_state == "ready" and context.threshold_breached is not True:
        return _ready_score(dimension)
    if context.health_state == "unavailable":
        return _attention_score(
            dimension=dimension,
            score=60,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code=unavailable_reason_code,
            measured_value=f"{context.source_product_name}:unavailable",
            threshold_value="ready",
            evidence_refs=[context_ref],
        )
    return _attention_score(
        dimension=dimension,
        score=65,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code=attention_reason_code,
        measured_value=f"{context.source_product_name}:{context.health_state}",
        threshold_value="ready",
        evidence_refs=[context_ref],
    )


def _score_workflow_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.workflow_blocked:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="REBALANCE_RUN_BLOCKED",
        )
    if input_.sustainability_review_required:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="SUSTAINABILITY_REVIEW_REQUIRED",
        )
    if input_.approval_required:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="APPROVAL_REQUIRED",
        )
    return _ready_score(MandateHealthDimension.WORKFLOW_READINESS)


def _score_review_cadence(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    due_date = input_.twin.review_policy.next_review_due_date
    if due_date is not None and due_date < input_.twin.as_of_date:
        days_overdue = (input_.twin.as_of_date - due_date).days
        return _attention_score(
            dimension=MandateHealthDimension.REVIEW_CADENCE,
            score=65,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MANDATE_REVIEW_OVERDUE",
            measured_value=days_overdue,
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.REVIEW_CADENCE)


def _score_model_freshness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.model_effective_to is not None and input_.model_effective_to < input_.twin.as_of_date:
        return _attention_score(
            dimension=MandateHealthDimension.MODEL_FRESHNESS,
            score=55,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MODEL_VERSION_STALE",
            measured_value=input_.model_effective_to.isoformat(),
            threshold_value=input_.twin.as_of_date.isoformat(),
        )
    return _ready_score(MandateHealthDimension.MODEL_FRESHNESS)


def _reason_from_score(score: DpmMandateDimensionScore) -> DpmMandateHealthReason:
    severity = (
        MonitoringSeverity.CRITICAL
        if score.state == MandateHealthState.BLOCKED
        else MonitoringSeverity.WARNING
    )
    return DpmMandateHealthReason(
        dimension=score.dimension,
        reason_code=score.reason_code,
        severity=severity,
        message=f"{score.dimension.value} requires attention: {score.reason_code}",
        recommended_action=_recommended_action_for_dimension(score.dimension, score.state),
    )


def _recommended_action_for_dimension(
    dimension: MandateHealthDimension,
    state: MandateHealthState,
) -> MandateRecommendedAction:
    if dimension == MandateHealthDimension.SOURCE_READINESS:
        return MandateRecommendedAction.FIX_SOURCE_DATA
    if dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS:
        return MandateRecommendedAction.REVIEW_RESTRICTION
    if dimension in {
        MandateHealthDimension.WORKFLOW_READINESS,
        MandateHealthDimension.REVIEW_CADENCE,
    }:
        return MandateRecommendedAction.REVIEW_WORKFLOW
    if state == MandateHealthState.PENDING_REVIEW:
        return MandateRecommendedAction.SIMULATE_REBALANCE
    return MandateRecommendedAction.REVIEW_MANDATE


def _overall_recommended_action(
    health_state: MandateHealthState,
    reasons: list[DpmMandateHealthReason],
) -> MandateRecommendedAction:
    if health_state == MandateHealthState.READY:
        return MandateRecommendedAction.NONE
    if reasons:
        return reasons[0].recommended_action
    return MandateRecommendedAction.REVIEW_MANDATE


def _severity_rank(severity: MonitoringSeverity) -> int:
    return {
        MonitoringSeverity.INFO: 0,
        MonitoringSeverity.WARNING: 1,
        MonitoringSeverity.CRITICAL: 2,
    }[severity]


if sum(DIMENSION_WEIGHTS.values()) != 100:
    raise RuntimeError("Mandate health dimension weights must total 100")
