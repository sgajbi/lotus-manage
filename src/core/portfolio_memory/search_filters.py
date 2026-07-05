"""Search and facet helpers for portfolio memory."""

from collections.abc import Iterable

from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.event_projection import (
    event_source_systems as projected_event_source_systems,
    event_source_types as projected_event_source_types,
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
    source_system: str | None,
    source_type: str | None,
) -> bool:
    return (
        _event_type_matches(event=event, event_type=event_type)
        and _event_source_system_matches(event=event, source_system=source_system)
        and _event_source_type_matches(event=event, source_type=source_type)
    )


def _event_type_matches(*, event: DpmPortfolioMemoryEvent, event_type: str | None) -> bool:
    return event_type is None or event.event_type == event_type


def _event_source_system_matches(
    *, event: DpmPortfolioMemoryEvent, source_system: str | None
) -> bool:
    return source_system is None or source_system in event_source_systems(event)


def _event_source_type_matches(*, event: DpmPortfolioMemoryEvent, source_type: str | None) -> bool:
    return source_type is None or source_type in event_source_types(event)


def event_source_systems(event: DpmPortfolioMemoryEvent) -> set[str]:
    return projected_event_source_systems(event)


def event_source_types(event: DpmPortfolioMemoryEvent) -> set[str]:
    return projected_event_source_types(event)


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
