from __future__ import annotations

from dataclasses import dataclass

from src.core.mandates import (
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    calculate_mandate_health,
    monitoring_exceptions_from_health,
)


@dataclass(frozen=True)
class DpmMandateHealthCalculationResult:
    snapshot: DpmMandateHealthSnapshot
    monitoring_exceptions: list[DpmMonitoringException]


def calculate_mandate_health_result(
    health_input: DpmMandateHealthInput, *, tenant_id: str
) -> DpmMandateHealthCalculationResult:
    snapshot = calculate_mandate_health(health_input, tenant_id=tenant_id)
    return DpmMandateHealthCalculationResult(
        snapshot=snapshot,
        monitoring_exceptions=monitoring_exceptions_from_health(
            snapshot,
            source_lineage=health_input.twin.source_lineage,
        ),
    )


__all__ = [
    "DpmMandateHealthCalculationResult",
    "calculate_mandate_health_result",
]
