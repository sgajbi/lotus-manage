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
from src.api.services.core_resolver_service import CoreResolverClient
from src.api.services.mandate_health_persistence import persist_mandate_health_evidence
from src.api.services import mandate_monitoring_support
from src.api.services.mandate_monitoring_run import (
    DpmMonitoringRunAccumulator as DpmMonitoringRunAccumulator,
    DpmMonitoringRunMandateResult as DpmMonitoringRunMandateResult,
    build_monitoring_run,
    monitoring_run_id_for,
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
    MANDATE_LIMIT_PROVENANCE_AMBIGUOUS,
    DpmCommandCenterSummary,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
)


def refresh_mandate_from_core(
    *,
    repository: DpmMandateRepository,
    core_resolver: CoreResolverClient,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: str,
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
        tenant_id=tenant_id,
        twin=refresh_result.twin,
        mandate_producer_kind="CORE_COMPILED",
        health_snapshot=refresh_result.health_snapshot,
        monitoring_exceptions=refresh_result.monitoring_exceptions,
    )

    return refresh_result


def get_latest_mandate_by_portfolio(
    *,
    repository: DpmMandateRepository,
    portfolio_id: str,
    tenant_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate_by_portfolio(
        portfolio_id=portfolio_id, tenant_id=tenant_id
    )
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def get_latest_mandate(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    tenant_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate(mandate_id=mandate_id, tenant_id=tenant_id)
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def list_mandate_versions(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    tenant_id: str,
) -> list[DpmMandateDigitalTwin]:
    versions = repository.list_mandate_versions(mandate_id=mandate_id, tenant_id=tenant_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return versions


def get_latest_mandate_health(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    tenant_id: str,
) -> DpmMandateHealthSnapshot:
    snapshot = repository.get_latest_health_snapshot(mandate_id=mandate_id, tenant_id=tenant_id)
    if snapshot is None:
        raise DpmMandateHealthNotFoundError("DPM_MANDATE_HEALTH_NOT_FOUND")
    return snapshot


def recalculate_mandate_health(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    health_input: DpmMandateHealthInput,
    tenant_id: str,
) -> DpmMandateHealthSnapshot:
    if health_input.twin.mandate_id != mandate_id:
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_HEALTH_INPUT_MISMATCH")
    retained_projection = _resolve_retained_ambiguous_projection(
        repository=repository,
        twin=health_input.twin,
        tenant_id=tenant_id,
    )
    calculation_input = (
        health_input.model_copy(update={"twin": retained_projection})
        if retained_projection is not None
        else health_input
    )
    health_result = calculate_mandate_health_result(calculation_input, tenant_id=tenant_id)
    persist_mandate_health_evidence(
        repository=repository,
        tenant_id=tenant_id,
        twin=calculation_input.twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
        verified_retained_projection=retained_projection is not None,
    )
    return health_result.snapshot


def _resolve_retained_ambiguous_projection(
    *,
    repository: DpmMandateRepository,
    twin: DpmMandateDigitalTwin,
    tenant_id: str,
) -> DpmMandateDigitalTwin | None:
    matching_snapshot = next(
        (
            stored
            for stored in repository.list_mandate_versions(
                mandate_id=twin.mandate_id,
                tenant_id=tenant_id,
            )
            if stored.mandate_version == twin.mandate_version
            and stored.as_of_date == twin.as_of_date
        ),
        None,
    )
    submitted_as_ambiguous = MANDATE_LIMIT_PROVENANCE_AMBIGUOUS in twin.field_gap_codes
    if matching_snapshot is None:
        if not submitted_as_ambiguous:
            return None
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_FOUND")
    stored_as_ambiguous = MANDATE_LIMIT_PROVENANCE_AMBIGUOUS in matching_snapshot.field_gap_codes
    if stored_as_ambiguous:
        if matching_snapshot.portfolio_id != twin.portfolio_id:
            raise DpmMandateSourceIncompleteError("DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_FOUND")
        return matching_snapshot
    if submitted_as_ambiguous:
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_FOUND")
    return None


def run_mandate_monitoring_once(
    *,
    repository: DpmMandateRepository,
    mandate_ids: list[str],
    as_of_date: date,
    filters: dict[str, str],
    tenant_id: str,
) -> DpmMonitoringRun:
    requested_at = datetime.now(timezone.utc)
    monitoring_run_id = monitoring_run_id_for(requested_at)
    accumulator = mandate_monitoring_support.aggregate_monitoring_results(
        tenant_id=tenant_id,
        mandate_ids=mandate_ids,
        as_of_date=as_of_date,
        monitoring_run_id=monitoring_run_id,
        resolve_twin=lambda mandate_id: get_latest_mandate(
            repository=repository,
            mandate_id=mandate_id,
            tenant_id=tenant_id,
        ),
        persist_result=lambda twin, snapshot, exceptions: persist_mandate_health_evidence(
            repository=repository,
            tenant_id=tenant_id,
            health_snapshot=snapshot,
            monitoring_exceptions=exceptions,
        ),
    )

    run = build_monitoring_run(
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
    tenant_id: str,
) -> DpmMonitoringRun:
    run = repository.get_monitoring_run(monitoring_run_id=monitoring_run_id, tenant_id=tenant_id)
    if run is None:
        raise DpmMonitoringRunNotFoundError("DPM_MONITORING_RUN_NOT_FOUND")
    return run


def list_monitoring_runs(
    *,
    repository: DpmMandateRepository,
    status: Optional[str],
    limit: int,
    cursor: Optional[str],
    tenant_id: str,
) -> tuple[list[DpmMonitoringRun], Optional[str]]:
    return repository.list_monitoring_runs(
        status=status, limit=limit, cursor=cursor, tenant_id=tenant_id
    )


def list_monitoring_exceptions(
    *,
    tenant_id: str,
    repository: DpmMandateRepository,
    mandate_id: Optional[str],
    portfolio_id: Optional[str],
    state: Optional[str],
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmMonitoringException], Optional[str]]:
    return repository.list_monitoring_exceptions(
        tenant_id=tenant_id,
        monitoring_run_id=None,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        state=state,
        limit=limit,
        cursor=cursor,
    )


def resolve_monitoring_exception(
    *,
    tenant_id: str,
    repository: DpmMandateRepository,
    exception_id: str,
    resolution_reason: str,
) -> DpmMonitoringException:
    resolved = repository.resolve_monitoring_exception(
        tenant_id=tenant_id,
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
    tenant_id: str,
    portfolio_manager_id: Optional[str],
    book_id: Optional[str],
    as_of_date: Optional[date],
    health_state: Optional[str],
    limit: int,
) -> DpmCommandCenterSummary:
    # Fenced in the query rather than after the fetch. This previously read
    # every tenant's runs and narrowed them in Python, so the caller's own
    # page size was spent on rows they may not see - a correctness bug that
    # presents as a short result rather than as a leak.
    runs, _ = repository.list_monitoring_runs(
        status=None, limit=200, cursor=None, tenant_id=tenant_id
    )
    latest_run = latest_command_center_run(
        runs,
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=as_of_date,
    )
    active_exceptions, _ = repository.list_monitoring_exceptions(
        tenant_id=tenant_id,
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
    tenant_id: str,
) -> DpmMandateDiff:
    versions = repository.list_mandate_versions(mandate_id=mandate_id, tenant_id=tenant_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")

    return build_mandate_diff_for_versions(
        mandate_id=mandate_id,
        versions=versions,
        from_version=from_version,
        to_version=to_version,
    )
