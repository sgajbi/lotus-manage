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


@dataclass(frozen=True)
class _MatchingEventFacetCounts:
    event_type_counts: dict[str, int] = field(default_factory=dict)
    supportability_state_counts: dict[str, int] = field(default_factory=dict)
    source_system_counts: dict[str, int] = field(default_factory=dict)
    source_type_counts: dict[str, int] = field(default_factory=dict)


def build_search_facet_counts(
    search_rows: Iterable[SearchFacetRow],
) -> PortfolioMemorySearchFacetCounts:
    rows = list(search_rows)
    matching_event_counts = _count_matching_event_facets(
        event for _item, matching_events in rows for event in matching_events
    )

    return PortfolioMemorySearchFacetCounts(
        supportability_state_counts=_sorted_counts(
            count_values(item.supportability_state for item, _events in rows)
        ),
        event_type_counts=_sorted_counts(matching_event_counts.event_type_counts),
        matching_event_supportability_state_counts=_sorted_counts(
            matching_event_counts.supportability_state_counts
        ),
        matching_event_source_system_counts=_sorted_counts(
            matching_event_counts.source_system_counts
        ),
        matching_event_source_type_counts=_sorted_counts(matching_event_counts.source_type_counts),
        source_system_counts=_sorted_counts(_count_represented_source_systems(rows)),
    )


def _count_matching_event_facets(
    matching_events: Iterable[DpmPortfolioMemoryEvent],
) -> _MatchingEventFacetCounts:
    counts = _MatchingEventFacetCounts()
    for event in matching_events:
        _increment_count(counts.event_type_counts, event.event_type)
        _increment_count(counts.supportability_state_counts, event.supportability_state)
        for source_system in event_source_systems(event):
            _increment_count(counts.source_system_counts, source_system)
        for source_type in event_source_types(event):
            _increment_count(counts.source_type_counts, source_type)
    return counts


def _count_represented_source_systems(rows: Iterable[SearchFacetRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item, _matching_events in rows:
        for represented_source_system in item.source_systems:
            _increment_count(counts, represented_source_system)
    return counts


def _increment_count(counts: dict[str, int], value: str) -> None:
    counts[value] = counts.get(value, 0) + 1


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items()))
