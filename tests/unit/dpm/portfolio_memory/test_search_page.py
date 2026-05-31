from src.core.portfolio_memory.envelopes import finalize_portfolio_memory
from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence,
    external_execution_boundary_evidence,
    portfolio_memory_governance_policy,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.search_page import (
    PortfolioMemorySearchFilters,
    build_search_page,
    build_search_row,
)


def test_build_search_row_projects_latest_matching_event_metadata() -> None:
    memory = _memory(
        portfolio_id="PB_SEARCH_001",
        events=[
            _event(
                event_id="memory:search:handoff",
                event_type="WAVE_HANDOFF_READY",
                event_time="2026-05-31T10:00:00+00:00",
                source_id="handoff-001",
                content_hash="sha256:handoff",
            )
        ],
    )

    row = build_search_row(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type="WAVE_HANDOFF_READY",
            supportability_state=None,
            source_system="lotus-core",
            source_type="PortfolioManagerBookMembership",
        ),
        explicit_candidate_ids=set(),
    )

    assert row is not None
    item, matching_events = row
    assert item.matching_event_count == 1
    assert item.latest_matching_event_id == "memory:search:handoff"
    assert item.latest_matching_event_source_type == "DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF"
    assert item.latest_matching_event_content_hash == "sha256:handoff"
    assert matching_events[0].source_refs[0].source_system == "lotus-core"


def test_build_search_row_keeps_only_explicit_empty_portfolios() -> None:
    memory = _memory(portfolio_id="PB_EMPTY_001", events=[])
    filters = PortfolioMemorySearchFilters(
        event_type=None,
        supportability_state="EMPTY",
        source_system=None,
        source_type=None,
    )

    assert (
        build_search_row(
            memory=memory,
            filters=filters,
            explicit_candidate_ids={"PB_EMPTY_001"},
        )
        is not None
    )
    assert (
        build_search_row(
            memory=memory,
            filters=filters,
            explicit_candidate_ids=set(),
        )
        is None
    )


def test_build_search_page_counts_matching_event_facets_and_paginates() -> None:
    first_memory = _memory(
        portfolio_id="PB_SEARCH_001",
        events=[
            _event(
                event_id="memory:search:handoff:1",
                event_type="WAVE_HANDOFF_READY",
                event_time="2026-05-31T10:00:00+00:00",
                source_id="handoff-001",
                content_hash="sha256:handoff-1",
            )
        ],
    )
    second_memory = _memory(
        portfolio_id="PB_SEARCH_002",
        events=[
            _event(
                event_id="memory:search:handoff:2",
                event_type="WAVE_HANDOFF_READY",
                event_time="2026-05-31T11:00:00+00:00",
                source_id="handoff-002",
                content_hash="sha256:handoff-2",
            )
        ],
    )
    filters = PortfolioMemorySearchFilters(
        event_type="WAVE_HANDOFF_READY",
        supportability_state=None,
        source_system="lotus-core",
        source_type=None,
    )
    rows = [
        row
        for row in [
            build_search_row(
                memory=first_memory,
                filters=filters,
                explicit_candidate_ids=set(),
            ),
            build_search_row(
                memory=second_memory,
                filters=filters,
                explicit_candidate_ids=set(),
            ),
        ]
        if row is not None
    ]

    page = build_search_page(
        search_rows=rows,
        filters=filters,
        explicit_candidate_ids=set(),
        scanned_portfolio_count=2,
        source_scan_limit=100,
        limit=1,
        offset=0,
        generated_at="2026-05-31T12:00:00+00:00",
    )

    assert page.returned_count == 1
    assert page.total_count == 2
    assert page.has_more is True
    assert page.next_offset == 1
    assert page.items[0].portfolio_id == "PB_SEARCH_002"
    assert page.event_type_counts == {"WAVE_HANDOFF_READY": 2}
    assert page.matching_event_source_system_counts == {"lotus-core": 2, "lotus-manage": 2}
    assert page.matching_event_source_type_counts["DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF"] == 2
    assert page.source_system_counts == {"lotus-core": 2, "lotus-manage": 2}


def test_build_search_page_orders_timestamp_ties_by_portfolio_id() -> None:
    filters = PortfolioMemorySearchFilters(
        event_type="WAVE_HANDOFF_READY",
        supportability_state=None,
        source_system=None,
        source_type=None,
    )
    rows = [
        row
        for row in [
            build_search_row(
                memory=_memory(
                    portfolio_id="PB_SEARCH_Z",
                    events=[
                        _event(
                            event_id="memory:search:handoff:z",
                            event_type="WAVE_HANDOFF_READY",
                            event_time="2026-05-31T10:00:00+00:00",
                            source_id="handoff-z",
                            content_hash="sha256:handoff-z",
                        )
                    ],
                ),
                filters=filters,
                explicit_candidate_ids=set(),
            ),
            build_search_row(
                memory=_memory(
                    portfolio_id="PB_SEARCH_A",
                    events=[
                        _event(
                            event_id="memory:search:handoff:a",
                            event_type="WAVE_HANDOFF_READY",
                            event_time="2026-05-31T10:00:00+00:00",
                            source_id="handoff-a",
                            content_hash="sha256:handoff-a",
                        )
                    ],
                ),
                filters=filters,
                explicit_candidate_ids=set(),
            ),
        ]
        if row is not None
    ]

    page = build_search_page(
        search_rows=rows,
        filters=filters,
        explicit_candidate_ids=set(),
        scanned_portfolio_count=2,
        source_scan_limit=100,
        limit=10,
        offset=0,
        generated_at="2026-05-31T12:00:00+00:00",
    )

    assert [item.portfolio_id for item in page.items] == ["PB_SEARCH_A", "PB_SEARCH_Z"]


def _memory(
    *,
    portfolio_id: str,
    events: list[DpmPortfolioMemoryEvent],
) -> DpmPortfolioMemory:
    source_systems = sorted(
        {
            source_system
            for event in events
            for source_system in {
                event.source_system,
                *(ref.source_system for ref in event.source_refs),
                *(ref.source_system for ref in event.artifact_refs),
            }
        }
    )
    return finalize_portfolio_memory(
        DpmPortfolioMemory(
            portfolio_id=portfolio_id,
            event_count=len(events),
            supportability_state="READY" if events else "EMPTY",
            event_type_counts={
                event_type: sum(1 for event in events if event.event_type == event_type)
                for event_type in {event.event_type for event in events}
            },
            source_systems=source_systems,
            reason_codes=sorted({reason for event in events for reason in event.reason_codes}),
            governance_policy=portfolio_memory_governance_policy(),
            source_event_family_posture=[],
            external_execution_boundary=external_execution_boundary_evidence(),
            client_communication_boundary=client_communication_boundary_evidence(),
            events=events,
            content_hash="sha256:pending",
            generated_at="2026-05-31T12:00:00+00:00",
        )
    )


def _event(
    *,
    event_id: str,
    event_type: str,
    event_time: str,
    source_id: str,
    content_hash: str,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type=event_type,
        event_time=event_time,
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id=source_id,
        status="READY",
        supportability_state="READY",
        summary="Internal handoff recorded.",
        reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
        source_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-core",
                source_type="PortfolioManagerBookMembership",
                source_id="pm-book-001",
            )
        ],
        content_hash=content_hash,
    )
