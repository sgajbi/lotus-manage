from datetime import date, datetime
from typing import Literal

from src.core.mandates import (
    DpmCommandCenterAttentionBucket,
    DpmCommandCenterRecommendedAction,
    DpmCommandCenterSummary,
    DpmCommandCenterSupportability,
    DpmMonitoringException,
    DpmMonitoringRun,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    MonitoringSeverity,
)


def command_center_supportability_state(
    *,
    latest_run: DpmMonitoringRun | None,
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


def run_matches_command_center_filters(
    run: DpmMonitoringRun,
    *,
    tenant_id: str | None,
    portfolio_manager_id: str | None,
    book_id: str | None,
    as_of_date: date | None,
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


def latest_command_center_run(
    runs: list[DpmMonitoringRun],
    *,
    tenant_id: str | None,
    portfolio_manager_id: str | None,
    book_id: str | None,
    as_of_date: date | None,
) -> DpmMonitoringRun | None:
    return next(
        (
            run
            for run in runs
            if run_matches_command_center_filters(
                run,
                tenant_id=tenant_id,
                portfolio_manager_id=portfolio_manager_id,
                book_id=book_id,
                as_of_date=as_of_date,
            )
        ),
        None,
    )


def build_command_center_summary(
    *,
    tenant_id: str | None,
    portfolio_manager_id: str | None,
    book_id: str | None,
    as_of_date: date | None,
    health_state: str | None,
    latest_run: DpmMonitoringRun | None,
    active_exceptions: list[DpmMonitoringException],
    limit: int,
    generated_at: datetime,
) -> DpmCommandCenterSummary:
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
    supportability_state, supportability_reason = command_center_supportability_state(
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
        attention_buckets=attention_buckets(active_exceptions),
        recommended_actions=recommended_actions(active_exceptions),
        latest_monitoring_run=latest_run,
        supportability=DpmCommandCenterSupportability(
            state=supportability_state,
            data_completeness_state=completeness,
            reason=supportability_reason,
            generated_at=generated_at,
            source_run_id=latest_run.monitoring_run_id if latest_run else None,
            partial_readiness_reasons=partial_reasons,
        ),
    )


def attention_buckets(
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
                -severity_rank(item[0][1]),
                -item[1],
                item[0][0],
            ),
        )
    ]


def recommended_actions(
    exceptions: list[DpmMonitoringException],
) -> list[DpmCommandCenterRecommendedAction]:
    action_counts: dict[str, int] = {}
    action_highest_severity: dict[str, str] = {}
    for exception in exceptions:
        action = exception.recommended_action.value
        action_counts[action] = action_counts.get(action, 0) + 1
        current_highest = action_highest_severity.setdefault(action, exception.severity.value)
        if severity_rank(exception.severity.value) > severity_rank(current_highest):
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
                -severity_rank(action_highest_severity[item[0]]),
                -item[1],
                item[0],
            ),
        )
    ]


def severity_rank(severity: str) -> int:
    return {"CRITICAL": 3, "WARNING": 2, "INFO": 1}.get(severity, 0)


__all__ = [
    "attention_buckets",
    "build_command_center_summary",
    "command_center_supportability_state",
    "latest_command_center_run",
    "recommended_actions",
    "run_matches_command_center_filters",
    "severity_rank",
]
