from __future__ import annotations

from collections.abc import Callable
from datetime import date

from src.api.services.mandate_monitoring_run import (
    DpmMonitoringRunAccumulator,
    calculate_monitoring_run_mandate_result,
)
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)

ResolveMandate = Callable[[str], DpmMandateDigitalTwin]
PersistMonitoringResult = Callable[
    [DpmMandateDigitalTwin, DpmMandateHealthSnapshot, list[DpmMonitoringException]],
    None,
]


def aggregate_monitoring_results(
    *,
    mandate_ids: list[str],
    as_of_date: date,
    monitoring_run_id: str,
    resolve_twin: ResolveMandate,
    persist_result: PersistMonitoringResult,
    tenant_id: str,
) -> DpmMonitoringRunAccumulator:
    accumulator = DpmMonitoringRunAccumulator.empty()
    for mandate_id in mandate_ids:
        twin = resolve_twin(mandate_id)
        result = calculate_monitoring_run_mandate_result(
            twin=twin,
            as_of_date=as_of_date,
            monitoring_run_id=monitoring_run_id,
            tenant_id=tenant_id,
        )
        persist_result(twin, result.health_snapshot, result.monitoring_exceptions)
        accumulator.record(result)
    return accumulator


__all__ = ["aggregate_monitoring_results"]
