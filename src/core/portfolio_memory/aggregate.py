"""Aggregate assembly for source-backed portfolio memory."""

from datetime import datetime

from src.core.portfolio_memory.envelopes import finalize_portfolio_memory
from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence,
    external_execution_boundary_evidence,
    portfolio_memory_governance_policy,
    source_event_family_posture,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
)
from src.core.portfolio_memory.search_filters import (
    count_values,
    dedupe_and_sort_events,
    event_source_systems,
)
from src.core.portfolio_memory.supportability import portfolio_memory_state


def build_portfolio_memory_aggregate(
    *,
    portfolio_id: str,
    events: list[DpmPortfolioMemoryEvent],
    limit: int,
    generated_at: datetime,
) -> DpmPortfolioMemory:
    """Build the replay-stable memory aggregate from projected source events."""

    bounded_events = dedupe_and_sort_events(events)[:limit]
    memory = DpmPortfolioMemory(
        portfolio_id=portfolio_id,
        event_count=len(bounded_events),
        supportability_state=portfolio_memory_state(bounded_events),
        event_type_counts=count_values(event.event_type for event in bounded_events),
        source_systems=sorted(
            {
                source_system
                for event in bounded_events
                for source_system in event_source_systems(event)
            }
        ),
        reason_codes=sorted({reason for event in bounded_events for reason in event.reason_codes}),
        governance_policy=portfolio_memory_governance_policy(),
        source_event_family_posture=source_event_family_posture(),
        external_execution_boundary=external_execution_boundary_evidence(),
        client_communication_boundary=client_communication_boundary_evidence(),
        events=bounded_events,
        content_hash="",
        generated_at=generated_at.isoformat(),
    )
    return finalize_portfolio_memory(memory)
