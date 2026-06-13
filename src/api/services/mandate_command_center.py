from dataclasses import dataclass
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

CommandCenterSupportabilityState = Literal["READY", "PARTIAL", "EMPTY", "DEGRADED", "BLOCKED"]
CommandCenterSupportabilityPosture = tuple[CommandCenterSupportabilityState, str]
_BLOCKING_SOURCE_READINESS_STATES = {"INCOMPLETE", "UNAVAILABLE", "BLOCKED"}
_DEGRADED_SOURCE_READINESS_STATES = {"DEGRADED", "STALE"}


@dataclass(frozen=True)
class _CommandCenterReadModel:
    health_distribution: dict[str, int]
    partial_reasons: list[str]
    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"]
    supportability_state: CommandCenterSupportabilityState
    supportability_reason: str


def command_center_supportability_state(
    *,
    latest_run: DpmMonitoringRun | None,
    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"],
    partial_reasons: list[str],
) -> CommandCenterSupportabilityPosture:
    empty_posture = _empty_command_center_supportability(
        latest_run=latest_run,
        completeness=completeness,
    )
    if empty_posture is not None:
        return empty_posture
    assert latest_run is not None

    source_posture = _source_readiness_supportability_posture(
        source_readiness_summary=latest_run.source_readiness_summary
    )
    if source_posture is not None:
        return source_posture
    partial_posture = _partial_command_center_supportability(
        completeness=completeness,
        partial_reasons=partial_reasons,
    )
    if partial_posture is not None:
        return partial_posture
    return "READY", "COMMAND_CENTER_READY"


def _empty_command_center_supportability(
    *,
    latest_run: DpmMonitoringRun | None,
    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"],
) -> CommandCenterSupportabilityPosture | None:
    if latest_run is None or completeness == "EMPTY":
        return "EMPTY", "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS"
    return None


def _partial_command_center_supportability(
    *,
    completeness: Literal["COMPLETE", "PARTIAL", "EMPTY"],
    partial_reasons: list[str],
) -> CommandCenterSupportabilityPosture | None:
    if completeness == "PARTIAL" or partial_reasons:
        return "PARTIAL", partial_reasons[0] if partial_reasons else "COMMAND_CENTER_PARTIAL"
    return None


def _source_readiness_supportability_posture(
    *,
    source_readiness_summary: dict[str, int],
) -> CommandCenterSupportabilityPosture | None:
    source_states = _normalized_source_readiness_states(source_readiness_summary)
    if _source_readiness_blocks_command_center(source_states):
        return "BLOCKED", "COMMAND_CENTER_SOURCE_READINESS_BLOCKED"
    if _source_readiness_degrades_command_center(source_states):
        return "DEGRADED", "COMMAND_CENTER_SOURCE_READINESS_DEGRADED"
    return None


def _normalized_source_readiness_states(source_readiness_summary: dict[str, int]) -> set[str]:
    return {state.upper() for state in source_readiness_summary}


def _source_readiness_blocks_command_center(source_states: set[str]) -> bool:
    return bool(source_states.intersection(_BLOCKING_SOURCE_READINESS_STATES))


def _source_readiness_degrades_command_center(source_states: set[str]) -> bool:
    return bool(source_states.intersection(_DEGRADED_SOURCE_READINESS_STATES))


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


def command_center_health_distribution(
    *,
    latest_run: DpmMonitoringRun | None,
    health_state: str | None,
) -> dict[str, int]:
    health_distribution = dict(latest_run.health_distribution) if latest_run else {}
    if health_state is None:
        return health_distribution
    return {health_state: health_distribution.get(health_state, 0)}


def command_center_partial_reasons(
    *,
    latest_run: DpmMonitoringRun | None,
    portfolio_manager_id: str | None,
    book_id: str | None,
    active_exception_count: int,
    limit: int,
) -> list[str]:
    partial_reasons: list[str] = []
    if latest_run is None:
        partial_reasons.append("NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS")
    if portfolio_manager_id is None and book_id is None:
        partial_reasons.append("PM_BOOK_DISCOVERY_NOT_YET_SOURCED")
    if active_exception_count >= limit:
        partial_reasons.append("ATTENTION_QUEUE_LIMIT_REACHED")
    return partial_reasons


def command_center_completeness(
    *,
    latest_run: DpmMonitoringRun | None,
    partial_reasons: list[str],
) -> Literal["COMPLETE", "PARTIAL", "EMPTY"]:
    if latest_run is None:
        return "EMPTY"
    if partial_reasons:
        return "PARTIAL"
    return "COMPLETE"


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
    read_model = _command_center_read_model(
        health_state=health_state,
        latest_run=latest_run,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        active_exception_count=len(active_exceptions),
        limit=limit,
    )

    return DpmCommandCenterSummary(
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=_command_center_as_of_date(as_of_date=as_of_date, latest_run=latest_run),
        selected_health_state=_selected_health_state(health_state),
        evaluated_mandates=_evaluated_mandates(latest_run),
        monitored_mandate_ids=_monitored_mandate_ids(latest_run),
        health_distribution=read_model.health_distribution,
        source_readiness_summary=_source_readiness_summary(latest_run),
        active_exception_count=len(active_exceptions),
        attention_buckets=attention_buckets(active_exceptions),
        recommended_actions=recommended_actions(active_exceptions),
        latest_monitoring_run=latest_run,
        supportability=DpmCommandCenterSupportability(
            state=read_model.supportability_state,
            data_completeness_state=read_model.completeness,
            reason=read_model.supportability_reason,
            generated_at=generated_at,
            source_run_id=latest_run.monitoring_run_id if latest_run else None,
            partial_readiness_reasons=read_model.partial_reasons,
        ),
    )


def _command_center_read_model(
    *,
    health_state: str | None,
    latest_run: DpmMonitoringRun | None,
    portfolio_manager_id: str | None,
    book_id: str | None,
    active_exception_count: int,
    limit: int,
) -> _CommandCenterReadModel:
    health_distribution = command_center_health_distribution(
        latest_run=latest_run,
        health_state=health_state,
    )
    partial_reasons = command_center_partial_reasons(
        latest_run=latest_run,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        active_exception_count=active_exception_count,
        limit=limit,
    )
    completeness = command_center_completeness(
        latest_run=latest_run,
        partial_reasons=partial_reasons,
    )
    supportability_state, supportability_reason = command_center_supportability_state(
        latest_run=latest_run,
        completeness=completeness,
        partial_reasons=partial_reasons,
    )
    return _CommandCenterReadModel(
        health_distribution=health_distribution,
        partial_reasons=partial_reasons,
        completeness=completeness,
        supportability_state=supportability_state,
        supportability_reason=supportability_reason,
    )


def _command_center_as_of_date(
    *,
    as_of_date: date | None,
    latest_run: DpmMonitoringRun | None,
) -> date | None:
    return as_of_date or (latest_run.as_of_date if latest_run else None)


def _selected_health_state(health_state: str | None) -> MandateHealthState | None:
    return MandateHealthState(health_state) if health_state is not None else None


def _evaluated_mandates(latest_run: DpmMonitoringRun | None) -> int:
    return latest_run.total_mandates if latest_run else 0


def _monitored_mandate_ids(latest_run: DpmMonitoringRun | None) -> list[str]:
    return list(latest_run.mandate_ids) if latest_run else []


def _source_readiness_summary(latest_run: DpmMonitoringRun | None) -> dict[str, int]:
    return dict(latest_run.source_readiness_summary) if latest_run else {}


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
    "command_center_completeness",
    "command_center_health_distribution",
    "command_center_partial_reasons",
    "command_center_supportability_state",
    "latest_command_center_run",
    "recommended_actions",
    "run_matches_command_center_filters",
    "severity_rank",
]
