from src.core.common.canonical import hash_canonical_payload
from src.core.portfolio_memory.mandate_projection import (
    mandate_exception_event,
    mandate_health_event,
)
from tests.unit.dpm.api.test_portfolio_memory_api import (
    _health_snapshot,
    _mandate_twin,
    _monitoring_exception,
)


def test_mandate_health_event_projects_source_lineage_and_health_evidence() -> None:
    health_snapshot = _health_snapshot()

    event = mandate_health_event(
        health_snapshot=health_snapshot,
        source_lineage=_mandate_twin().source_lineage,
    )

    assert event.event_type == "MANDATE_HEALTH_SNAPSHOT"
    assert event.source_type == "DPM_MANDATE_HEALTH_SNAPSHOT"
    assert event.supportability_state == "PENDING_REVIEW"
    assert event.reason_codes == ["ALLOCATION_DRIFT_REVIEW"]
    assert event.source_refs[0].source_system == "lotus-core"
    assert event.source_refs[0].source_type == "CoreMandateBinding"
    assert event.artifact_refs[0].source_id == "core:mandate-binding:MANDATE_PB_SG_GLOBAL_BAL_001"
    assert event.content_hash == hash_canonical_payload(health_snapshot.model_dump(mode="json"))
    assert event.metadata["health_score"] == 72
    assert event.metadata["dimension_count"] == 1


def test_mandate_exception_event_projects_monitoring_run_and_threshold_metadata() -> None:
    exception = _monitoring_exception()

    event = mandate_exception_event(exception)

    assert event.event_type == "MANDATE_MONITORING_EXCEPTION"
    assert event.source_type == "DPM_MONITORING_EXCEPTION"
    assert event.supportability_state == "DEGRADED"
    assert event.reason_codes == ["ALLOCATION_DRIFT", "ALLOCATION_DRIFT_REVIEW", "WARNING"]
    assert event.artifact_refs[0].source_type == "DPM_MONITORING_RUN"
    assert event.artifact_refs[0].source_id == "dmr_memory_001"
    assert event.content_hash == hash_canonical_payload(exception.model_dump(mode="json"))
    assert event.metadata["monitoring_run_id"] == "dmr_memory_001"
    assert event.metadata["measured_value"] == "0.08"
    assert event.metadata["threshold_value"] == "0.05"
    assert event.metadata["resolved_at"] is None
