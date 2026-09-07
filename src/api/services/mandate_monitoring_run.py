from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
    calculate_mandate_health,
    monitoring_exceptions_from_health,
)


@dataclass(frozen=True)
class DpmMonitoringRunMandateResult:
    health_snapshot: DpmMandateHealthSnapshot
    monitoring_exceptions: list[DpmMonitoringException]


@dataclass
class DpmMonitoringRunAccumulator:
    health_distribution: dict[str, int]
    source_readiness_summary: dict[str, int]
    exception_count: int = 0

    @classmethod
    def empty(cls) -> "DpmMonitoringRunAccumulator":
        return cls(health_distribution={}, source_readiness_summary={})

    def record(self, result: DpmMonitoringRunMandateResult) -> None:
        increment_distribution(
            self.health_distribution,
            result.health_snapshot.health_state.value,
        )
        increment_distribution(
            self.source_readiness_summary,
            result.health_snapshot.source_readiness_state,
        )
        self.exception_count += len(result.monitoring_exceptions)


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


def calculate_monitoring_run_mandate_result(
    *,
    twin: DpmMandateDigitalTwin,
    as_of_date: date,
    monitoring_run_id: str,
    tenant_id: str,
) -> DpmMonitoringRunMandateResult:
    snapshot = calculate_mandate_health(
        DpmMandateHealthInput(twin=twin.model_copy(update={"as_of_date": as_of_date})),
        tenant_id=tenant_id,
    )
    exceptions = monitoring_exceptions_from_health(
        snapshot,
        source_lineage=twin.source_lineage,
    )
    return DpmMonitoringRunMandateResult(
        health_snapshot=snapshot,
        monitoring_exceptions=exceptions_for_monitoring_run(
            exceptions,
            monitoring_run_id=monitoring_run_id,
        ),
    )


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
    "DpmMonitoringRunAccumulator",
    "DpmMonitoringRunMandateResult",
    "build_monitoring_run",
    "calculate_monitoring_run_mandate_result",
    "exceptions_for_monitoring_run",
    "increment_distribution",
    "monitoring_run_id_for",
]
