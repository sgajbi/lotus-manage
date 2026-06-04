from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional, Protocol, cast

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
)
from src.api.services.core_resolver_service import (
    CoreResolverClient,
    CoreResolverError,
)


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


class OptionalSourceReadyFn(Protocol):
    def __call__(
        self,
        *,
        source: Any | None,
        unavailable_family: str | None,
        family_name: str,
    ) -> tuple[Any | None, str | None]: ...


def try_resolve_optional_source(
    *,
    resolver: CoreResolverClient,
    method_name: str,
    family_name: str,
    **kwargs: Any,
) -> tuple[Any | None, str | None]:
    method = getattr(resolver, method_name, None)
    if method is None:
        return None, None
    try:
        return method(**kwargs), None
    except CoreResolverError:
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


def _resolve_optional_source_family(
    *,
    resolver: CoreResolverClient,
    family_name: str,
    method_name: str,
    kwargs: dict[str, Any],
    readiness_fn: OptionalSourceReadyFn,
) -> tuple[Any | None, str | None]:
    source, unavailable_family = try_resolve_optional_source(
        resolver=resolver,
        method_name=method_name,
        family_name=family_name,
        **kwargs,
    )
    return readiness_fn(
        source=source,
        unavailable_family=unavailable_family,
        family_name=family_name,
    )


def _mandate_optional_source_specs(
    *,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: Optional[str],
    reference_currency: Optional[str],
    correlation_id: Optional[str],
) -> tuple[tuple[str, str, dict[str, Any], OptionalSourceReadyFn], ...]:
    return (
        (
            "CLIENT_RESTRICTION_PROFILE",
            "resolve_client_restriction_profile",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "tenant_id": tenant_id,
                "mandate_id": mandate_id,
                "include_inactive_restrictions": False,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "SUSTAINABILITY_PREFERENCE_PROFILE",
            "resolve_sustainability_preference_profile",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "tenant_id": tenant_id,
                "mandate_id": mandate_id,
                "include_inactive_preferences": False,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "PORTFOLIO_CASHFLOW_PROJECTION",
            "resolve_portfolio_cashflow_projection",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "horizon_days": 90,
                "include_projected": True,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "CLIENT_INCOME_NEEDS_SCHEDULE",
            "resolve_client_income_needs_schedule",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "tenant_id": tenant_id,
                "mandate_id": mandate_id,
                "include_inactive_schedules": False,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "LIQUIDITY_RESERVE_REQUIREMENT",
            "resolve_liquidity_reserve_requirement",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "tenant_id": tenant_id,
                "mandate_id": mandate_id,
                "include_inactive_requirements": False,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "PLANNED_WITHDRAWAL_SCHEDULE",
            "resolve_planned_withdrawal_schedule",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "tenant_id": tenant_id,
                "mandate_id": mandate_id,
                "horizon_days": 365,
                "include_inactive_withdrawals": False,
                "correlation_id": correlation_id,
            },
            ready_optional_source,
        ),
        (
            "BENCHMARK_ASSIGNMENT",
            "resolve_benchmark_assignment",
            {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "reporting_currency": reference_currency,
                "correlation_id": correlation_id,
            },
            ready_benchmark_assignment_source,
        ),
    )


def resolve_mandate_optional_sources(
    *,
    resolver: CoreResolverClient,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: Optional[str],
    reference_currency: Optional[str],
    correlation_id: Optional[str],
) -> DpmMandateOptionalSources:
    resolved_sources: dict[str, Any | None] = {}
    unavailable_source_families: list[str] = []

    for (
        family_name,
        method_name,
        family_kwargs,
        readiness_fn,
    ) in _mandate_optional_source_specs(
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        reference_currency=reference_currency,
        correlation_id=correlation_id,
    ):
        source, unavailable_family = _resolve_optional_source_family(
            resolver=resolver,
            family_name=family_name,
            method_name=method_name,
            kwargs=family_kwargs,
            readiness_fn=readiness_fn,
        )
        resolved_sources[family_name] = source
        if unavailable_family is not None:
            unavailable_source_families.append(unavailable_family)

    client_restriction_profile = resolved_sources["CLIENT_RESTRICTION_PROFILE"]
    sustainability_preference_profile = resolved_sources["SUSTAINABILITY_PREFERENCE_PROFILE"]
    portfolio_cashflow_projection = resolved_sources["PORTFOLIO_CASHFLOW_PROJECTION"]
    client_income_needs_schedule = resolved_sources["CLIENT_INCOME_NEEDS_SCHEDULE"]
    liquidity_reserve_requirement = resolved_sources["LIQUIDITY_RESERVE_REQUIREMENT"]
    planned_withdrawal_schedule = resolved_sources["PLANNED_WITHDRAWAL_SCHEDULE"]
    benchmark_assignment = cast(
        DpmCoreBenchmarkAssignmentResponse | None,
        resolved_sources["BENCHMARK_ASSIGNMENT"],
    )
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
    family_name: str,
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
