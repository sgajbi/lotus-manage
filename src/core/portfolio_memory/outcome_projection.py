"""Outcome-review source-event projection helpers for portfolio memory."""

from src.core.outcomes.models import DpmOutcomeEvent, DpmPostTradeOutcomeReview
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.source_refs import from_outcome_source_ref
from src.core.portfolio_memory.supportability import source_supportability_state


def outcome_review_events(
    *,
    review: DpmPostTradeOutcomeReview,
    persisted_events: list[DpmOutcomeEvent],
) -> list[DpmPortfolioMemoryEvent]:
    events_by_id = {event.event_id: event for event in [*review.events, *persisted_events]}
    events = [_outcome_review_created_event(review)]
    events.extend(
        _outcome_review_event(review=review, event=event) for event in events_by_id.values()
    )
    return events


def _outcome_review_created_event(
    review: DpmPostTradeOutcomeReview,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:outcome:{review.outcome_review_id}:created",
        event_type="OUTCOME_REVIEW_CREATED",
        event_time=review.created_at.isoformat(),
        actor=review.created_by,
        source_system="lotus-manage",
        source_type="DPM_POST_TRADE_OUTCOME_REVIEW",
        source_id=review.outcome_review_id,
        status=review.state,
        supportability_state=source_supportability_state(review.state),
        summary=f"Outcome review {review.outcome_review_id} created with {review.overall_outcome}.",
        reason_codes=review.supportability.reason_codes,
        source_refs=[from_outcome_source_ref(ref) for ref in review.source_lineage],
        content_hash=review.content_hash,
        metadata={
            "proof_pack_id": review.proof_pack_id,
            "wave_id": review.wave_id,
            "wave_item_id": review.wave_item_id,
            "operations_handoff_ref_id": review.operations_handoff_ref_id,
        },
    )


def _outcome_review_event(
    *,
    review: DpmPostTradeOutcomeReview,
    event: DpmOutcomeEvent,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:outcome:{review.outcome_review_id}:event:{event.event_id}",
        event_type="OUTCOME_REVIEW_EVENT",
        event_time=event.event_time,
        actor=event.actor,
        source_system="lotus-manage",
        source_type=event.event_type,
        source_id=event.event_id,
        status=event.state,
        supportability_state=source_supportability_state(event.state),
        summary=f"Outcome-review event {event.event_type}.",
        reason_codes=event.reason_codes,
        source_refs=[from_outcome_source_ref(ref) for ref in event.source_refs],
        content_hash=review.content_hash,
        metadata={"outcome_review_id": review.outcome_review_id},
    )
