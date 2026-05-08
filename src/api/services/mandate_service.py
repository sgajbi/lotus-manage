from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmCommandCenterAttentionBucket,
    DpmCommandCenterRecommendedAction,
    DpmCommandCenterSummary,
    DpmCommandCenterSupportability,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    MonitoringSeverity,
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
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse


class DpmMandateNotFoundError(LookupError):
    pass


class DpmMandateDiffUnavailableError(LookupError):
    pass


class DpmMandateSourceUnavailableError(RuntimeError):
    pass


class DpmMandateSourceIncompleteError(RuntimeError):
    pass


class DpmMandateHealthNotFoundError(LookupError):
    pass


class DpmMonitoringRunNotFoundError(LookupError):
    pass


class DpmMandateFieldChange(BaseModel):
    field_path: str = Field(
        description="Dot-separated mandate digital-twin field path that changed.",
        examples=["constraints.turnover_budget"],
    )
    previous_value: Any = Field(
        description="Value from the older mandate version.",
        examples=["0.1000000000"],
    )
    current_value: Any = Field(
        description="Value from the newer mandate version.",
        examples=["0.1500000000"],
    )
    materiality: str = Field(
        description="Business materiality of the field change for DPM oversight.",
        examples=["HIGH"],
    )


class DpmMandateDiff(BaseModel):
    mandate_id: str = Field(
        description="Discretionary mandate identifier whose versions were compared.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    compared_at: datetime = Field(
        description="UTC timestamp when lotus-manage generated the diff.",
        examples=["2026-05-03T08:30:00Z"],
    )
    from_version: str = Field(
        description="Older mandate version used as the comparison baseline.",
        examples=["2"],
    )
    to_version: str = Field(
        description="Newer mandate version used as the comparison target.",
        examples=["3"],
    )
    changed_fields: list[DpmMandateFieldChange] = Field(
        description="Changed mandate fields, ordered by field path for deterministic review.",
    )


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

    twin = compile_mandate_digital_twin_from_core(
        mandate=mandate,
        model_targets=model_targets,
        as_of_date=as_of_date,
        reference_currency=reference_currency,
    )
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
    )
    health_snapshot = calculate_mandate_health(health_input)
    monitoring_exceptions = monitoring_exceptions_from_health(
        health_snapshot,
        source_lineage=twin.source_lineage,
    )

    repository.save_mandate_snapshot(twin)
    repository.save_health_snapshot(health_snapshot)
    for exception in monitoring_exceptions:
        repository.save_monitoring_exception(exception)

    return DpmMandateRefreshResult(
        twin=twin,
        health_snapshot=health_snapshot,
        monitoring_exceptions=monitoring_exceptions,
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
    snapshot = calculate_mandate_health(health_input)
    exceptions = monitoring_exceptions_from_health(
        snapshot,
        source_lineage=health_input.twin.source_lineage,
    )
    repository.save_mandate_snapshot(health_input.twin)
    repository.save_health_snapshot(snapshot)
    for exception in exceptions:
        repository.save_monitoring_exception(exception)
    return snapshot


def run_mandate_monitoring_once(
    *,
    repository: DpmMandateRepository,
    mandate_ids: list[str],
    as_of_date: date,
    filters: dict[str, str],
) -> DpmMonitoringRun:
    requested_at = datetime.now(timezone.utc)
    monitoring_run_id = f"dmr_{requested_at.strftime('%Y%m%d_%H%M%S_%f')}"
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
        health_distribution[snapshot.health_state.value] = (
            health_distribution.get(snapshot.health_state.value, 0) + 1
        )
        source_readiness_summary[snapshot.source_readiness_state] = (
            source_readiness_summary.get(snapshot.source_readiness_state, 0) + 1
        )
        exceptions = monitoring_exceptions_from_health(
            snapshot,
            source_lineage=twin.source_lineage,
        )
        exception_count += len(exceptions)
        for exception in exceptions:
            repository.save_monitoring_exception(
                exception.model_copy(update={"monitoring_run_id": monitoring_run_id})
            )

    run = DpmMonitoringRun(
        monitoring_run_id=monitoring_run_id,
        as_of_date=as_of_date,
        requested_at=requested_at,
        completed_at=datetime.now(timezone.utc),
        status="SUCCEEDED",
        mandate_ids=mandate_ids,
        filters=filters,
        total_mandates=len(mandate_ids),
        health_distribution=health_distribution,
        exception_count=exception_count,
        source_readiness_summary=source_readiness_summary,
    )
    repository.save_monitoring_run(run)
    return run


def mandate_ids_from_pm_book_membership(
    *,
    repository: DpmMandateRepository,
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> list[str]:
    mandate_ids: list[str] = []
    missing_portfolio_ids: list[str] = []
    for member in membership.members:
        twin = repository.get_latest_mandate_by_portfolio(portfolio_id=member.portfolio_id)
        if twin is None:
            missing_portfolio_ids.append(member.portfolio_id)
            continue
        mandate_ids.append(twin.mandate_id)

    if missing_portfolio_ids:
        raise DpmMandateSourceIncompleteError("DPM_PM_BOOK_MANDATE_SNAPSHOT_MISSING")
    if not mandate_ids:
        raise DpmMandateSourceIncompleteError("DPM_PM_BOOK_MANDATE_SNAPSHOT_EMPTY")
    return mandate_ids


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

    health_distribution = dict(latest_run.health_distribution) if latest_run else {}
    if health_state is not None:
        health_distribution = {health_state: health_distribution.get(health_state, 0)}

    partial_reasons: list[str] = []
    if latest_run is None:
        partial_reasons.append("NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS")
    if portfolio_manager_id is None and book_id is None:
        partial_reasons.append("PM_BOOK_DISCOVERY_NOT_YET_SOURCED")
    if len(active_exceptions) >= limit:
        partial_reasons.append("ATTENTION_QUEUE_LIMIT_REACHED")

    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"] = "COMPLETE"
    if latest_run is None:
        completeness = "EMPTY"
    elif partial_reasons:
        completeness = "PARTIAL"
    supportability_state, supportability_reason = _command_center_supportability_state(
        latest_run=latest_run,
        completeness=completeness,
        partial_reasons=partial_reasons,
    )

    return DpmCommandCenterSummary(
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=as_of_date or (latest_run.as_of_date if latest_run else None),
        selected_health_state=MandateHealthState(health_state)
        if health_state is not None
        else None,
        evaluated_mandates=latest_run.total_mandates if latest_run else 0,
        monitored_mandate_ids=list(latest_run.mandate_ids) if latest_run else [],
        health_distribution=health_distribution,
        source_readiness_summary=dict(latest_run.source_readiness_summary) if latest_run else {},
        active_exception_count=len(active_exceptions),
        attention_buckets=_attention_buckets(active_exceptions),
        recommended_actions=_recommended_actions(active_exceptions),
        latest_monitoring_run=latest_run,
        supportability=DpmCommandCenterSupportability(
            state=supportability_state,
            data_completeness_state=completeness,
            reason=supportability_reason,
            generated_at=datetime.now(timezone.utc),
            source_run_id=latest_run.monitoring_run_id if latest_run else None,
            partial_readiness_reasons=partial_reasons,
        ),
    )


def _command_center_supportability_state(
    *,
    latest_run: Optional[DpmMonitoringRun],
    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"],
    partial_reasons: list[str],
) -> tuple[Literal["READY", "PARTIAL", "EMPTY", "DEGRADED", "BLOCKED"], str]:
    if latest_run is None or completeness == "EMPTY":
        return "EMPTY", "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS"

    source_states = {state.upper() for state in latest_run.source_readiness_summary}
    if source_states.intersection({"INCOMPLETE", "UNAVAILABLE", "BLOCKED"}):
        return "BLOCKED", "COMMAND_CENTER_SOURCE_READINESS_BLOCKED"
    if source_states.intersection({"DEGRADED", "STALE"}):
        return "DEGRADED", "COMMAND_CENTER_SOURCE_READINESS_DEGRADED"
    if completeness == "PARTIAL" or partial_reasons:
        return "PARTIAL", partial_reasons[0] if partial_reasons else "COMMAND_CENTER_PARTIAL"
    return "READY", "COMMAND_CENTER_READY"


def _run_matches_command_center_filters(
    run: DpmMonitoringRun,
    *,
    tenant_id: Optional[str],
    portfolio_manager_id: Optional[str],
    book_id: Optional[str],
    as_of_date: Optional[date],
) -> bool:
    if as_of_date is not None and run.as_of_date != as_of_date:
        return False
    expected_filters = {
        "tenant_id": tenant_id,
        "portfolio_manager_id": portfolio_manager_id,
        "book_id": book_id,
    }
    return all(
        value is None or run.filters.get(key) == value for key, value in expected_filters.items()
    )


def _attention_buckets(
    exceptions: list[DpmMonitoringException],
) -> list[DpmCommandCenterAttentionBucket]:
    bucket_counts: dict[tuple[str, str, str], int] = {}
    bucket_reason_counts: dict[tuple[str, str, str], dict[str, int]] = {}
    for exception in exceptions:
        key = (
            exception.dimension.value,
            exception.severity.value,
            exception.recommended_action.value,
        )
        bucket_counts[key] = bucket_counts.get(key, 0) + 1
        reason_counts = bucket_reason_counts.setdefault(key, {})
        reason_counts[exception.reason_code] = reason_counts.get(exception.reason_code, 0) + 1

    return [
        DpmCommandCenterAttentionBucket(
            dimension=MandateHealthDimension(dimension),
            severity=MonitoringSeverity(severity),
            recommended_action=MandateRecommendedAction(recommended_action),
            exception_count=exception_count,
            top_reason_codes=[
                reason_code
                for reason_code, _ in sorted(
                    bucket_reason_counts[(dimension, severity, recommended_action)].items(),
                    key=lambda item: (-item[1], item[0]),
                )[:3]
            ],
        )
        for (dimension, severity, recommended_action), exception_count in sorted(
            bucket_counts.items(),
            key=lambda item: (
                -_severity_rank(item[0][1]),
                -item[1],
                item[0][0],
            ),
        )
    ]


def _recommended_actions(
    exceptions: list[DpmMonitoringException],
) -> list[DpmCommandCenterRecommendedAction]:
    action_counts: dict[str, int] = {}
    action_highest_severity: dict[str, str] = {}
    for exception in exceptions:
        action = exception.recommended_action.value
        action_counts[action] = action_counts.get(action, 0) + 1
        current_highest = action_highest_severity.setdefault(action, exception.severity.value)
        if _severity_rank(exception.severity.value) > _severity_rank(current_highest):
            action_highest_severity[action] = exception.severity.value

    return [
        DpmCommandCenterRecommendedAction(
            recommended_action=MandateRecommendedAction(action),
            exception_count=exception_count,
            highest_severity=MonitoringSeverity(action_highest_severity[action]),
        )
        for action, exception_count in sorted(
            action_counts.items(),
            key=lambda item: (
                -_severity_rank(action_highest_severity[item[0]]),
                -item[1],
                item[0],
            ),
        )
    ]


def _severity_rank(severity: str) -> int:
    return {"CRITICAL": 3, "WARNING": 2, "INFO": 1}.get(severity, 0)


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

    return DpmMandateDiff(
        mandate_id=mandate_id,
        compared_at=datetime.now(timezone.utc),
        from_version=previous.mandate_version,
        to_version=current.mandate_version,
        changed_fields=_diff_payloads(
            previous.model_dump(mode="json"),
            current.model_dump(mode="json"),
        ),
    )


def _diff_payloads(
    previous: dict[str, Any], current: dict[str, Any]
) -> list[DpmMandateFieldChange]:
    changes: list[DpmMandateFieldChange] = []
    for field_path, previous_value, current_value in _iter_changed_fields(previous, current):
        changes.append(
            DpmMandateFieldChange(
                field_path=field_path,
                previous_value=previous_value,
                current_value=current_value,
                materiality=_materiality_for_field(field_path),
            )
        )
    return sorted(changes, key=lambda change: change.field_path)


def _iter_changed_fields(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    prefix: str = "",
) -> list[tuple[str, Any, Any]]:
    ignored = {"source_lineage"}
    changes: list[tuple[str, Any, Any]] = []
    keys = sorted((set(previous) | set(current)) - ignored)
    for key in keys:
        field_path = f"{prefix}.{key}" if prefix else key
        previous_value = previous.get(key)
        current_value = current.get(key)
        if isinstance(previous_value, dict) and isinstance(current_value, dict):
            changes.extend(_iter_changed_fields(previous_value, current_value, prefix=field_path))
            continue
        if previous_value != current_value:
            changes.append((field_path, previous_value, current_value))
    return changes


def _materiality_for_field(field_path: str) -> str:
    high_prefixes = (
        "constraints.",
        "risk_profile",
        "investment_objective",
        "model_portfolio_id",
        "model_portfolio_version",
        "time_horizon",
    )
    if field_path.startswith(high_prefixes):
        return "HIGH"
    if field_path in {"mandate_version", "as_of_date", "field_gap_codes"}:
        return "MEDIUM"
    return "LOW"
