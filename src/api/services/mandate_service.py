from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from src.api.services.mandate_command_center import (
    attention_buckets,
    build_command_center_summary,
    command_center_supportability_state,
    recommended_actions,
    run_matches_command_center_filters as _run_matches_command_center_filters,
    severity_rank,
)
from src.api.services.mandate_errors import (
    DpmMandateDiffUnavailableError as DpmMandateDiffUnavailableError,
    DpmMandateHealthNotFoundError as DpmMandateHealthNotFoundError,
    DpmMandateNotFoundError as DpmMandateNotFoundError,
    DpmMandateSourceIncompleteError as DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError as DpmMandateSourceUnavailableError,
    DpmMonitoringRunNotFoundError as DpmMonitoringRunNotFoundError,
)
from src.api.services.mandate_diff import (
    DpmMandateDiff as DpmMandateDiff,
    DpmMandateFieldChange as DpmMandateFieldChange,
    build_mandate_diff as _build_mandate_diff,
    diff_payloads,
    iter_changed_fields,
    materiality_for_field,
)
from src.api.services.mandate_health_result import (
    DpmMandateHealthCalculationResult as DpmMandateHealthCalculationResult,
    calculate_mandate_health_result,
)
from src.api.services.mandate_monitoring_run import (
    build_monitoring_run,
    exceptions_for_monitoring_run,
    increment_distribution,
    monitoring_run_id_for,
)
from src.api.services.mandate_optional_sources import (
    ready_benchmark_assignment_source,
    ready_optional_source,
    resolve_mandate_optional_sources,
    try_resolve_optional_source,
)
from src.api.services.mandate_pm_book import (
    mandate_ids_from_pm_book_membership as mandate_ids_from_pm_book_membership,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmCommandCenterSummary,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
    build_health_input_from_core_sources,
    calculate_mandate_health,
    compile_mandate_digital_twin_from_core,
    monitoring_exceptions_from_health,
)
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)

_severity_rank = severity_rank
_attention_buckets = attention_buckets
_build_command_center_summary = build_command_center_summary
_command_center_supportability_state = command_center_supportability_state
_recommended_actions = recommended_actions
_diff_payloads = diff_payloads
_iter_changed_fields = iter_changed_fields
_materiality_for_field = materiality_for_field
_try_resolve_optional_source = try_resolve_optional_source
_ready_optional_source = ready_optional_source
_ready_benchmark_assignment_source = ready_benchmark_assignment_source
_resolve_mandate_optional_sources = resolve_mandate_optional_sources
_calculate_mandate_health_result = calculate_mandate_health_result
_monitoring_run_id_for = monitoring_run_id_for
_increment_distribution = increment_distribution
_exceptions_for_monitoring_run = exceptions_for_monitoring_run
_build_monitoring_run = build_monitoring_run


@dataclass(frozen=True)
class DpmMandateRefreshResult:
    twin: DpmMandateDigitalTwin
    health_snapshot: DpmMandateHealthSnapshot
    monitoring_exceptions: list[DpmMonitoringException]


def refresh_mandate_from_core(
    *,
    repository: DpmMandateRepository,
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
    optional_sources = _resolve_mandate_optional_sources(
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
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
        client_restriction_profile=optional_sources.client_restriction_profile,
        sustainability_preference_profile=optional_sources.sustainability_preference_profile,
        portfolio_cashflow_projection=optional_sources.portfolio_cashflow_projection,
        unavailable_source_families=optional_sources.unavailable_source_families,
    )
    health_result = _calculate_mandate_health_result(health_input)

    repository.save_mandate_snapshot(twin)
    repository.save_health_snapshot(health_result.snapshot)
    for exception in health_result.monitoring_exceptions:
        repository.save_monitoring_exception(exception)

    return DpmMandateRefreshResult(
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
    )


def get_latest_mandate_by_portfolio(
    *,
    repository: DpmMandateRepository,
    portfolio_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def get_latest_mandate(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate(mandate_id=mandate_id)
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def list_mandate_versions(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
) -> list[DpmMandateDigitalTwin]:
    versions = repository.list_mandate_versions(mandate_id=mandate_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return versions


def get_latest_mandate_health(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
) -> DpmMandateHealthSnapshot:
    snapshot = repository.get_latest_health_snapshot(mandate_id=mandate_id)
    if snapshot is None:
        raise DpmMandateHealthNotFoundError("DPM_MANDATE_HEALTH_NOT_FOUND")
    return snapshot


def recalculate_mandate_health(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    health_input: DpmMandateHealthInput,
) -> DpmMandateHealthSnapshot:
    if health_input.twin.mandate_id != mandate_id:
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_HEALTH_INPUT_MISMATCH")
    health_result = _calculate_mandate_health_result(health_input)
    repository.save_mandate_snapshot(health_input.twin)
    repository.save_health_snapshot(health_result.snapshot)
    for exception in health_result.monitoring_exceptions:
        repository.save_monitoring_exception(exception)
    return health_result.snapshot


def run_mandate_monitoring_once(
    *,
    repository: DpmMandateRepository,
    mandate_ids: list[str],
    as_of_date: date,
    filters: dict[str, str],
) -> DpmMonitoringRun:
    requested_at = datetime.now(timezone.utc)
    monitoring_run_id = _monitoring_run_id_for(requested_at)
    health_distribution: dict[str, int] = {}
    source_readiness_summary: dict[str, int] = {}
    exception_count = 0

    for mandate_id in mandate_ids:
        twin = get_latest_mandate(repository=repository, mandate_id=mandate_id)
        health_input = DpmMandateHealthInput(
            twin=twin.model_copy(update={"as_of_date": as_of_date})
        )
        snapshot = calculate_mandate_health(health_input)
        repository.save_health_snapshot(snapshot)
        _increment_distribution(health_distribution, snapshot.health_state.value)
        _increment_distribution(source_readiness_summary, snapshot.source_readiness_state)
        exceptions = monitoring_exceptions_from_health(
            snapshot,
            source_lineage=twin.source_lineage,
        )
        exception_count += len(exceptions)
        for exception in _exceptions_for_monitoring_run(
            exceptions,
            monitoring_run_id=monitoring_run_id,
        ):
            repository.save_monitoring_exception(exception)

    run = _build_monitoring_run(
        monitoring_run_id=monitoring_run_id,
        as_of_date=as_of_date,
        requested_at=requested_at,
        completed_at=datetime.now(timezone.utc),
        mandate_ids=mandate_ids,
        filters=filters,
        health_distribution=health_distribution,
        exception_count=exception_count,
        source_readiness_summary=source_readiness_summary,
    )
    repository.save_monitoring_run(run)
    return run


def get_monitoring_run(
    *,
    repository: DpmMandateRepository,
    monitoring_run_id: str,
) -> DpmMonitoringRun:
    run = repository.get_monitoring_run(monitoring_run_id=monitoring_run_id)
    if run is None:
        raise DpmMonitoringRunNotFoundError("DPM_MONITORING_RUN_NOT_FOUND")
    return run


def list_monitoring_runs(
    *,
    repository: DpmMandateRepository,
    status: Optional[str],
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmMonitoringRun], Optional[str]]:
    return repository.list_monitoring_runs(status=status, limit=limit, cursor=cursor)


def list_monitoring_exceptions(
    *,
    repository: DpmMandateRepository,
    mandate_id: Optional[str],
    portfolio_id: Optional[str],
    state: Optional[str],
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmMonitoringException], Optional[str]]:
    return repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        state=state,
        limit=limit,
        cursor=cursor,
    )


def resolve_monitoring_exception(
    *,
    repository: DpmMandateRepository,
    exception_id: str,
    resolution_reason: str,
) -> DpmMonitoringException:
    resolved = repository.resolve_monitoring_exception(
        exception_id=exception_id,
        resolved_at=datetime.now(timezone.utc),
        resolution_reason=resolution_reason,
    )
    if resolved is None:
        raise DpmMandateNotFoundError("DPM_MONITORING_EXCEPTION_NOT_FOUND")
    return resolved


def get_command_center_summary(
    *,
    repository: DpmMandateRepository,
    tenant_id: Optional[str],
    portfolio_manager_id: Optional[str],
    book_id: Optional[str],
    as_of_date: Optional[date],
    health_state: Optional[str],
    limit: int,
) -> DpmCommandCenterSummary:
    runs, _ = repository.list_monitoring_runs(status=None, limit=200, cursor=None)
    matching_runs = [
        run
        for run in runs
        if _run_matches_command_center_filters(
            run,
            tenant_id=tenant_id,
            portfolio_manager_id=portfolio_manager_id,
            book_id=book_id,
            as_of_date=as_of_date,
        )
    ]
    latest_run = matching_runs[0] if matching_runs else None
    active_exceptions, _ = repository.list_monitoring_exceptions(
        monitoring_run_id=latest_run.monitoring_run_id if latest_run else None,
        mandate_id=None,
        portfolio_id=None,
        state="ACTIVE",
        limit=limit,
        cursor=None,
    )

    return _build_command_center_summary(
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=as_of_date,
        health_state=health_state,
        latest_run=latest_run,
        active_exceptions=active_exceptions,
        limit=limit,
        generated_at=datetime.now(timezone.utc),
    )


def diff_mandate_versions(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    from_version: Optional[str],
    to_version: Optional[str],
) -> DpmMandateDiff:
    versions = repository.list_mandate_versions(mandate_id=mandate_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")

    by_version = {version.mandate_version: version for version in versions}
    if from_version is not None or to_version is not None:
        if from_version is None or to_version is None:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
        if from_version not in by_version or to_version not in by_version:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_VERSION_NOT_FOUND")
        previous = by_version[from_version]
        current = by_version[to_version]
    else:
        if len(versions) < 2:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
        current, previous = versions[0], versions[1]

    return _build_mandate_diff(
        mandate_id=mandate_id,
        previous=previous,
        current=current,
    )
