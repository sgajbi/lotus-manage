from __future__ import annotations

from src.core.mandate_repository import DpmMandateRepository, MandateSnapshotProducer
from src.core.mandates import (
    MANDATE_LIMIT_PROVENANCE_AMBIGUOUS,
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)


def persist_mandate_health_evidence(
    *,
    repository: DpmMandateRepository,
    health_snapshot: DpmMandateHealthSnapshot,
    monitoring_exceptions: list[DpmMonitoringException],
    tenant_id: str,
    twin: DpmMandateDigitalTwin | None = None,
    mandate_producer_kind: MandateSnapshotProducer = "CALLER_SUPPLIED",
    verified_retained_projection: bool = False,
) -> None:
    caller_projection = (
        twin is not None
        and mandate_producer_kind == "CALLER_SUPPLIED"
        and MANDATE_LIMIT_PROVENANCE_AMBIGUOUS in twin.field_gap_codes
    )
    if caller_projection and not verified_retained_projection:
        raise ValueError("DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_VERIFIED")
    if twin is not None and not caller_projection:
        repository.save_mandate_snapshot(
            twin,
            tenant_id=tenant_id,
            producer_kind=mandate_producer_kind,
        )
    repository.save_health_snapshot(health_snapshot, tenant_id=tenant_id)
    for exception in monitoring_exceptions:
        repository.save_monitoring_exception(exception, tenant_id=tenant_id)


__all__ = ["persist_mandate_health_evidence"]
