from datetime import date
from types import SimpleNamespace

from src.api.services.mandate_optional_sources import DpmMandateOptionalSources
from src.api.services.mandate_refresh_context import (
    build_digital_twin_source_context,
    build_health_input_source_context,
)


def _optional_sources() -> DpmMandateOptionalSources:
    return DpmMandateOptionalSources(
        client_restriction_profile=SimpleNamespace(name="restriction_profile"),
        sustainability_preference_profile=SimpleNamespace(name="sustainability_profile"),
        portfolio_cashflow_projection=SimpleNamespace(name="cashflow_projection"),
        client_income_needs_schedule=SimpleNamespace(name="income_needs"),
        liquidity_reserve_requirement=SimpleNamespace(name="reserve_requirement"),
        planned_withdrawal_schedule=SimpleNamespace(name="withdrawal_schedule"),
        benchmark_assignment=SimpleNamespace(name="benchmark_assignment"),
        unavailable_source_families=["CLIENT_RESTRICTION_PROFILE"],
    )


def test_build_digital_twin_source_context_uses_full_optional_bundle() -> None:
    sources = _optional_sources()
    context = build_digital_twin_source_context(optional_sources=sources)
    assert context == {
        "client_restriction_profile": sources.client_restriction_profile,
        "sustainability_preference_profile": sources.sustainability_preference_profile,
        "portfolio_cashflow_projection": sources.portfolio_cashflow_projection,
        "client_income_needs_schedule": sources.client_income_needs_schedule,
        "liquidity_reserve_requirement": sources.liquidity_reserve_requirement,
        "planned_withdrawal_schedule": sources.planned_withdrawal_schedule,
        "benchmark_assignment": sources.benchmark_assignment,
    }


def test_build_health_input_source_context_projects_refresh_health_inputs() -> None:
    sources = _optional_sources()
    twin = SimpleNamespace(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    model_targets = SimpleNamespace(as_of_date=date(2026, 5, 3))
    market_data_coverage = SimpleNamespace(source_product_name="MarketDataCoverageWindow")
    context = build_health_input_source_context(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
        optional_sources=sources,
    )
    assert context["twin"] is twin
    assert context["model_targets"] is model_targets
    assert context["market_data_coverage"] is market_data_coverage
    assert context["client_restriction_profile"] is sources.client_restriction_profile
    assert context["sustainability_preference_profile"] is sources.sustainability_preference_profile
    assert context["portfolio_cashflow_projection"] is sources.portfolio_cashflow_projection
    assert context["unavailable_source_families"] == ["CLIENT_RESTRICTION_PROFILE"]


def test_mandate_refresh_context_exports_public_surface() -> None:
    from src.api.services import mandate_refresh_context

    assert set(mandate_refresh_context.__all__) == {
        "build_digital_twin_source_context",
        "build_health_input_source_context",
    }
