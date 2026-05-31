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


def build_search_row(
    *,
    memory: DpmPortfolioMemory,
    filters: PortfolioMemorySearchFilters,
    explicit_candidate_ids: set[str],
) -> SearchRow | None:
    if memory.event_count == 0:
        if (
            filters.supportability_state != "EMPTY"
            or memory.portfolio_id not in explicit_candidate_ids
        ):
            return None
    if filters.event_type is not None and filters.event_type not in memory.event_type_counts:
        return None
    if (
        filters.supportability_state is not None
        and memory.supportability_state != filters.supportability_state
    ):
        return None
    if filters.source_system is not None and filters.source_system not in memory.source_systems:
        return None

    matching_events = [
        event
        for event in memory.events
        if event_matches_search_filters(
            event=event,
            event_type=filters.event_type,
            supportability_state=filters.supportability_state,
            source_system=filters.source_system,
            source_type=filters.source_type,
        )
    ]
    if (
        (
            filters.event_type is not None
            or filters.source_system is not None
            or filters.source_type is not None
            or filters.supportability_state is not None
        )
        and filters.supportability_state != "EMPTY"
        and not matching_events
    ):
        return None

    latest_event = memory.events[0] if memory.events else None
    latest_matching_event = matching_events[0] if matching_events else None
    return (
        DpmPortfolioMemorySearchItem(
            portfolio_id=memory.portfolio_id,
            event_count=memory.event_count,
            supportability_state=memory.supportability_state,
            event_type_counts=memory.event_type_counts,
            source_systems=memory.source_systems,
            reason_codes=memory.reason_codes,
            latest_event_time=latest_event.event_time if latest_event else None,
            latest_event_type=latest_event.event_type if latest_event else None,
            matching_event_count=len(matching_events),
            latest_matching_event_time=(
                latest_matching_event.event_time if latest_matching_event else None
            ),
            latest_matching_event_type=(
                latest_matching_event.event_type if latest_matching_event else None
            ),
            latest_matching_event_id=(
                latest_matching_event.event_id if latest_matching_event else None
            ),
            latest_matching_event_identity=(
                latest_matching_event.event_identity if latest_matching_event else None
            ),
            latest_matching_event_source_system=(
                latest_matching_event.source_system if latest_matching_event else None
            ),
            latest_matching_event_source_type=(
                latest_matching_event.source_type if latest_matching_event else None
            ),
            latest_matching_event_source_id=(
                latest_matching_event.source_id if latest_matching_event else None
            ),
            latest_matching_event_content_hash=(
                latest_matching_event.content_hash if latest_matching_event else None
            ),
            content_hash=memory.content_hash,
        ),
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
    sorted_rows = sorted(
        search_rows,
        key=lambda row: (row[0].latest_event_time or "", row[0].portfolio_id),
        reverse=True,
    )
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
