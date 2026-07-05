from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.search_filters import (
    count_values,
    dedupe_and_sort_events,
    event_matches_search_filters,
    event_source_systems,
    event_source_types,
    _event_source_system_matches,
    _event_source_type_matches,
    _event_type_matches,
    normalize_portfolio_memory_search_filter,
)


def _event(
    *,
    event_id: str = "event_001",
    event_time: str = "2026-05-31T00:00:00+00:00",
    supportability_state: str = "READY",
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type="WAVE_EVENT",
        event_time=event_time,
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DpmRebalanceWave",
        source_id=event_id,
        status=supportability_state,
        supportability_state=supportability_state,
        summary="Portfolio memory search helper test event.",
        source_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-core",
                source_type="PortfolioManagerBookMembership",
                source_id="pm-book-001",
            )
        ],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-report",
                source_type="REPORT_INPUT",
                source_id="report-input-001",
            )
        ],
    )


def test_normalize_portfolio_memory_search_filter_preserves_explicit_values() -> None:
    assert normalize_portfolio_memory_search_filter(None) is None
    assert normalize_portfolio_memory_search_filter("   ") is None
    assert normalize_portfolio_memory_search_filter(" lotus-core ") == "lotus-core"


def test_event_source_facets_include_event_source_refs_and_artifact_refs() -> None:
    event = _event()

    assert event_source_systems(event) == {"lotus-manage", "lotus-core", "lotus-report"}
    assert event_source_types(event) == {
        "DpmRebalanceWave",
        "PortfolioManagerBookMembership",
        "REPORT_INPUT",
    }


def test_event_matches_search_filters_across_source_facets() -> None:
    event = _event()

    assert event_matches_search_filters(
        event=event,
        event_type="WAVE_EVENT",
        source_system="lotus-report",
        source_type="REPORT_INPUT",
    )


def test_event_search_filter_predicates_match_optional_fields_and_facets() -> None:
    event = _event()

    assert _event_type_matches(event=event, event_type=None)
    assert _event_type_matches(event=event, event_type="WAVE_EVENT")
    assert not _event_type_matches(event=event, event_type="OUTCOME_REVIEW_CREATED")
    assert _event_source_system_matches(event=event, source_system=None)
    assert _event_source_system_matches(event=event, source_system="lotus-core")
    assert not _event_source_system_matches(event=event, source_system="lotus-risk")
    assert _event_source_type_matches(event=event, source_type=None)
    assert _event_source_type_matches(event=event, source_type="REPORT_INPUT")
    assert not _event_source_type_matches(event=event, source_type="RiskMetricsReport")
    assert not event_matches_search_filters(
        event=event,
        event_type="OUTCOME_REVIEW_CREATED",
        source_system="lotus-report",
        source_type="REPORT_INPUT",
    )


def test_count_values_and_event_sorting_are_deterministic() -> None:
    older = _event(event_id="event_older", event_time="2026-05-30T00:00:00+00:00")
    newer = _event(event_id="event_newer", event_time="2026-05-31T00:00:00+00:00")
    duplicate_newer = _event(event_id="event_newer", event_time="2026-05-31T00:00:00+00:00")

    assert count_values(["READY", "READY", "BLOCKED"]) == {"READY": 2, "BLOCKED": 1}
    assert [
        event.event_id for event in dedupe_and_sort_events([older, newer, duplicate_newer])
    ] == [
        "event_newer",
        "event_older",
    ]


def test_dedupe_and_sort_events_keeps_latest_duplicate_event_independent_of_input_order() -> None:
    older_duplicate = _event(
        event_id="event_duplicate",
        event_time="2026-05-30T00:00:00+00:00",
    ).model_copy(update={"content_hash": "sha256:older"})
    latest_duplicate = _event(
        event_id="event_duplicate",
        event_time="2026-05-31T00:00:00+00:00",
    ).model_copy(update={"content_hash": "sha256:latest"})

    first = dedupe_and_sort_events([older_duplicate, latest_duplicate])
    second = dedupe_and_sort_events([latest_duplicate, older_duplicate])

    assert [event.content_hash for event in first] == ["sha256:latest"]
    assert [event.content_hash for event in second] == ["sha256:latest"]
