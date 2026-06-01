from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from src.api.services import mandate_optional_sources, mandate_service
from src.api.services.mandate_optional_sources import (
    DpmMandateOptionalSources,
    ready_benchmark_assignment_source,
    ready_optional_source,
    resolve_mandate_optional_sources,
    try_resolve_optional_source,
)
from src.core.dpm_source_context import DpmCoreBenchmarkAssignmentResponse
from src.infrastructure.core_sourcing import DpmCoreResolverError


@dataclass(frozen=True)
class _Supportability:
    state: str


@dataclass(frozen=True)
class _OptionalSource:
    supportability: _Supportability | None = None
    data_quality_status: str | None = None


class _Resolver:
    def resolve_ready_source(self, **kwargs: Any) -> dict[str, Any]:
        return {"kwargs": kwargs}

    def resolve_unavailable_source(self, **kwargs: Any) -> dict[str, Any]:
        raise DpmCoreResolverError("source unavailable")


class _BundleResolver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _source(self, method_name: str, kwargs: dict[str, Any]) -> _OptionalSource:
        self.calls.append((method_name, kwargs))
        return _OptionalSource(
            supportability=_Supportability(state="READY"),
            data_quality_status="COMPLETE",
        )

    def resolve_client_restriction_profile(self, **kwargs: Any) -> _OptionalSource:
        return self._source("client_restriction_profile", kwargs)

    def resolve_sustainability_preference_profile(self, **kwargs: Any) -> _OptionalSource:
        return self._source("sustainability_preference_profile", kwargs)

    def resolve_portfolio_cashflow_projection(self, **kwargs: Any) -> _OptionalSource:
        return self._source("portfolio_cashflow_projection", kwargs)

    def resolve_client_income_needs_schedule(self, **kwargs: Any) -> _OptionalSource:
        return self._source("client_income_needs_schedule", kwargs)

    def resolve_liquidity_reserve_requirement(self, **kwargs: Any) -> _OptionalSource:
        self.calls.append(("liquidity_reserve_requirement", kwargs))
        return _OptionalSource(
            supportability=_Supportability(state="DEGRADED"),
            data_quality_status="COMPLETE",
        )

    def resolve_planned_withdrawal_schedule(self, **kwargs: Any) -> _OptionalSource:
        return self._source("planned_withdrawal_schedule", kwargs)

    def resolve_benchmark_assignment(self, **kwargs: Any) -> DpmCoreBenchmarkAssignmentResponse:
        self.calls.append(("benchmark_assignment", kwargs))
        return _benchmark_assignment()


def _benchmark_assignment(
    *,
    assignment_status: str = "ACTIVE",
) -> DpmCoreBenchmarkAssignmentResponse:
    return DpmCoreBenchmarkAssignmentResponse.model_validate(
        {
            "product_name": "BenchmarkAssignment",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
            "as_of_date": date(2026, 5, 3),
            "effective_from": date(2026, 1, 1),
            "assignment_source": "IPS",
            "assignment_status": assignment_status,
            "assignment_recorded_at": datetime(2026, 5, 3, tzinfo=timezone.utc),
            "assignment_version": 1,
        }
    )


def test_try_resolve_optional_source_calls_available_resolver_method() -> None:
    source, unavailable_family = try_resolve_optional_source(
        resolver=_Resolver(),
        method_name="resolve_ready_source",
        family_name="CLIENT_RESTRICTION_PROFILE",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )

    assert source == {"kwargs": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"}}
    assert unavailable_family is None


def test_try_resolve_optional_source_preserves_absent_optional_method() -> None:
    source, unavailable_family = try_resolve_optional_source(
        resolver=_Resolver(),
        method_name="resolve_missing_source",
        family_name="CLIENT_RESTRICTION_PROFILE",
    )

    assert source is None
    assert unavailable_family is None


def test_try_resolve_optional_source_maps_resolver_error_to_family() -> None:
    source, unavailable_family = try_resolve_optional_source(
        resolver=_Resolver(),
        method_name="resolve_unavailable_source",
        family_name="CLIENT_RESTRICTION_PROFILE",
    )

    assert source is None
    assert unavailable_family == "CLIENT_RESTRICTION_PROFILE"


def test_ready_optional_source_accepts_ready_or_complete_source() -> None:
    source = _OptionalSource(
        supportability=_Supportability(state="READY"),
        data_quality_status="COMPLETE",
    )

    ready_source, unavailable_family = ready_optional_source(
        source=source,
        unavailable_family=None,
        family_name="SUSTAINABILITY_PREFERENCE_PROFILE",
    )

    assert ready_source is source
    assert unavailable_family is None


def test_ready_optional_source_rejects_degraded_supportability() -> None:
    source = _OptionalSource(
        supportability=_Supportability(state="DEGRADED"),
        data_quality_status="COMPLETE",
    )

    ready_source, unavailable_family = ready_optional_source(
        source=source,
        unavailable_family=None,
        family_name="SUSTAINABILITY_PREFERENCE_PROFILE",
    )

    assert ready_source is None
    assert unavailable_family == "SUSTAINABILITY_PREFERENCE_PROFILE"


def test_ready_optional_source_rejects_unaccepted_data_quality_status() -> None:
    source = _OptionalSource(
        supportability=_Supportability(state="READY"),
        data_quality_status="STALE",
    )

    ready_source, unavailable_family = ready_optional_source(
        source=source,
        unavailable_family=None,
        family_name="PORTFOLIO_CASHFLOW_PROJECTION",
    )

    assert ready_source is None
    assert unavailable_family == "PORTFOLIO_CASHFLOW_PROJECTION"


def test_ready_optional_source_preserves_existing_unavailable_family_for_missing_source() -> None:
    ready_source, unavailable_family = ready_optional_source(
        source=None,
        unavailable_family="PLANNED_WITHDRAWAL_SCHEDULE",
        family_name="PLANNED_WITHDRAWAL_SCHEDULE",
    )

    assert ready_source is None
    assert unavailable_family == "PLANNED_WITHDRAWAL_SCHEDULE"


def test_ready_benchmark_assignment_source_requires_active_assignment() -> None:
    assignment = _benchmark_assignment(assignment_status="RETIRED")

    ready_source, unavailable_family = ready_benchmark_assignment_source(
        source=assignment,
        unavailable_family=None,
    )

    assert ready_source is None
    assert unavailable_family == "BENCHMARK_ASSIGNMENT"


def test_resolve_mandate_optional_sources_builds_typed_bundle_and_family_gaps() -> None:
    resolver = _BundleResolver()

    sources = resolve_mandate_optional_sources(
        resolver=resolver,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 5, 3),
        tenant_id="default",
        reference_currency="SGD",
        correlation_id="corr_mandate_sources",
    )

    assert isinstance(sources, DpmMandateOptionalSources)
    assert sources.client_restriction_profile is not None
    assert sources.sustainability_preference_profile is not None
    assert sources.portfolio_cashflow_projection is not None
    assert sources.client_income_needs_schedule is not None
    assert sources.liquidity_reserve_requirement is None
    assert sources.planned_withdrawal_schedule is not None
    assert sources.benchmark_assignment is not None
    assert sources.unavailable_source_families == ["LIQUIDITY_RESERVE_REQUIREMENT"]
    calls = dict(resolver.calls)
    assert calls["client_restriction_profile"]["include_inactive_restrictions"] is False
    assert calls["sustainability_preference_profile"]["include_inactive_preferences"] is False
    assert calls["portfolio_cashflow_projection"]["horizon_days"] == 90
    assert calls["portfolio_cashflow_projection"]["include_projected"] is True
    assert calls["client_income_needs_schedule"]["include_inactive_schedules"] is False
    assert calls["liquidity_reserve_requirement"]["include_inactive_requirements"] is False
    assert calls["planned_withdrawal_schedule"]["horizon_days"] == 365
    assert calls["planned_withdrawal_schedule"]["include_inactive_withdrawals"] is False
    assert calls["benchmark_assignment"]["reporting_currency"] == "SGD"


def test_service_preserves_optional_source_helper_aliases() -> None:
    assert mandate_service._try_resolve_optional_source is try_resolve_optional_source
    assert mandate_service._ready_optional_source is ready_optional_source
    assert mandate_service._ready_benchmark_assignment_source is ready_benchmark_assignment_source
    assert mandate_service._resolve_mandate_optional_sources is resolve_mandate_optional_sources


def test_optional_source_helper_exports_public_surface() -> None:
    assert set(mandate_optional_sources.__all__) == {
        "DpmMandateOptionalSources",
        "ready_benchmark_assignment_source",
        "ready_optional_source",
        "resolve_mandate_optional_sources",
        "try_resolve_optional_source",
    }
