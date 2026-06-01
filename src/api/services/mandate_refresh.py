from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from src.api.services.mandate_errors import (
    DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError,
)
from src.api.services.mandate_health_result import (
    DpmMandateHealthCalculationResult,
    calculate_mandate_health_result,
)
from src.api.services.mandate_optional_sources import resolve_mandate_optional_sources
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    build_health_input_from_core_sources,
    compile_mandate_digital_twin_from_core,
)
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)


@dataclass(frozen=True)
class DpmMandateRefreshResult:
    twin: DpmMandateDigitalTwin
    health_snapshot: DpmMandateHealthSnapshot
    monitoring_exceptions: list[DpmMonitoringException]


def build_mandate_refresh_result_from_core(
    *,
    core_resolver: DpmCoreResolverClient,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: Optional[str],
    booking_center_code: Optional[str],
    model_portfolio_id: Optional[str],
    reference_currency: Optional[str],
    include_market_data_coverage: bool,
    correlation_id: Optional[str],
) -> DpmMandateRefreshResult:
    try:
        mandate = core_resolver.resolve_mandate_binding(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
            mandate_id=mandate_id,
            booking_center_code=booking_center_code,
            include_policy_pack=True,
            correlation_id=correlation_id,
        )
        resolved_model_portfolio_id = model_portfolio_id or mandate.model_portfolio_id
        model_targets = core_resolver.resolve_model_portfolio_targets(
            model_portfolio_id=resolved_model_portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        market_data_coverage = None
        if include_market_data_coverage:
            market_data_coverage = core_resolver.resolve_market_data_coverage(
                instrument_ids=[target.instrument_id for target in model_targets.targets],
                currency_pairs=[],
                as_of_date=as_of_date,
                valuation_currency=model_targets.base_currency,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
    except DpmCoreResolverUnavailableError as exc:
        raise DpmMandateSourceUnavailableError("DPM_MANDATE_SOURCE_UNAVAILABLE") from exc
    except DpmCoreResolverError as exc:
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_SOURCE_INCOMPLETE") from exc

    optional_sources = resolve_mandate_optional_sources(
        resolver=core_resolver,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        reference_currency=reference_currency,
        correlation_id=correlation_id,
    )
    twin = compile_mandate_digital_twin_from_core(
        mandate=mandate,
        model_targets=model_targets,
        as_of_date=as_of_date,
        reference_currency=reference_currency,
        client_restriction_profile=optional_sources.client_restriction_profile,
        sustainability_preference_profile=optional_sources.sustainability_preference_profile,
        portfolio_cashflow_projection=optional_sources.portfolio_cashflow_projection,
        client_income_needs_schedule=optional_sources.client_income_needs_schedule,
        liquidity_reserve_requirement=optional_sources.liquidity_reserve_requirement,
        planned_withdrawal_schedule=optional_sources.planned_withdrawal_schedule,
        benchmark_assignment=optional_sources.benchmark_assignment,
    )
    health_result = _health_result_for_refresh(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
        optional_sources=optional_sources,
    )
    return DpmMandateRefreshResult(
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
    )


def _health_result_for_refresh(
    *,
    twin: DpmMandateDigitalTwin,
    model_targets: Any,
    market_data_coverage: Any | None,
    optional_sources: Any,
) -> DpmMandateHealthCalculationResult:
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
        client_restriction_profile=optional_sources.client_restriction_profile,
        sustainability_preference_profile=optional_sources.sustainability_preference_profile,
        portfolio_cashflow_projection=optional_sources.portfolio_cashflow_projection,
        unavailable_source_families=optional_sources.unavailable_source_families,
    )
    return calculate_mandate_health_result(health_input)


__all__ = ["DpmMandateRefreshResult", "build_mandate_refresh_result_from_core"]
