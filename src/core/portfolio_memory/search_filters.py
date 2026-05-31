"""Search and facet helpers for portfolio memory."""

from collections.abc import Iterable

from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    PortfolioMemorySupportabilityState,
)


def normalize_portfolio_memory_search_filter(value: str | None) -> str | None:
    """Normalize optional string search filters without inventing aliases."""

    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def event_matches_search_filters(
    *,
    event: DpmPortfolioMemoryEvent,
    event_type: str | None,
    supportability_state: PortfolioMemorySupportabilityState | None,
    source_system: str | None,
    source_type: str | None,
) -> bool:
    if event_type is not None and event.event_type != event_type:
        return False
    if supportability_state is not None and event.supportability_state != supportability_state:
        return False
    if source_system is not None and source_system not in event_source_systems(event):
        return False
    if source_type is not None and source_type not in event_source_types(event):
        return False
    return True


def event_source_systems(event: DpmPortfolioMemoryEvent) -> set[str]:
    return {
        source_system
        for source_system in [
            event.source_system,
            *(ref.source_system for ref in event.source_refs),
            *(ref.source_system for ref in event.artifact_refs),
        ]
        if source_system
    }


def event_source_types(event: DpmPortfolioMemoryEvent) -> set[str]:
    return {
        source_type
        for source_type in [
            event.source_type,
            *(ref.source_type for ref in event.source_refs),
            *(ref.source_type for ref in event.artifact_refs),
        ]
        if source_type
    }


def count_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def dedupe_and_sort_events(
    events: Iterable[DpmPortfolioMemoryEvent],
) -> list[DpmPortfolioMemoryEvent]:
    unique: dict[str, DpmPortfolioMemoryEvent] = {}
    for event in events:
        existing = unique.get(event.event_id)
        if existing is None or _event_dedupe_key(event) > _event_dedupe_key(existing):
            unique[event.event_id] = event
    return sorted(
        unique.values(), key=lambda event: (event.event_time, event.event_id), reverse=True
    )


def _event_dedupe_key(event: DpmPortfolioMemoryEvent) -> tuple[str, str, str, str, str]:
    return (
        event.event_time,
        event.content_hash or "",
        event.source_system,
        event.source_type,
        event.source_id,
    )
