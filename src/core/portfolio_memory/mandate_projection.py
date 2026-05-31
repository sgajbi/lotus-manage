"""Mandate source-event projection helpers for portfolio memory."""

from src.core.common.canonical import hash_canonical_payload
from src.core.mandates import (
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmSourceProductLineage,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.source_refs import from_source_product_lineage
from src.core.portfolio_memory.supportability import (
    monitoring_exception_state,
    source_supportability_state,
)


def mandate_health_event(
    *,
    health_snapshot: DpmMandateHealthSnapshot,
    source_lineage: list[DpmSourceProductLineage],
) -> DpmPortfolioMemoryEvent:
    reason_codes = sorted(
        {reason.reason_code for reason in health_snapshot.top_reasons if reason.reason_code}
        | {score.reason_code for score in health_snapshot.dimension_scores if score.reason_code}
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:mandate:{health_snapshot.mandate_id}:health:{health_snapshot.health_snapshot_id}",
        event_type="MANDATE_HEALTH_SNAPSHOT",
        event_time=health_snapshot.calculated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
        source_id=health_snapshot.health_snapshot_id,
        status=health_snapshot.health_state.value,
        supportability_state=source_supportability_state(health_snapshot.health_state.value),
        summary=(
            f"Mandate health snapshot {health_snapshot.health_snapshot_id} calculated as "
            f"{health_snapshot.health_state.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[from_source_product_lineage(ref) for ref in source_lineage],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_MANDATE_HEALTH_EVIDENCE_REF",
                source_id=evidence_ref,
            )
            for evidence_ref in health_snapshot.evidence_refs
        ],
        content_hash=hash_canonical_payload(health_snapshot.model_dump(mode="json")),
        metadata={
            "mandate_id": health_snapshot.mandate_id,
            "as_of_date": health_snapshot.as_of_date.isoformat(),
            "health_score": health_snapshot.health_score,
            "recommended_action": health_snapshot.recommended_action.value,
            "source_readiness_state": health_snapshot.source_readiness_state,
            "dimension_count": len(health_snapshot.dimension_scores),
        },
    )


def mandate_exception_event(
    exception: DpmMonitoringException,
) -> DpmPortfolioMemoryEvent:
    reason_codes = sorted(
        {
            exception.reason_code,
            exception.dimension.value,
            exception.severity.value,
        }
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:mandate:{exception.mandate_id}:exception:{exception.exception_id}",
        event_type="MANDATE_MONITORING_EXCEPTION",
        event_time=exception.detected_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_MONITORING_EXCEPTION",
        source_id=exception.exception_id,
        status=exception.state,
        supportability_state=monitoring_exception_state(exception),
        summary=(
            f"Mandate monitoring exception {exception.exception_id} is {exception.state} "
            f"for {exception.dimension.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[from_source_product_lineage(ref) for ref in exception.source_lineage],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_MONITORING_RUN",
                source_id=exception.monitoring_run_id,
            )
        ]
        if exception.monitoring_run_id is not None
        else [],
        content_hash=hash_canonical_payload(exception.model_dump(mode="json")),
        metadata={
            "mandate_id": exception.mandate_id,
            "monitoring_run_id": exception.monitoring_run_id,
            "as_of_date": exception.as_of_date.isoformat(),
            "dimension": exception.dimension.value,
            "severity": exception.severity.value,
            "recommended_action": exception.recommended_action.value,
            "measured_value": str(exception.measured_value)
            if exception.measured_value is not None
            else None,
            "threshold_value": str(exception.threshold_value)
            if exception.threshold_value is not None
            else None,
            "resolved_at": exception.resolved_at.isoformat()
            if exception.resolved_at is not None
            else None,
            "resolution_reason": exception.resolution_reason,
        },
    )
