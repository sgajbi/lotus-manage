"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone
from typing import Iterable

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmSourceProductLineage,
)
from src.core.outcomes.models import DpmOutcomeEvent, DpmOutcomeSourceRef, DpmPostTradeOutcomeReview
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceEventFamilyPosture,
    DpmPortfolioMemorySourceRef,
    PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
    PORTFOLIO_MEMORY_AUDIT_POLICY,
    PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
    PORTFOLIO_MEMORY_REDACTION_POLICY,
    PORTFOLIO_MEMORY_RETENTION_POLICY,
    PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    PortfolioMemorySupportabilityState,
)
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSourceRef,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
)
from src.core.waves.repository import DpmWaveRepository


def build_portfolio_memory(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    limit: int = 100,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose manage-owned portfolio memory without recalculating source truth."""

    generated_at = generated_at or datetime.now(timezone.utc)
    events: list[DpmPortfolioMemoryEvent] = []
    proof_packs = proof_pack_repository.list_proof_packs(portfolio_id=portfolio_id, limit=limit)
    for proof_pack in proof_packs:
        events.extend(_proof_pack_events(proof_pack))

    if mandate_repository is not None:
        events.extend(
            _mandate_events(
                portfolio_id=portfolio_id,
                mandate_repository=mandate_repository,
                limit=limit,
            )
        )

    for wave in _waves_for_portfolio(
        portfolio_id=portfolio_id,
        wave_repository=wave_repository,
        limit=limit,
    ):
        events.extend(_wave_events(wave=wave, portfolio_id=portfolio_id))

    outcome_reviews = outcome_review_repository.list_outcome_reviews(
        portfolio_id=portfolio_id,
        limit=limit,
    )
    for review in outcome_reviews:
        persisted_events = outcome_review_repository.list_events(
            outcome_review_id=review.outcome_review_id
        )
        events.extend(_outcome_review_events(review=review, persisted_events=persisted_events))

    events = _dedupe_and_sort(events)[:limit]
    event_type_counts = _counts(event.event_type for event in events)
    reason_codes = sorted({reason for event in events for reason in event.reason_codes})
    source_systems = sorted(
        {
            source_system
            for event in events
            for source_system in [
                event.source_system,
                *(ref.source_system for ref in event.source_refs),
            ]
            if source_system
        }
    )
    memory = DpmPortfolioMemory(
        portfolio_id=portfolio_id,
        event_count=len(events),
        supportability_state=_memory_state(events),
        event_type_counts=event_type_counts,
        source_systems=source_systems,
        reason_codes=reason_codes,
        governance_policy=_portfolio_memory_governance_policy(),
        source_event_family_posture=_source_event_family_posture(),
        events=events,
        content_hash="",
        generated_at=generated_at.isoformat(),
    )
    payload = memory.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmPortfolioMemory.model_validate(payload)


def _portfolio_memory_governance_policy() -> dict[str, str]:
    return {
        "event_identity_scheme": PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
        "retention_policy": PORTFOLIO_MEMORY_RETENTION_POLICY,
        "redaction_policy": PORTFOLIO_MEMORY_REDACTION_POLICY,
        "audit_policy": PORTFOLIO_MEMORY_AUDIT_POLICY,
        "access_classification": PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
        "source_authority_policy": PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    }


def _source_event_family_posture() -> list[DpmPortfolioMemorySourceEventFamilyPosture]:
    return [
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_health",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_HEALTH_SNAPSHOT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_HEALTH_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate health snapshots are projected from persisted mandate repository truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_monitoring_exception",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_MONITORING_EXCEPTION"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_MONITORING_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate monitoring exceptions are projected from persisted exception truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="proof_pack_decision_timeline",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["PROOF_PACK_CREATED", "PROOF_PACK_TIMELINE_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="PROOF_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="Proof-pack creation and proof-pack-local decision timeline events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="rebalance_wave",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["WAVE_CREATED", "WAVE_EVENT", "WAVE_HANDOFF_READY"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="REBALANCE_WAVE_SOURCE_EVENTS_SUPPORTED",
            summary="Rebalance wave lifecycle and internal handoff events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="post_trade_outcome_review",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["OUTCOME_REVIEW_CREATED", "OUTCOME_REVIEW_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="OUTCOME_REVIEW_SOURCE_EVENTS_SUPPORTED",
            summary="Post-trade outcome-review creation and review events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="report_lifecycle",
            source_system="lotus-report",
            owner="lotus-report",
            support_status="SUPPORTED",
            event_types=[
                "REPORT_JOB_CREATED",
                "REPORT_SNAPSHOT_CAPTURED",
                "REPORT_RENDERED",
                "REPORT_ARCHIVED",
            ],
            route="/reports/jobs/{job_id}/portfolio-memory-events",
            reason_code="REPORT_SOURCE_EVENTS_SUPPORTED",
            summary="Report lifecycle, snapshot, render, and archive lineage are source-owned by report.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="ai_workflow_pack",
            source_system="lotus-ai",
            owner="lotus-ai",
            support_status="SUPPORTED",
            event_types=[
                "AI_WORKFLOW_PACK_RUN",
                "AI_WORKFLOW_PACK_REVIEW",
                "AI_WORKFLOW_PACK_LINEAGE",
            ],
            route="/platform/workflow-packs/source-events",
            reason_code="AI_WORKFLOW_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="AI workflow-pack run, review, and lineage posture are source-owned by AI.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="generated_document_archive",
            source_system="lotus-archive",
            owner="lotus-archive",
            support_status="SUPPORTED",
            event_types=[
                "GENERATED_DOCUMENT_ARCHIVED",
                "GENERATED_DOCUMENT_SUPERSEDED",
                "GENERATED_DOCUMENT_CORRECTED",
                "CLIENT_DELIVERY_REISSUED",
            ],
            route="/documents/{document_id}/source-events",
            reason_code="GENERATED_DOCUMENT_SOURCE_EVENTS_SUPPORTED",
            summary="Generated-document archive and client-delivery lineage are source-owned by archive.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="external_oms_execution",
            source_system="future-oms-owner",
            owner="future execution or OMS owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route=None,
            reason_code="OMS_SOURCE_EVENTS_NOT_SUPPORTED",
            summary=(
                "No external OMS execution, fill, or acknowledgement events are projected until a "
                "governed OMS owner publishes a no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="pm_scoring",
            source_system="lotus-manage",
            owner="lotus-manage PM operating quality product",
            support_status="SEPARATE_PRODUCT_NO_EVENT_FAMILY",
            event_types=[],
            route="/api/v1/rebalance/pm-operating-quality/score-runs",
            reason_code="PM_QUALITY_SCORE_RUN_SUPPORTED_SEPARATELY",
            summary=(
                "Persisted PM operating quality score runs are supported as a separate explicit "
                "Manage product with bank-supplied policy and source-backed evidence; portfolio "
                "memory projects no PM-scoring events until a separate event family is governed."
            ),
        ),
    ]


def _mandate_events(
    *,
    portfolio_id: str,
    mandate_repository: DpmMandateRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    twin = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    events: list[DpmPortfolioMemoryEvent] = []
    if twin is not None:
        health_snapshot = mandate_repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
        if health_snapshot is not None:
            events.append(
                _mandate_health_event(
                    health_snapshot=health_snapshot,
                    source_lineage=twin.source_lineage,
                )
            )

    exceptions, _cursor = mandate_repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=twin.mandate_id if twin is not None else None,
        portfolio_id=portfolio_id,
        state=None,
        limit=limit,
        cursor=None,
    )
    events.extend(_mandate_exception_event(exception) for exception in exceptions)
    return events


def _mandate_health_event(
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
        supportability_state=_state(health_snapshot.health_state.value),
        summary=(
            f"Mandate health snapshot {health_snapshot.health_snapshot_id} calculated as "
            f"{health_snapshot.health_state.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[_from_source_product_lineage(ref) for ref in source_lineage],
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


def _mandate_exception_event(
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
        supportability_state=_monitoring_exception_state(exception),
        summary=(
            f"Mandate monitoring exception {exception.exception_id} is {exception.state} "
            f"for {exception.dimension.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[_from_source_product_lineage(ref) for ref in exception.source_lineage],
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


def _proof_pack_events(proof_pack: DpmPreTradeProofPack) -> list[DpmPortfolioMemoryEvent]:
    refs = _proof_pack_source_refs(proof_pack)
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:proof_pack:{proof_pack.proof_pack_id}:created",
            event_type="PROOF_PACK_CREATED",
            event_time=proof_pack.created_at.isoformat(),
            actor=proof_pack.created_by,
            source_system="lotus-manage",
            source_type="DPM_PRE_TRADE_PROOF_PACK",
            source_id=proof_pack.proof_pack_id,
            status=proof_pack.status,
            supportability_state=_state(proof_pack.status),
            summary=f"Proof pack {proof_pack.proof_pack_id} created from {proof_pack.source_type}.",
            reason_codes=proof_pack.supportability.reason_codes,
            source_refs=refs,
            artifact_refs=_proof_pack_artifact_refs(proof_pack),
            content_hash=proof_pack.content_hash,
            metadata={
                "mandate_id": proof_pack.mandate_id,
                "rebalance_run_id": proof_pack.rebalance_run_id,
                "alternative_set_id": proof_pack.alternative_set_id,
                "selected_alternative_id": proof_pack.selected_alternative_id,
                "as_of_date": proof_pack.as_of_date,
            },
        )
    ]
    for timeline_event in proof_pack.decision_timeline.events:
        events.append(
            DpmPortfolioMemoryEvent(
                event_id=(
                    f"memory:proof_pack:{proof_pack.proof_pack_id}:"
                    f"timeline:{timeline_event.event_id}"
                ),
                event_type="PROOF_PACK_TIMELINE_EVENT",
                event_time=timeline_event.event_time,
                actor=timeline_event.actor,
                source_system=timeline_event.source_system,
                source_type=timeline_event.event_type,
                source_id=timeline_event.event_id,
                status=timeline_event.status,
                supportability_state=_state(timeline_event.status),
                summary=f"Proof-pack timeline event {timeline_event.event_type}.",
                reason_codes=timeline_event.reason_codes,
                source_refs=refs,
                artifact_refs=[
                    _from_proof_pack_evidence_ref(ref) for ref in timeline_event.artifact_refs
                ],
                content_hash=proof_pack.content_hash,
                metadata={"proof_pack_id": proof_pack.proof_pack_id},
            )
        )
    return events


def _wave_events(*, wave: DpmRebalanceWave, portfolio_id: str) -> list[DpmPortfolioMemoryEvent]:
    matching_items = [item for item in wave.items if item.portfolio_id == portfolio_id]
    item_ids = {item.wave_item_id for item in matching_items}
    refs = _wave_source_refs(wave=wave, items=matching_items)
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:wave:{wave.wave_id}:created",
            event_type="WAVE_CREATED",
            event_time=wave.created_at.isoformat(),
            actor=wave.created_by,
            source_system="lotus-manage",
            source_type="DPM_REBALANCE_WAVE",
            source_id=wave.wave_id,
            status=wave.state,
            supportability_state=_state(wave.state),
            summary=f"Rebalance wave {wave.wave_id} created for trigger {wave.trigger.trigger_type}.",
            reason_codes=sorted(
                {reason for item in matching_items for reason in item.reason_codes}
            ),
            source_refs=refs,
            content_hash=None,
            metadata={
                "trigger_type": wave.trigger.trigger_type,
                "trigger_id": wave.trigger.trigger_id,
                "as_of_date": wave.as_of_date,
                "matching_item_count": len(matching_items),
            },
        )
    ]
    events.extend(_wave_state_events(wave=wave, refs=refs))
    for handoff in wave.handoff_refs:
        if item_ids and not item_ids.intersection(handoff.item_ids):
            continue
        events.append(_handoff_event(wave=wave, handoff=handoff, refs=refs))
    return events


def _wave_state_events(
    *,
    wave: DpmRebalanceWave,
    refs: list[DpmPortfolioMemorySourceRef],
) -> list[DpmPortfolioMemoryEvent]:
    return [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:wave:{wave.wave_id}:event:{event.event_id}",
            event_type="WAVE_EVENT",
            event_time=event.created_at.isoformat(),
            actor=event.actor_id,
            source_system="lotus-manage",
            source_type=event.event_type,
            source_id=event.event_id,
            status=event.to_state,
            supportability_state=_state(event.to_state),
            summary=f"Wave event {event.event_type} moved wave to {event.to_state}.",
            reason_codes=[event.reason_code],
            source_refs=refs,
            content_hash=None,
            metadata=_wave_event_metadata(event),
        )
        for event in wave.events
    ]


def _handoff_event(
    *,
    wave: DpmRebalanceWave,
    handoff: DpmWaveHandoffRef,
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:wave:{wave.wave_id}:handoff:{handoff.handoff_ref_id}",
        event_type="WAVE_HANDOFF_READY",
        event_time=handoff.created_at.isoformat(),
        actor=handoff.actor_id,
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id=handoff.handoff_ref_id,
        status=wave.state,
        supportability_state=_state(wave.state),
        summary="Internal operations handoff evidence recorded without external execution claim.",
        reason_codes=[handoff.reason_code],
        source_refs=refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
                source_id=handoff.handoff_ref_id,
                content_hash=handoff.content_hash,
            )
        ],
        content_hash=handoff.content_hash,
        metadata={
            "wave_id": wave.wave_id,
            "item_count": len(handoff.item_ids),
            "external_execution_claimed": handoff.external_execution_claimed,
        },
    )


def _outcome_review_events(
    *,
    review: DpmPostTradeOutcomeReview,
    persisted_events: list[DpmOutcomeEvent],
) -> list[DpmPortfolioMemoryEvent]:
    events_by_id = {event.event_id: event for event in [*review.events, *persisted_events]}
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:outcome:{review.outcome_review_id}:created",
            event_type="OUTCOME_REVIEW_CREATED",
            event_time=review.created_at.isoformat(),
            actor=review.created_by,
            source_system="lotus-manage",
            source_type="DPM_POST_TRADE_OUTCOME_REVIEW",
            source_id=review.outcome_review_id,
            status=review.state,
            supportability_state=_state(review.state),
            summary=f"Outcome review {review.outcome_review_id} created with {review.overall_outcome}.",
            reason_codes=review.supportability.reason_codes,
            source_refs=[_from_outcome_source_ref(ref) for ref in review.source_lineage],
            content_hash=review.content_hash,
            metadata={
                "proof_pack_id": review.proof_pack_id,
                "wave_id": review.wave_id,
                "wave_item_id": review.wave_item_id,
                "operations_handoff_ref_id": review.operations_handoff_ref_id,
            },
        )
    ]
    for event in events_by_id.values():
        events.append(
            DpmPortfolioMemoryEvent(
                event_id=f"memory:outcome:{review.outcome_review_id}:event:{event.event_id}",
                event_type="OUTCOME_REVIEW_EVENT",
                event_time=event.event_time,
                actor=event.actor,
                source_system="lotus-manage",
                source_type=event.event_type,
                source_id=event.event_id,
                status=event.state,
                supportability_state=_state(event.state),
                summary=f"Outcome-review event {event.event_type}.",
                reason_codes=event.reason_codes,
                source_refs=[_from_outcome_source_ref(ref) for ref in event.source_refs],
                content_hash=review.content_hash,
                metadata={"outcome_review_id": review.outcome_review_id},
            )
        )
    return events


def _waves_for_portfolio(
    *,
    portfolio_id: str,
    wave_repository: DpmWaveRepository,
    limit: int,
) -> list[DpmRebalanceWave]:
    waves = wave_repository.list_waves(limit=limit)
    return [wave for wave in waves if any(item.portfolio_id == portfolio_id for item in wave.items)]


def _dedupe_and_sort(
    events: Iterable[DpmPortfolioMemoryEvent],
) -> list[DpmPortfolioMemoryEvent]:
    unique = {event.event_id: event for event in events}
    return sorted(
        unique.values(), key=lambda event: (event.event_time, event.event_id), reverse=True
    )


def _memory_state(
    events: list[DpmPortfolioMemoryEvent],
) -> PortfolioMemorySupportabilityState:
    if not events:
        return "EMPTY"
    states = {event.supportability_state for event in events}
    for state in ("BLOCKED", "DEGRADED", "PENDING_REVIEW"):
        if state in states:
            return state
    return "READY"


def _state(source_state: str | None) -> PortfolioMemorySupportabilityState:
    normalized = (source_state or "").upper()
    if "BLOCK" in normalized or normalized in {"FAILED", "REJECTED", "CANCELLED"}:
        return "BLOCKED"
    if "DEGRADED" in normalized or "BREACHED" in normalized or "PARTIAL" in normalized:
        return "DEGRADED"
    if "REVIEW" in normalized or normalized in {"CREATED", "DRAFT", "PREVIEWED", "CANDIDATE"}:
        return "PENDING_REVIEW"
    return "READY"


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _proof_pack_source_refs(proof_pack: DpmPreTradeProofPack) -> list[DpmPortfolioMemorySourceRef]:
    refs: dict[tuple[str, str, str], DpmPortfolioMemorySourceRef] = {}
    for section in proof_pack.sections:
        for ref in section.source_refs:
            memory_ref = _from_proof_pack_source_ref(ref)
            refs[(memory_ref.source_system, memory_ref.source_type, memory_ref.source_id)] = (
                memory_ref
            )
    return sorted(
        refs.values(), key=lambda ref: (ref.source_system, ref.source_type, ref.source_id)
    )


def _proof_pack_artifact_refs(
    proof_pack: DpmPreTradeProofPack,
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [
        ref
        for ref in [
            proof_pack.markdown_summary_ref,
            proof_pack.report_input_ref,
            proof_pack.ai_evidence_ref,
        ]
        if ref is not None
    ]
    return [_from_proof_pack_evidence_ref(ref) for ref in refs]


def _wave_source_refs(
    *,
    wave: DpmRebalanceWave,
    items: list[DpmRebalanceWaveItem],
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [_from_wave_source_ref(ref) for ref in wave.trigger.source_refs]
    for item in items:
        refs.extend(_from_wave_source_ref(ref) for ref in item.source_refs)
    return sorted(refs, key=lambda ref: (ref.source_system, ref.source_type, ref.source_id))


def _from_proof_pack_source_ref(ref: DpmProofPackSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def _from_proof_pack_evidence_ref(ref: DpmProofPackEvidenceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.ref_type,
        source_id=ref.ref_id,
        content_hash=ref.content_hash,
    )


def _from_wave_source_ref(ref: DpmWaveSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def _from_outcome_source_ref(ref: DpmOutcomeSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        content_hash=ref.content_hash,
    )


def _from_source_product_lineage(ref: DpmSourceProductLineage) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.product_name,
        source_id=ref.source_record_id or ref.product_name,
        source_version=ref.product_version,
        supportability_state=ref.data_quality_status,
    )


def _monitoring_exception_state(
    exception: DpmMonitoringException,
) -> PortfolioMemorySupportabilityState:
    if exception.state == "RESOLVED":
        return "READY"
    if exception.severity.value == "CRITICAL":
        return "BLOCKED"
    if exception.severity.value == "WARNING":
        return "DEGRADED"
    return "PENDING_REVIEW"


def _wave_event_metadata(event: DpmRebalanceWaveEvent) -> dict[str, object]:
    metadata = dict(event.metadata)
    metadata["from_state"] = event.from_state
    metadata["to_state"] = event.to_state
    metadata["correlation_id"] = event.correlation_id
    return metadata
