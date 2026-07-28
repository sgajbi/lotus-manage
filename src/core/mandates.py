from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
    DpmMandateHealthSourceContextMetadata,
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
from src.core.mandate_health_scoring import calculate_mandate_health

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
    "DpmMandateHealthSourceContextMetadata",
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
