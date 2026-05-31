"""Exact-event lookup assembly for portfolio memory."""

from src.core.portfolio_memory.envelopes import finalize_event_lookup
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEventLookup,
)


def build_portfolio_memory_event_lookup(
    *,
    memory: DpmPortfolioMemory,
    event_id: str,
    support_boundary: str,
) -> DpmPortfolioMemoryEventLookup | None:
    """Select one portfolio-memory event and return a replay-stable lookup envelope."""

    for event in memory.events:
        if event.event_id != event_id:
            continue
        lookup = DpmPortfolioMemoryEventLookup(
            portfolio_id=memory.portfolio_id,
            event_id=event_id,
            event_identity=event.event_identity,
            event=event,
            memory_content_hash=memory.content_hash,
            content_hash="sha256:pending",
            generated_at=memory.generated_at,
            support_boundary=support_boundary,
        )
        return finalize_event_lookup(lookup)
    return None
