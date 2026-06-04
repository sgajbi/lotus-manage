from __future__ import annotations

from typing import Any

from src.api.services.mandate_optional_sources import DpmMandateOptionalSources


def build_digital_twin_source_context(
    *,
    optional_sources: DpmMandateOptionalSources,
) -> dict[str, Any]:
    return {
        "client_restriction_profile": optional_sources.client_restriction_profile,
        "sustainability_preference_profile": optional_sources.sustainability_preference_profile,
        "portfolio_cashflow_projection": optional_sources.portfolio_cashflow_projection,
        "client_income_needs_schedule": optional_sources.client_income_needs_schedule,
        "liquidity_reserve_requirement": optional_sources.liquidity_reserve_requirement,
        "planned_withdrawal_schedule": optional_sources.planned_withdrawal_schedule,
        "benchmark_assignment": optional_sources.benchmark_assignment,
    }


def build_health_input_source_context(
    *,
    twin: Any,
    model_targets: Any,
    market_data_coverage: Any | None,
    optional_sources: DpmMandateOptionalSources,
) -> dict[str, Any]:
    return {
        "twin": twin,
        "model_targets": model_targets,
        "market_data_coverage": market_data_coverage,
        "client_restriction_profile": optional_sources.client_restriction_profile,
        "sustainability_preference_profile": optional_sources.sustainability_preference_profile,
        "portfolio_cashflow_projection": optional_sources.portfolio_cashflow_projection,
        "unavailable_source_families": optional_sources.unavailable_source_families,
    }


__all__ = ["build_digital_twin_source_context", "build_health_input_source_context"]
