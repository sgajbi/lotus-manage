"""Search-page assembly for portfolio-memory summaries."""

from dataclasses import dataclass

from src.core.portfolio_memory.envelopes import finalize_search_page_payload
from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence,
    external_execution_boundary_evidence,
    source_event_family_posture,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySearchAppliedFilters,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySearchPage,
    PortfolioMemoryEventType,
    PortfolioMemorySupportabilityState,
)
from src.core.portfolio_memory.search_facets import build_search_facet_counts
from src.core.portfolio_memory.search_filters import (
    event_matches_search_filters,
)

PORTFOLIO_MEMORY_SEARCH_SUPPORT_BOUNDARY = (
    "Manage-local memory search indexes persisted Manage evidence and explicit "
    "caller-supplied portfolio identifiers only. It exposes supported and deferred "
    "source-event family posture for Manage/report/AI/archive/PM-quality lineage, but "
    "does not discover the global portfolio universe, query external source-owner "
    "event stores, project OMS acknowledgement/fill/settlement events, project "
    "client-communication events, or recalculate source truth."
)


@dataclass(frozen=True)
class PortfolioMemorySearchFilters:
    event_type: str | None
    supportability_state: PortfolioMemorySupportabilityState | None
    source_system: str | None
    source_type: str | None


SearchRow = tuple[DpmPortfolioMemorySearchItem, list[DpmPortfolioMemoryEvent]]


@dataclass(frozen=True)
class _LatestEventMetadata:
    latest_event_time: str | None
    latest_event_type: PortfolioMemoryEventType | None


@dataclass(frozen=True)
class _LatestMatchingEventMetadata:
    latest_matching_event_time: str | None
    latest_matching_event_type: PortfolioMemoryEventType | None
    latest_matching_event_id: str | None
    latest_matching_event_identity: str | None
    latest_matching_event_source_system: str | None
    latest_matching_event_source_type: str | None
    latest_matching_event_source_id: str | None
    latest_matching_event_content_hash: str | None


def _memory_passes_search_summary_filters(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
    explicit_candidate_ids: set[str],
) -> bool:
    if memory.event_count == 0 and not _empty_memory_matches_search_summary_filters(
        memory=memory,
        filters=filters,
        explicit_candidate_ids=explicit_candidate_ids,
    ):
        return False
    return all(
        (
            _event_type_matches_search_summary(memory=memory, filters=filters),
            _supportability_matches_search_summary(memory=memory, filters=filters),
            _source_system_matches_search_summary(memory=memory, filters=filters),
        )
    )


def _empty_memory_matches_search_summary_filters(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
    explicit_candidate_ids: set[str],
) -> bool:
    return filters.supportability_state == "EMPTY" and memory.portfolio_id in explicit_candidate_ids


def _event_type_matches_search_summary(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
) -> bool:
    return filters.event_type is None or filters.event_type in memory.event_type_counts


def _supportability_matches_search_summary(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
) -> bool:
    return (
        filters.supportability_state is None
        or memory.supportability_state == filters.supportability_state
    )


def _source_system_matches_search_summary(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
) -> bool:
    return filters.source_system is None or filters.source_system in memory.source_systems


def _filters_require_matching_events(filters: PortfolioMemorySearchFilters) -> bool:
    return (
        filters.event_type is not None
        or filters.source_system is not None
        or filters.source_type is not None
    )


def _latest_event_metadata(memory: DpmPortfolioMemory) -> _LatestEventMetadata:
    latest_event = memory.events[0] if memory.events else None
    return _LatestEventMetadata(
        latest_event_time=latest_event.event_time if latest_event else None,
        latest_event_type=latest_event.event_type if latest_event else None,
    )


def _latest_matching_event_metadata(
    matching_events: list[DpmPortfolioMemoryEvent],
) -> _LatestMatchingEventMetadata:
    latest_matching_event = matching_events[0] if matching_events else None
    if latest_matching_event is None:
        return _empty_latest_matching_event_metadata()
    return _latest_matching_event_metadata_from_event(latest_matching_event)


def _empty_latest_matching_event_metadata() -> _LatestMatchingEventMetadata:
    return _LatestMatchingEventMetadata(
        latest_matching_event_time=None,
        latest_matching_event_type=None,
        latest_matching_event_id=None,
        latest_matching_event_identity=None,
        latest_matching_event_source_system=None,
        latest_matching_event_source_type=None,
        latest_matching_event_source_id=None,
        latest_matching_event_content_hash=None,
    )


def _latest_matching_event_metadata_from_event(
    event: DpmPortfolioMemoryEvent,
) -> _LatestMatchingEventMetadata:
    return _LatestMatchingEventMetadata(
        latest_matching_event_time=event.event_time,
        latest_matching_event_type=event.event_type,
        latest_matching_event_id=event.event_id,
        latest_matching_event_identity=event.event_identity,
        latest_matching_event_source_system=event.source_system,
        latest_matching_event_source_type=event.source_type,
        latest_matching_event_source_id=event.source_id,
        latest_matching_event_content_hash=event.content_hash,
    )


def _portfolio_memory_search_item(
    *,
    memory: DpmPortfolioMemory,
    matching_events: list[DpmPortfolioMemoryEvent],
) -> DpmPortfolioMemorySearchItem:
    latest_event_metadata = _latest_event_metadata(memory)
    latest_matching_metadata = _latest_matching_event_metadata(matching_events)
    return DpmPortfolioMemorySearchItem(
        portfolio_id=memory.portfolio_id,
        event_count=memory.event_count,
        supportability_state=memory.supportability_state,
        event_type_counts=memory.event_type_counts,
        source_systems=memory.source_systems,
        reason_codes=memory.reason_codes,
        latest_event_time=latest_event_metadata.latest_event_time,
        latest_event_type=latest_event_metadata.latest_event_type,
        matching_event_count=len(matching_events),
        latest_matching_event_time=latest_matching_metadata.latest_matching_event_time,
        latest_matching_event_type=latest_matching_metadata.latest_matching_event_type,
        latest_matching_event_id=latest_matching_metadata.latest_matching_event_id,
        latest_matching_event_identity=latest_matching_metadata.latest_matching_event_identity,
        latest_matching_event_source_system=(
            latest_matching_metadata.latest_matching_event_source_system
        ),
        latest_matching_event_source_type=latest_matching_metadata.latest_matching_event_source_type,
        latest_matching_event_source_id=latest_matching_metadata.latest_matching_event_source_id,
        latest_matching_event_content_hash=(
            latest_matching_metadata.latest_matching_event_content_hash
        ),
        content_hash=memory.content_hash,
    )


def build_search_row(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
    explicit_candidate_ids: set[str],
) -> SearchRow | None:
    if not _memory_passes_search_summary_filters(
        memory=memory,
        filters=filters,
        explicit_candidate_ids=explicit_candidate_ids,
    ):
        return None

    matching_events = [
        event
        for event in memory.events
        if event_matches_search_filters(
            event=event,
            event_type=filters.event_type,
            source_system=filters.source_system,
            source_type=filters.source_type,
        )
    ]
    if (
        _filters_require_matching_events(filters)
        and filters.supportability_state != "EMPTY"
        and not matching_events
    ):
        return None

    return (
        _portfolio_memory_search_item(memory=memory, matching_events=matching_events),
        matching_events,
    )


def build_search_page(
    *,
    search_rows: list[SearchRow],
    filters: PortfolioMemorySearchFilters,
    explicit_candidate_ids: set[str],
    scanned_portfolio_count: int,
    source_scan_limit: int,
    limit: int,
    offset: int,
    generated_at: str,
) -> DpmPortfolioMemorySearchPage:
    sorted_rows = sorted(search_rows, key=lambda row: row[0].portfolio_id)
    sorted_rows.sort(key=lambda row: row[0].latest_event_time or "", reverse=True)
    total_count = len(sorted_rows)
    facet_counts = build_search_facet_counts(sorted_rows)

    page_rows = sorted_rows[offset : offset + limit]
    page = [item for item, _events in page_rows]
    next_offset = offset + len(page)
    has_more = next_offset < total_count
    return finalize_search_page_payload(
        {
            "items": page,
            "limit": limit,
            "offset": offset,
            "returned_count": len(page),
            "total_count": total_count,
            "has_more": has_more,
            "next_offset": next_offset if has_more else None,
            "scanned_portfolio_count": scanned_portfolio_count,
            "source_scan_limit": source_scan_limit,
            "applied_filters": DpmPortfolioMemorySearchAppliedFilters(
                portfolio_ids=sorted(explicit_candidate_ids),
                event_type=filters.event_type,
                supportability_state=filters.supportability_state,
                source_system=filters.source_system,
                source_type=filters.source_type,
            ),
            "supportability_state_counts": facet_counts.supportability_state_counts,
            "event_type_counts": facet_counts.event_type_counts,
            "matching_event_supportability_state_counts": (
                facet_counts.matching_event_supportability_state_counts
            ),
            "matching_event_source_system_counts": (
                facet_counts.matching_event_source_system_counts
            ),
            "matching_event_source_type_counts": facet_counts.matching_event_source_type_counts,
            "source_system_counts": facet_counts.source_system_counts,
            "source_event_family_posture": source_event_family_posture(),
            "external_execution_boundary": external_execution_boundary_evidence(),
            "client_communication_boundary": client_communication_boundary_evidence(),
            "generated_at": generated_at,
            "support_boundary": PORTFOLIO_MEMORY_SEARCH_SUPPORT_BOUNDARY,
        }
    )
