from __future__ import annotations

from datetime import date, datetime

from src.core.mandates import DpmMonitoringException, DpmMonitoringRun


def monitoring_run_id_for(requested_at: datetime) -> str:
    return f"dmr_{requested_at.strftime('%Y%m%d_%H%M%S_%f')}"


def increment_distribution(
    distribution: dict[str, int],
    key: str,
) -> None:
    distribution[key] = distribution.get(key, 0) + 1


def exceptions_for_monitoring_run(
    exceptions: list[DpmMonitoringException],
    *,
    monitoring_run_id: str,
) -> list[DpmMonitoringException]:
    return [
        exception.model_copy(update={"monitoring_run_id": monitoring_run_id})
        for exception in exceptions
    ]


def build_monitoring_run(
    *,
    monitoring_run_id: str,
    as_of_date: date,
    requested_at: datetime,
    completed_at: datetime,
    mandate_ids: list[str],
    filters: dict[str, str],
    health_distribution: dict[str, int],
    exception_count: int,
    source_readiness_summary: dict[str, int],
) -> DpmMonitoringRun:
    return DpmMonitoringRun(
        monitoring_run_id=monitoring_run_id,
        as_of_date=as_of_date,
        requested_at=requested_at,
        completed_at=completed_at,
        status="SUCCEEDED",
        mandate_ids=mandate_ids,
        filters=filters,
        total_mandates=len(mandate_ids),
        health_distribution=health_distribution,
        exception_count=exception_count,
        source_readiness_summary=source_readiness_summary,
    )


__all__ = [
    "build_monitoring_run",
    "exceptions_for_monitoring_run",
    "increment_distribution",
    "monitoring_run_id_for",
]
