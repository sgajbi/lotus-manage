"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone
from typing import Iterable

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.outcomes.models import DpmOutcomeEvent, DpmOutcomeSourceRef, DpmPostTradeOutcomeReview
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
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
    limit: int = 100,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose manage-owned portfolio memory without recalculating source truth."""

    generated_at = generated_at or datetime.now(timezone.utc)
    events: list[DpmPortfolioMemoryEvent] = []
    proof_packs = proof_pack_repository.list_proof_packs(portfolio_id=portfolio_id, limit=limit)
    for proof_pack in proof_packs:
        events.extend(_proof_pack_events(proof_pack))

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
        events=events,
        content_hash="",
        generated_at=generated_at.isoformat(),
    )
    payload = memory.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmPortfolioMemory.model_validate(payload)


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


def _wave_event_metadata(event: DpmRebalanceWaveEvent) -> dict[str, object]:
    metadata = dict(event.metadata)
    metadata["from_state"] = event.from_state
    metadata["to_state"] = event.to_state
    metadata["correlation_id"] = event.correlation_id
    return metadata
