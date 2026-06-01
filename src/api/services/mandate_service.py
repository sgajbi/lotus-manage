from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from src.api.services.mandate_command_center import (
    build_command_center_summary,
    latest_command_center_run,
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
    build_mandate_diff_for_versions,
)
from src.api.services.mandate_health_result import (
    DpmMandateHealthCalculationResult as DpmMandateHealthCalculationResult,
    calculate_mandate_health_result,
)
from src.api.services.mandate_health_persistence import persist_mandate_health_evidence
from src.api.services.mandate_monitoring_run import (
    DpmMonitoringRunAccumulator as DpmMonitoringRunAccumulator,
    DpmMonitoringRunMandateResult as DpmMonitoringRunMandateResult,
    build_monitoring_run,
    calculate_monitoring_run_mandate_result,
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
from src.api.services.mandate_refresh import (
    DpmMandateRefreshResult as DpmMandateRefreshResult,
    build_mandate_refresh_result_from_core,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmCommandCenterSummary,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
)
from src.infrastructure.core_sourcing import DpmCoreResolverClient

_try_resolve_optional_source = try_resolve_optional_source
_ready_optional_source = ready_optional_source
_ready_benchmark_assignment_source = ready_benchmark_assignment_source
_resolve_mandate_optional_sources = resolve_mandate_optional_sources
_monitoring_run_accumulator = DpmMonitoringRunAccumulator
_monitoring_run_id_for = monitoring_run_id_for
_increment_distribution = increment_distribution
_exceptions_for_monitoring_run = exceptions_for_monitoring_run
_calculate_monitoring_run_mandate_result = calculate_monitoring_run_mandate_result
_build_monitoring_run = build_monitoring_run


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
    refresh_result = build_mandate_refresh_result_from_core(
        core_resolver=core_resolver,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        booking_center_code=booking_center_code,
        model_portfolio_id=model_portfolio_id,
        reference_currency=reference_currency,
        include_market_data_coverage=include_market_data_coverage,
        correlation_id=correlation_id,
    )

    persist_mandate_health_evidence(
        repository=repository,
        twin=refresh_result.twin,
        health_snapshot=refresh_result.health_snapshot,
        monitoring_exceptions=refresh_result.monitoring_exceptions,
    )

    return refresh_result


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
    health_result = calculate_mandate_health_result(health_input)
    persist_mandate_health_evidence(
        repository=repository,
        twin=health_input.twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
    )
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
    accumulator = _monitoring_run_accumulator.empty()

    for mandate_id in mandate_ids:
        twin = get_latest_mandate(repository=repository, mandate_id=mandate_id)
        mandate_result = _calculate_monitoring_run_mandate_result(
            twin=twin,
            as_of_date=as_of_date,
            monitoring_run_id=monitoring_run_id,
        )
        snapshot = mandate_result.health_snapshot
        persist_mandate_health_evidence(
            repository=repository,
            health_snapshot=snapshot,
            monitoring_exceptions=mandate_result.monitoring_exceptions,
        )
        accumulator.record(mandate_result)

    run = _build_monitoring_run(
        monitoring_run_id=monitoring_run_id,
        as_of_date=as_of_date,
        requested_at=requested_at,
        completed_at=datetime.now(timezone.utc),
        mandate_ids=mandate_ids,
        filters=filters,
        health_distribution=accumulator.health_distribution,
        exception_count=accumulator.exception_count,
        source_readiness_summary=accumulator.source_readiness_summary,
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
    latest_run = latest_command_center_run(
        runs,
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=as_of_date,
    )
    active_exceptions, _ = repository.list_monitoring_exceptions(
        monitoring_run_id=latest_run.monitoring_run_id if latest_run else None,
        mandate_id=None,
        portfolio_id=None,
        state="ACTIVE",
        limit=limit,
        cursor=None,
    )

    return build_command_center_summary(
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

    return build_mandate_diff_for_versions(
        mandate_id=mandate_id,
        versions=versions,
        from_version=from_version,
        to_version=to_version,
    )
