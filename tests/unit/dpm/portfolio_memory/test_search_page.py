import pytest

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
    _expected_search_page_next_offset,
    _latest_event_metadata_is_complete,
    _latest_event_metadata_is_present,
    _next_offset_advances,
    _next_offset_matches_expected,
    _page_has_more,
    _search_page_source_system_counts,
    _search_page_is_terminal,
    _validate_empty_search_item_latest_event_metadata,
    _validate_populated_search_item_latest_event_metadata,
    _validate_search_item_counts,
    _validate_search_item_latest_event_metadata,
    _validate_search_item_latest_matching_event_metadata,
    _validate_search_item_metadata,
    _validate_search_item_sorted_aggregates,
    _validate_complete_search_page_counts,
    _validate_search_page_count_maps,
    _validate_search_page_next_offset,
    _validate_search_page_pagination,
    _validate_search_page_returned_counts_covered,
    _validate_terminal_search_page_next_offset,
)
from src.core.portfolio_memory.search_page import (
    PortfolioMemorySearchFilters,
    _LatestEventMetadata,
    _LatestMatchingEventMetadata,
    _empty_latest_matching_event_metadata,
    _empty_memory_matches_search_summary_filters,
    _event_type_matches_search_summary,
    _filters_require_matching_events,
    _latest_event_metadata,
    _latest_matching_event_metadata,
    _latest_matching_event_metadata_from_event,
    _memory_passes_search_summary_filters,
    _portfolio_memory_search_item,
    _source_system_matches_search_summary,
    _supportability_matches_search_summary,
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


def test_memory_passes_search_summary_filters_rejects_unmatched_summary_fields() -> None:
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

    assert not _memory_passes_search_summary_filters(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type="OUTCOME_REVIEW_CREATED",
            supportability_state=None,
            source_system=None,
            source_type=None,
        ),
        explicit_candidate_ids=set(),
    )
    assert not _memory_passes_search_summary_filters(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system="lotus-risk",
            source_type=None,
        ),
        explicit_candidate_ids=set(),
    )


def test_empty_memory_summary_filter_helper_requires_empty_filter_and_explicit_id() -> None:
    memory = _memory(portfolio_id="PB_EMPTY_001", events=[])
    filters = PortfolioMemorySearchFilters(
        event_type=None,
        supportability_state="EMPTY",
        source_system=None,
        source_type=None,
    )

    assert _empty_memory_matches_search_summary_filters(
        memory=memory,
        filters=filters,
        explicit_candidate_ids={"PB_EMPTY_001"},
    )
    assert not _empty_memory_matches_search_summary_filters(
        memory=memory,
        filters=filters,
        explicit_candidate_ids=set(),
    )
    assert not _empty_memory_matches_search_summary_filters(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system=None,
            source_type=None,
        ),
        explicit_candidate_ids={"PB_EMPTY_001"},
    )


def test_search_summary_predicate_helpers_match_optional_summary_fields() -> None:
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

    assert _event_type_matches_search_summary(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type="WAVE_HANDOFF_READY",
            supportability_state=None,
            source_system=None,
            source_type=None,
        ),
    )
    assert not _event_type_matches_search_summary(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type="OUTCOME_REVIEW_CREATED",
            supportability_state=None,
            source_system=None,
            source_type=None,
        ),
    )
    assert _supportability_matches_search_summary(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=memory.supportability_state,
            source_system=None,
            source_type=None,
        ),
    )
    assert _source_system_matches_search_summary(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system="lotus-core",
            source_type=None,
        ),
    )
    assert not _source_system_matches_search_summary(
        memory=memory,
        filters=PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system="lotus-risk",
            source_type=None,
        ),
    )


def test_filters_require_matching_events_tracks_event_level_filters() -> None:
    assert not _filters_require_matching_events(
        PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system=None,
            source_type=None,
        )
    )
    assert _filters_require_matching_events(
        PortfolioMemorySearchFilters(
            event_type=None,
            supportability_state=None,
            source_system=None,
            source_type="PortfolioManagerBookMembership",
        )
    )


def test_validate_search_page_pagination_accepts_advancing_page() -> None:
    _validate_search_page_pagination(
        returned_count=2,
        item_count=2,
        total_count=5,
        offset=0,
        has_more=True,
        next_offset=2,
    )


def test_validate_search_page_pagination_rejects_item_count_mismatch() -> None:
    with pytest.raises(ValueError, match="returned_count must equal"):
        _validate_search_page_pagination(
            returned_count=2,
            item_count=1,
            total_count=5,
            offset=0,
            has_more=True,
            next_offset=2,
        )


def test_validate_search_page_pagination_rejects_wrong_has_more_posture() -> None:
    with pytest.raises(ValueError, match="has_more must match"):
        _validate_search_page_pagination(
            returned_count=2,
            item_count=2,
            total_count=5,
            offset=0,
            has_more=False,
            next_offset=None,
        )


def test_validate_search_page_pagination_rejects_terminal_next_offset() -> None:
    with pytest.raises(ValueError, match="next_offset must be null"):
        _validate_search_page_pagination(
            returned_count=2,
            item_count=2,
            total_count=2,
            offset=0,
            has_more=False,
            next_offset=2,
        )


def test_search_page_pagination_helpers_project_has_more_and_next_offset() -> None:
    assert _page_has_more(offset=0, returned_count=2, total_count=5)
    assert not _page_has_more(offset=3, returned_count=2, total_count=5)
    assert _expected_search_page_next_offset(offset=10, returned_count=25, has_more=True) == 35
    assert _expected_search_page_next_offset(offset=10, returned_count=25, has_more=False) is None
    assert _search_page_is_terminal(False)
    assert not _search_page_is_terminal(True)
    assert _next_offset_matches_expected(next_offset=35, expected_next_offset=35)
    assert not _next_offset_matches_expected(next_offset=None, expected_next_offset=35)
    assert not _next_offset_matches_expected(next_offset=34, expected_next_offset=35)
    assert _next_offset_advances(offset=10, next_offset=35)
    assert not _next_offset_advances(offset=10, next_offset=10)


def test_search_page_next_offset_helper_rejects_non_advancing_offset() -> None:
    with pytest.raises(ValueError, match="next_offset must advance"):
        _validate_search_page_next_offset(
            offset=2,
            returned_count=0,
            has_more=True,
            next_offset=2,
        )


def test_terminal_search_page_next_offset_helper_requires_null_offset() -> None:
    _validate_terminal_search_page_next_offset(None)
    with pytest.raises(ValueError, match="next_offset must be null"):
        _validate_terminal_search_page_next_offset(2)


def test_validate_search_page_count_maps_rejects_negative_and_mismatched_totals() -> None:
    with pytest.raises(ValueError, match="event_type_counts values must be non-negative"):
        _validate_search_page_count_maps(
            total_count=1,
            supportability_state_counts={"READY": 1},
            event_type_counts={"WAVE_HANDOFF_READY": -1},
            matching_event_supportability_state_counts={},
            matching_event_source_system_counts={},
            matching_event_source_type_counts={},
            source_system_counts={"lotus-manage": 1},
        )

    with pytest.raises(ValueError, match="supportability_state_counts must sum"):
        _validate_search_page_count_maps(
            total_count=2,
            supportability_state_counts={"READY": 1},
            event_type_counts={},
            matching_event_supportability_state_counts={},
            matching_event_source_system_counts={},
            matching_event_source_type_counts={},
            source_system_counts={"lotus-manage": 1},
        )


def test_search_page_source_system_counts_projects_returned_item_sources() -> None:
    event = _event(
        event_id="memory:search:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        source_id="handoff-001",
        content_hash="sha256:handoff",
    )
    item = _portfolio_memory_search_item(
        memory=_memory(portfolio_id="PB_SEARCH_001", events=[event]),
        matching_events=[event],
    )

    assert _search_page_source_system_counts([item]) == {
        "lotus-core": 1,
        "lotus-manage": 1,
    }


def test_validate_search_page_returned_counts_covered_rejects_underreported_page_counts() -> None:
    with pytest.raises(ValueError, match="reported counts must cover page counts"):
        _validate_search_page_returned_counts_covered(
            reported_counts={"READY": 1},
            page_counts={"READY": 2},
            message="reported counts must cover page counts",
        )


def test_validate_complete_search_page_counts_rejects_matching_event_count_mismatch() -> None:
    with pytest.raises(ValueError, match="matching_event_supportability_state_counts must sum"):
        _validate_complete_search_page_counts(
            total_count=1,
            returned_count=1,
            supportability_state_counts={"READY": 1},
            page_supportability_counts={"READY": 1},
            source_system_counts={"lotus-manage": 1},
            page_source_system_counts={"lotus-manage": 1},
            matching_event_supportability_state_counts={"READY": 0},
            expected_matching_event_count=1,
        )


def test_validate_search_item_metadata_accepts_empty_search_item_metadata() -> None:
    _validate_search_item_metadata(
        event_count=0,
        event_type_counts={},
        source_systems=[],
        reason_codes=[],
        supportability_state="EMPTY",
        matching_event_count=0,
        latest_event_time=None,
        latest_event_type=None,
        latest_matching_event_time=None,
        latest_matching_event_type=None,
        latest_matching_event_id=None,
        latest_matching_event_identity=None,
        latest_matching_event_source_system=None,
        latest_matching_event_source_type=None,
        latest_matching_event_source_id=None,
        latest_matching_event_content_hash=None,
    )


def test_validate_search_item_count_helper_rejects_matching_count_above_event_count() -> None:
    with pytest.raises(ValueError, match="matching_event_count must not exceed"):
        _validate_search_item_counts(
            event_count=1,
            event_type_counts={"WAVE_HANDOFF_READY": 1},
            matching_event_count=2,
        )


def test_validate_search_item_sorted_aggregate_helper_rejects_duplicate_reasons() -> None:
    with pytest.raises(ValueError, match="reason_codes must be sorted and unique"):
        _validate_search_item_sorted_aggregates(
            source_systems=["lotus-manage"],
            reason_codes=["READY_FOR_OPERATIONS_REVIEW", "READY_FOR_OPERATIONS_REVIEW"],
        )


def test_validate_search_item_latest_event_helper_rejects_empty_item_with_latest_event() -> None:
    with pytest.raises(ValueError, match="empty search items must not carry latest event metadata"):
        _validate_search_item_latest_event_metadata(
            event_count=0,
            supportability_state="EMPTY",
            event_type_counts={},
            source_systems=[],
            reason_codes=[],
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type=None,
        )


def test_validate_search_item_latest_event_helper_rejects_empty_item_with_non_empty_state() -> None:
    with pytest.raises(ValueError, match="empty search items must use EMPTY supportability_state"):
        _validate_search_item_latest_event_metadata(
            event_count=0,
            supportability_state="READY",
            event_type_counts={},
            source_systems=[],
            reason_codes=[],
            latest_event_time=None,
            latest_event_type=None,
        )


def test_latest_event_metadata_presence_helpers_track_partial_and_complete_metadata() -> None:
    assert not _latest_event_metadata_is_present(
        latest_event_time=None,
        latest_event_type=None,
    )
    assert _latest_event_metadata_is_present(
        latest_event_time="2026-05-31T10:00:00+00:00",
        latest_event_type=None,
    )
    assert not _latest_event_metadata_is_complete(
        latest_event_time="2026-05-31T10:00:00+00:00",
        latest_event_type=None,
    )
    assert _latest_event_metadata_is_complete(
        latest_event_time="2026-05-31T10:00:00+00:00",
        latest_event_type="WAVE_HANDOFF_READY",
    )


@pytest.mark.parametrize(
    ("event_type_counts", "source_systems", "reason_codes"),
    [
        ({"WAVE_HANDOFF_READY": 1}, [], []),
        ({}, ["lotus-manage"], []),
        ({}, [], ["READY_FOR_OPERATIONS_REVIEW"]),
    ],
)
def test_empty_search_item_latest_event_helper_rejects_aggregate_metadata(
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
) -> None:
    with pytest.raises(ValueError, match="aggregate event metadata"):
        _validate_empty_search_item_latest_event_metadata(
            supportability_state="EMPTY",
            event_type_counts=event_type_counts,
            source_systems=source_systems,
            reason_codes=reason_codes,
            latest_event_time=None,
            latest_event_type=None,
        )


def test_populated_search_item_latest_event_helper_requires_complete_metadata() -> None:
    with pytest.raises(ValueError, match="must carry latest event metadata"):
        _validate_populated_search_item_latest_event_metadata(
            supportability_state="READY",
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type=None,
        )


def test_validate_search_item_latest_matching_helper_rejects_missing_identity() -> None:
    with pytest.raises(ValueError, match="matching events must carry latest matching"):
        _validate_search_item_latest_matching_event_metadata(
            matching_event_count=1,
            latest_matching_event_time="2026-05-31T10:00:00+00:00",
            latest_matching_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_id="memory:search:handoff",
            latest_matching_event_identity=None,
            latest_matching_event_source_system="lotus-manage",
            latest_matching_event_source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
            latest_matching_event_source_id="handoff-001",
            latest_matching_event_content_hash=None,
        )


def test_validate_search_item_metadata_rejects_mismatched_aggregates_and_ordering() -> None:
    with pytest.raises(ValueError, match="event_count must equal"):
        _validate_search_item_metadata(
            event_count=2,
            event_type_counts={"WAVE_HANDOFF_READY": 1},
            source_systems=["lotus-manage"],
            reason_codes=[],
            supportability_state="READY",
            matching_event_count=0,
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_time=None,
            latest_matching_event_type=None,
            latest_matching_event_id=None,
            latest_matching_event_identity=None,
            latest_matching_event_source_system=None,
            latest_matching_event_source_type=None,
            latest_matching_event_source_id=None,
            latest_matching_event_content_hash=None,
        )

    with pytest.raises(ValueError, match="source_systems must be sorted"):
        _validate_search_item_metadata(
            event_count=1,
            event_type_counts={"WAVE_HANDOFF_READY": 1},
            source_systems=["b", "a"],
            reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
            supportability_state="READY",
            matching_event_count=0,
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_time=None,
            latest_matching_event_type=None,
            latest_matching_event_id=None,
            latest_matching_event_identity=None,
            latest_matching_event_source_system=None,
            latest_matching_event_source_type=None,
            latest_matching_event_source_id=None,
            latest_matching_event_content_hash=None,
        )


def test_validate_search_item_metadata_rejects_missing_matching_event_metadata() -> None:
    with pytest.raises(ValueError, match="matching events must carry latest matching"):
        _validate_search_item_metadata(
            event_count=1,
            event_type_counts={"WAVE_HANDOFF_READY": 1},
            source_systems=["lotus-manage"],
            reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
            supportability_state="READY",
            matching_event_count=1,
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_time="2026-05-31T10:00:00+00:00",
            latest_matching_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_id=None,
            latest_matching_event_identity="memory:search:handoff",
            latest_matching_event_source_system="lotus-manage",
            latest_matching_event_source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
            latest_matching_event_source_id="handoff-001",
            latest_matching_event_content_hash="sha256:handoff",
        )


def test_validate_search_item_metadata_rejects_stale_matching_metadata() -> None:
    with pytest.raises(
        ValueError, match="no matching events must not carry latest matching event metadata"
    ):
        _validate_search_item_metadata(
            event_count=1,
            event_type_counts={"WAVE_HANDOFF_READY": 1},
            source_systems=["lotus-manage"],
            reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
            supportability_state="READY",
            matching_event_count=0,
            latest_event_time="2026-05-31T10:00:00+00:00",
            latest_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_time="2026-05-31T10:00:00+00:00",
            latest_matching_event_type="WAVE_HANDOFF_READY",
            latest_matching_event_id="memory:search:handoff",
            latest_matching_event_identity="memory:search:handoff:id",
            latest_matching_event_source_system="lotus-manage",
            latest_matching_event_source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
            latest_matching_event_source_id="handoff-001",
            latest_matching_event_content_hash=None,
        )


def test_portfolio_memory_search_item_projects_latest_matching_event() -> None:
    event = _event(
        event_id="memory:search:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        source_id="handoff-001",
        content_hash="sha256:handoff",
    )
    memory = _memory(portfolio_id="PB_SEARCH_001", events=[event])

    item = _portfolio_memory_search_item(memory=memory, matching_events=[event])

    assert item.portfolio_id == "PB_SEARCH_001"
    assert item.matching_event_count == 1
    assert item.latest_matching_event_id == "memory:search:handoff"
    assert item.latest_matching_event_source_type == "DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF"
    assert item.latest_matching_event_content_hash == "sha256:handoff"


def test_latest_event_metadata_projects_empty_and_populated_memory() -> None:
    event = _event(
        event_id="memory:search:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        source_id="handoff-001",
        content_hash="sha256:handoff",
    )

    assert _latest_event_metadata(
        _memory(portfolio_id="PB_SEARCH_EMPTY", events=[])
    ) == _LatestEventMetadata(latest_event_time=None, latest_event_type=None)
    assert _latest_event_metadata(
        _memory(portfolio_id="PB_SEARCH_001", events=[event])
    ) == _LatestEventMetadata(
        latest_event_time="2026-05-31T10:00:00+00:00",
        latest_event_type="WAVE_HANDOFF_READY",
    )


def test_latest_matching_event_metadata_projects_source_identity() -> None:
    event = _event(
        event_id="memory:search:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        source_id="handoff-001",
        content_hash="sha256:handoff",
    )

    assert _latest_matching_event_metadata([]) == _LatestMatchingEventMetadata(
        latest_matching_event_time=None,
        latest_matching_event_type=None,
        latest_matching_event_id=None,
        latest_matching_event_identity=None,
        latest_matching_event_source_system=None,
        latest_matching_event_source_type=None,
        latest_matching_event_source_id=None,
        latest_matching_event_content_hash=None,
    )
    assert _latest_matching_event_metadata([event]) == _LatestMatchingEventMetadata(
        latest_matching_event_time="2026-05-31T10:00:00+00:00",
        latest_matching_event_type="WAVE_HANDOFF_READY",
        latest_matching_event_id="memory:search:handoff",
        latest_matching_event_identity=event.event_identity,
        latest_matching_event_source_system="lotus-manage",
        latest_matching_event_source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        latest_matching_event_source_id="handoff-001",
        latest_matching_event_content_hash="sha256:handoff",
    )


def test_latest_matching_event_metadata_helpers_project_empty_and_event_payloads() -> None:
    event = _event(
        event_id="memory:search:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        source_id="handoff-001",
        content_hash="sha256:handoff",
    )

    assert _empty_latest_matching_event_metadata() == _LatestMatchingEventMetadata(
        latest_matching_event_time=None,
        latest_matching_event_type=None,
        latest_matching_event_id=None,
        latest_matching_event_identity=None,
        latest_matching_event_source_system=None,
        latest_matching_event_source_type=None,
        latest_matching_event_source_id=None,
        latest_matching_event_content_hash=None,
    )
    assert _latest_matching_event_metadata_from_event(event) == _LatestMatchingEventMetadata(
        latest_matching_event_time="2026-05-31T10:00:00+00:00",
        latest_matching_event_type="WAVE_HANDOFF_READY",
        latest_matching_event_id="memory:search:handoff",
        latest_matching_event_identity=event.event_identity,
        latest_matching_event_source_system="lotus-manage",
        latest_matching_event_source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        latest_matching_event_source_id="handoff-001",
        latest_matching_event_content_hash="sha256:handoff",
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
