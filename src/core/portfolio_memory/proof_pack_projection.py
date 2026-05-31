"""Proof-pack source-event projection helpers for portfolio memory."""

from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.source_refs import (
    from_proof_pack_evidence_ref,
    proof_pack_artifact_refs,
    proof_pack_source_refs,
)
from src.core.portfolio_memory.supportability import source_supportability_state
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackDecisionTimelineEvent,
)


def proof_pack_events(proof_pack: DpmPreTradeProofPack) -> list[DpmPortfolioMemoryEvent]:
    refs = proof_pack_source_refs(proof_pack)
    events = [_proof_pack_created_event(proof_pack=proof_pack, refs=refs)]
    events.extend(
        _proof_pack_timeline_event(
            proof_pack=proof_pack,
            timeline_event=timeline_event,
            refs=refs,
        )
        for timeline_event in proof_pack.decision_timeline.events
    )
    return events


def _proof_pack_created_event(
    *,
    proof_pack: DpmPreTradeProofPack,
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:proof_pack:{proof_pack.proof_pack_id}:created",
        event_type="PROOF_PACK_CREATED",
        event_time=proof_pack.created_at.isoformat(),
        actor=proof_pack.created_by,
        source_system="lotus-manage",
        source_type="DPM_PRE_TRADE_PROOF_PACK",
        source_id=proof_pack.proof_pack_id,
        status=proof_pack.status,
        supportability_state=source_supportability_state(proof_pack.status),
        summary=f"Proof pack {proof_pack.proof_pack_id} created from {proof_pack.source_type}.",
        reason_codes=proof_pack.supportability.reason_codes,
        source_refs=refs,
        artifact_refs=proof_pack_artifact_refs(proof_pack),
        content_hash=proof_pack.content_hash,
        metadata={
            "mandate_id": proof_pack.mandate_id,
            "rebalance_run_id": proof_pack.rebalance_run_id,
            "alternative_set_id": proof_pack.alternative_set_id,
            "selected_alternative_id": proof_pack.selected_alternative_id,
            "as_of_date": proof_pack.as_of_date,
        },
    )


def _proof_pack_timeline_event(
    *,
    proof_pack: DpmPreTradeProofPack,
    timeline_event: DpmProofPackDecisionTimelineEvent,
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            f"memory:proof_pack:{proof_pack.proof_pack_id}:timeline:{timeline_event.event_id}"
        ),
        event_type="PROOF_PACK_TIMELINE_EVENT",
        event_time=timeline_event.event_time,
        actor=timeline_event.actor,
        source_system=timeline_event.source_system,
        source_type=timeline_event.event_type,
        source_id=timeline_event.event_id,
        status=timeline_event.status,
        supportability_state=source_supportability_state(timeline_event.status),
        summary=f"Proof-pack timeline event {timeline_event.event_type}.",
        reason_codes=timeline_event.reason_codes,
        source_refs=refs,
        artifact_refs=[from_proof_pack_evidence_ref(ref) for ref in timeline_event.artifact_refs],
        content_hash=proof_pack.content_hash,
        metadata={"proof_pack_id": proof_pack.proof_pack_id},
    )
