"""Facet counting for portfolio-memory search rows."""

from dataclasses import dataclass, field
from collections.abc import Iterable

from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySearchItem,
)
from src.core.portfolio_memory.search_filters import (
    count_values,
    event_source_systems,
    event_source_types,
)

SearchFacetRow = tuple[DpmPortfolioMemorySearchItem, list[DpmPortfolioMemoryEvent]]


@dataclass(frozen=True)
class PortfolioMemorySearchFacetCounts:
    supportability_state_counts: dict[str, int]
    event_type_counts: dict[str, int] = field(default_factory=dict)
    matching_event_supportability_state_counts: dict[str, int] = field(default_factory=dict)
    matching_event_source_system_counts: dict[str, int] = field(default_factory=dict)
    matching_event_source_type_counts: dict[str, int] = field(default_factory=dict)
    source_system_counts: dict[str, int] = field(default_factory=dict)


def build_search_facet_counts(
    search_rows: Iterable[SearchFacetRow],
) -> PortfolioMemorySearchFacetCounts:
    rows = list(search_rows)
    event_type_counts: dict[str, int] = {}
    matching_event_supportability_state_counts: dict[str, int] = {}
    matching_event_source_system_counts: dict[str, int] = {}
    matching_event_source_type_counts: dict[str, int] = {}
    source_system_counts: dict[str, int] = {}

    for item, matching_events in rows:
        for event in matching_events:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
            matching_event_supportability_state_counts[event.supportability_state] = (
                matching_event_supportability_state_counts.get(event.supportability_state, 0) + 1
            )
            for source_system in event_source_systems(event):
                matching_event_source_system_counts[source_system] = (
                    matching_event_source_system_counts.get(source_system, 0) + 1
                )
            for source_type in event_source_types(event):
                matching_event_source_type_counts[source_type] = (
                    matching_event_source_type_counts.get(source_type, 0) + 1
                )
        for represented_source_system in item.source_systems:
            source_system_counts[represented_source_system] = (
                source_system_counts.get(represented_source_system, 0) + 1
            )

    return PortfolioMemorySearchFacetCounts(
        supportability_state_counts=dict(
            sorted(count_values(item.supportability_state for item, _events in rows).items())
        ),
        event_type_counts=dict(sorted(event_type_counts.items())),
        matching_event_supportability_state_counts=dict(
            sorted(matching_event_supportability_state_counts.items())
        ),
        matching_event_source_system_counts=dict(
            sorted(matching_event_source_system_counts.items())
        ),
        matching_event_source_type_counts=dict(sorted(matching_event_source_type_counts.items())),
        source_system_counts=dict(sorted(source_system_counts.items())),
    )
