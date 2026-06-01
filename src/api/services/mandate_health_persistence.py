from __future__ import annotations

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)


def persist_mandate_health_evidence(
    *,
    repository: DpmMandateRepository,
    health_snapshot: DpmMandateHealthSnapshot,
    monitoring_exceptions: list[DpmMonitoringException],
    twin: DpmMandateDigitalTwin | None = None,
) -> None:
    if twin is not None:
        repository.save_mandate_snapshot(twin)
    repository.save_health_snapshot(health_snapshot)
    for exception in monitoring_exceptions:
        repository.save_monitoring_exception(exception)


__all__ = ["persist_mandate_health_evidence"]
