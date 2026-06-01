from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional, cast

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
)
from src.infrastructure.core_sourcing import DpmCoreResolverClient, DpmCoreResolverError


@dataclass(frozen=True)
class DpmMandateOptionalSources:
    client_restriction_profile: DpmCoreClientRestrictionProfileResponse | None
    sustainability_preference_profile: DpmCoreSustainabilityPreferenceProfileResponse | None
    portfolio_cashflow_projection: DpmCorePortfolioCashflowProjectionResponse | None
    client_income_needs_schedule: DpmCoreClientIncomeNeedsScheduleResponse | None
    liquidity_reserve_requirement: DpmCoreLiquidityReserveRequirementResponse | None
    planned_withdrawal_schedule: DpmCorePlannedWithdrawalScheduleResponse | None
    benchmark_assignment: DpmCoreBenchmarkAssignmentResponse | None
    unavailable_source_families: list[str]


def try_resolve_optional_source(
    *,
    resolver: DpmCoreResolverClient,
    method_name: str,
    family_name: str,
    **kwargs: Any,
) -> tuple[Any | None, str | None]:
    method = getattr(resolver, method_name, None)
    if method is None:
        return None, None
    try:
        return method(**kwargs), None
    except DpmCoreResolverError:
        return None, family_name


def ready_optional_source(
    *,
    source: Any | None,
    unavailable_family: str | None,
    family_name: str,
) -> tuple[Any | None, str | None]:
    if source is None:
        return None, unavailable_family
    supportability = getattr(source, "supportability", None)
    if supportability is not None and getattr(supportability, "state", None) != "READY":
        return None, family_name
    data_quality_status = getattr(source, "data_quality_status", None)
    if data_quality_status is not None and str(data_quality_status).upper() not in {
        "READY",
        "COMPLETE",
        "ACCEPTED",
    }:
        return None, family_name
    return source, unavailable_family


def resolve_mandate_optional_sources(
    *,
    resolver: DpmCoreResolverClient,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: Optional[str],
    reference_currency: Optional[str],
    correlation_id: Optional[str],
) -> DpmMandateOptionalSources:
    client_restriction_profile, unavailable_client_restrictions = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_client_restriction_profile",
        family_name="CLIENT_RESTRICTION_PROFILE",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        mandate_id=mandate_id,
        include_inactive_restrictions=False,
        correlation_id=correlation_id,
    )
    client_restriction_profile, unavailable_client_restrictions = ready_optional_source(
        source=client_restriction_profile,
        unavailable_family=unavailable_client_restrictions,
        family_name="CLIENT_RESTRICTION_PROFILE",
    )
    (
        sustainability_preference_profile,
        unavailable_sustainability_preferences,
    ) = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_sustainability_preference_profile",
        family_name="SUSTAINABILITY_PREFERENCE_PROFILE",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        mandate_id=mandate_id,
        include_inactive_preferences=False,
        correlation_id=correlation_id,
    )
    (
        sustainability_preference_profile,
        unavailable_sustainability_preferences,
    ) = ready_optional_source(
        source=sustainability_preference_profile,
        unavailable_family=unavailable_sustainability_preferences,
        family_name="SUSTAINABILITY_PREFERENCE_PROFILE",
    )
    portfolio_cashflow_projection, unavailable_cashflow_projection = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_portfolio_cashflow_projection",
        family_name="PORTFOLIO_CASHFLOW_PROJECTION",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        horizon_days=90,
        include_projected=True,
        correlation_id=correlation_id,
    )
    portfolio_cashflow_projection, unavailable_cashflow_projection = ready_optional_source(
        source=portfolio_cashflow_projection,
        unavailable_family=unavailable_cashflow_projection,
        family_name="PORTFOLIO_CASHFLOW_PROJECTION",
    )
    client_income_needs_schedule, unavailable_income_needs = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_client_income_needs_schedule",
        family_name="CLIENT_INCOME_NEEDS_SCHEDULE",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        mandate_id=mandate_id,
        include_inactive_schedules=False,
        correlation_id=correlation_id,
    )
    client_income_needs_schedule, unavailable_income_needs = ready_optional_source(
        source=client_income_needs_schedule,
        unavailable_family=unavailable_income_needs,
        family_name="CLIENT_INCOME_NEEDS_SCHEDULE",
    )
    liquidity_reserve_requirement, unavailable_liquidity_reserve = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_liquidity_reserve_requirement",
        family_name="LIQUIDITY_RESERVE_REQUIREMENT",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        mandate_id=mandate_id,
        include_inactive_requirements=False,
        correlation_id=correlation_id,
    )
    liquidity_reserve_requirement, unavailable_liquidity_reserve = ready_optional_source(
        source=liquidity_reserve_requirement,
        unavailable_family=unavailable_liquidity_reserve,
        family_name="LIQUIDITY_RESERVE_REQUIREMENT",
    )
    planned_withdrawal_schedule, unavailable_planned_withdrawal = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_planned_withdrawal_schedule",
        family_name="PLANNED_WITHDRAWAL_SCHEDULE",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        mandate_id=mandate_id,
        horizon_days=365,
        include_inactive_withdrawals=False,
        correlation_id=correlation_id,
    )
    planned_withdrawal_schedule, unavailable_planned_withdrawal = ready_optional_source(
        source=planned_withdrawal_schedule,
        unavailable_family=unavailable_planned_withdrawal,
        family_name="PLANNED_WITHDRAWAL_SCHEDULE",
    )
    benchmark_assignment, unavailable_benchmark_assignment = try_resolve_optional_source(
        resolver=resolver,
        method_name="resolve_benchmark_assignment",
        family_name="BENCHMARK_ASSIGNMENT",
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        reporting_currency=reference_currency,
        correlation_id=correlation_id,
    )
    benchmark_assignment, unavailable_benchmark_assignment = ready_optional_source(
        source=benchmark_assignment,
        unavailable_family=unavailable_benchmark_assignment,
        family_name="BENCHMARK_ASSIGNMENT",
    )
    benchmark_assignment, unavailable_benchmark_assignment = ready_benchmark_assignment_source(
        source=cast(DpmCoreBenchmarkAssignmentResponse | None, benchmark_assignment),
        unavailable_family=unavailable_benchmark_assignment,
    )
    unavailable_source_families = [
        family
        for family in (
            unavailable_client_restrictions,
            unavailable_sustainability_preferences,
            unavailable_cashflow_projection,
            unavailable_income_needs,
            unavailable_liquidity_reserve,
            unavailable_planned_withdrawal,
            unavailable_benchmark_assignment,
        )
        if family is not None
    ]
    return DpmMandateOptionalSources(
        client_restriction_profile=cast(
            DpmCoreClientRestrictionProfileResponse | None,
            client_restriction_profile,
        ),
        sustainability_preference_profile=cast(
            DpmCoreSustainabilityPreferenceProfileResponse | None,
            sustainability_preference_profile,
        ),
        portfolio_cashflow_projection=cast(
            DpmCorePortfolioCashflowProjectionResponse | None,
            portfolio_cashflow_projection,
        ),
        client_income_needs_schedule=cast(
            DpmCoreClientIncomeNeedsScheduleResponse | None,
            client_income_needs_schedule,
        ),
        liquidity_reserve_requirement=cast(
            DpmCoreLiquidityReserveRequirementResponse | None,
            liquidity_reserve_requirement,
        ),
        planned_withdrawal_schedule=cast(
            DpmCorePlannedWithdrawalScheduleResponse | None,
            planned_withdrawal_schedule,
        ),
        benchmark_assignment=benchmark_assignment,
        unavailable_source_families=unavailable_source_families,
    )


def ready_benchmark_assignment_source(
    *,
    source: DpmCoreBenchmarkAssignmentResponse | None,
    unavailable_family: str | None,
) -> tuple[DpmCoreBenchmarkAssignmentResponse | None, str | None]:
    if source is None:
        return None, unavailable_family
    if source.assignment_status.upper() != "ACTIVE":
        return None, "BENCHMARK_ASSIGNMENT"
    return source, unavailable_family


__all__ = [
    "DpmMandateOptionalSources",
    "ready_benchmark_assignment_source",
    "ready_optional_source",
    "resolve_mandate_optional_sources",
    "try_resolve_optional_source",
]
