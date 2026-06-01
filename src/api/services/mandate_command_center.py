from datetime import date
from typing import Literal

from src.core.mandates import (
    DpmCommandCenterAttentionBucket,
    DpmCommandCenterRecommendedAction,
    DpmMonitoringException,
    DpmMonitoringRun,
    MandateHealthDimension,
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
    "command_center_supportability_state",
    "recommended_actions",
    "run_matches_command_center_filters",
    "severity_rank",
]
