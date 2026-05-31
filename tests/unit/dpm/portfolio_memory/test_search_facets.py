from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.search_facets import build_search_facet_counts


def test_build_search_facet_counts_uses_matching_events_and_row_coverage() -> None:
    event = DpmPortfolioMemoryEvent(
        event_id="memory:facet:handoff",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id="handoff-001",
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
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-report",
                source_type="REPORT_INPUT",
                source_id="report-input-001",
            )
        ],
        content_hash="sha256:handoff",
    )
    search_item = DpmPortfolioMemorySearchItem(
        portfolio_id="PB_SEARCH_001",
        event_count=1,
        supportability_state="READY",
        event_type_counts={"WAVE_HANDOFF_READY": 1},
        source_systems=["lotus-core", "lotus-manage", "lotus-report"],
        reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
        latest_event_time=event.event_time,
        latest_event_type=event.event_type,
        matching_event_count=1,
        latest_matching_event_time=event.event_time,
        latest_matching_event_type=event.event_type,
        latest_matching_event_id=event.event_id,
        latest_matching_event_identity=event.event_identity,
        latest_matching_event_source_system=event.source_system,
        latest_matching_event_source_type=event.source_type,
        latest_matching_event_source_id=event.source_id,
        latest_matching_event_content_hash=event.content_hash,
        content_hash="sha256:memory",
    )

    facets = build_search_facet_counts([(search_item, [event])])

    assert facets.supportability_state_counts == {"READY": 1}
    assert facets.event_type_counts == {"WAVE_HANDOFF_READY": 1}
    assert facets.matching_event_supportability_state_counts == {"READY": 1}
    assert facets.matching_event_source_system_counts == {
        "lotus-core": 1,
        "lotus-manage": 1,
        "lotus-report": 1,
    }
    assert facets.matching_event_source_type_counts == {
        "DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF": 1,
        "PortfolioManagerBookMembership": 1,
        "REPORT_INPUT": 1,
    }
    assert facets.source_system_counts == {
        "lotus-core": 1,
        "lotus-manage": 1,
        "lotus-report": 1,
    }
