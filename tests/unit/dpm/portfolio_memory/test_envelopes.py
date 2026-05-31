from src.core.portfolio_memory.envelopes import (
    finalize_event_lookup,
    finalize_portfolio_memory,
    finalize_search_page_payload,
    replay_stable_content_hash,
)
from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence,
    external_execution_boundary_evidence,
    portfolio_memory_governance_policy,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemoryEventLookup,
    DpmPortfolioMemorySearchAppliedFilters,
)


def test_replay_stable_content_hash_excludes_generated_at_and_existing_hash() -> None:
    first = {
        "portfolio_id": "PB_001",
        "content_hash": "sha256:first",
        "generated_at": "2026-05-31T01:00:00+00:00",
    }
    later = {
        "portfolio_id": "PB_001",
        "content_hash": "sha256:later",
        "generated_at": "2026-05-31T02:00:00+00:00",
    }

    assert replay_stable_content_hash(first) == replay_stable_content_hash(later)


def test_finalize_portfolio_memory_keeps_hash_stable_across_generated_at() -> None:
    first = _empty_memory(generated_at="2026-05-31T01:00:00+00:00")
    later = _empty_memory(generated_at="2026-05-31T02:00:00+00:00")

    finalized_first = finalize_portfolio_memory(first)
    finalized_later = finalize_portfolio_memory(later)

    assert finalized_first.content_hash.startswith("sha256:")
    assert finalized_first.content_hash == finalized_later.content_hash


def test_finalize_search_page_payload_validates_and_hashes_page() -> None:
    first = finalize_search_page_payload(
        _empty_search_page_payload(generated_at="2026-05-31T01:00:00+00:00")
    )
    later = finalize_search_page_payload(
        _empty_search_page_payload(generated_at="2026-05-31T02:00:00+00:00")
    )

    assert first.returned_count == 0
    assert first.content_hash.startswith("sha256:")
    assert first.content_hash == later.content_hash


def test_finalize_event_lookup_keeps_hash_stable_across_generated_at() -> None:
    event = DpmPortfolioMemoryEvent(
        event_id="memory:test:event-001",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T01:00:00+00:00",
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id="handoff-001",
        status="READY",
        supportability_state="READY",
        summary="Internal handoff recorded.",
        content_hash="sha256:event",
    )
    first = finalize_event_lookup(_lookup(event=event, generated_at="2026-05-31T01:00:00+00:00"))
    later = finalize_event_lookup(_lookup(event=event, generated_at="2026-05-31T02:00:00+00:00"))

    assert first.content_hash.startswith("sha256:")
    assert first.content_hash == later.content_hash


def _empty_memory(*, generated_at: str) -> DpmPortfolioMemory:
    return DpmPortfolioMemory(
        portfolio_id="PB_EMPTY_001",
        event_count=0,
        supportability_state="EMPTY",
        event_type_counts={},
        source_systems=[],
        reason_codes=[],
        governance_policy=portfolio_memory_governance_policy(),
        source_event_family_posture=[],
        external_execution_boundary=external_execution_boundary_evidence(),
        client_communication_boundary=client_communication_boundary_evidence(),
        events=[],
        content_hash="sha256:pending",
        generated_at=generated_at,
    )


def _empty_search_page_payload(*, generated_at: str) -> dict[str, object]:
    return {
        "items": [],
        "limit": 50,
        "offset": 0,
        "returned_count": 0,
        "total_count": 0,
        "has_more": False,
        "next_offset": None,
        "scanned_portfolio_count": 0,
        "source_scan_limit": 500,
        "applied_filters": DpmPortfolioMemorySearchAppliedFilters(),
        "supportability_state_counts": {},
        "event_type_counts": {},
        "matching_event_supportability_state_counts": {},
        "matching_event_source_system_counts": {},
        "matching_event_source_type_counts": {},
        "source_system_counts": {},
        "source_event_family_posture": [],
        "external_execution_boundary": external_execution_boundary_evidence(),
        "client_communication_boundary": client_communication_boundary_evidence(),
        "generated_at": generated_at,
        "support_boundary": "Manage-local test search boundary.",
    }


def _lookup(
    *,
    event: DpmPortfolioMemoryEvent,
    generated_at: str,
) -> DpmPortfolioMemoryEventLookup:
    return DpmPortfolioMemoryEventLookup(
        portfolio_id="PB_LOOKUP_001",
        event_id=event.event_id,
        event_identity=event.event_identity,
        event=event,
        memory_content_hash="sha256:memory",
        content_hash="sha256:pending",
        generated_at=generated_at,
        support_boundary="Manage-local test lookup boundary.",
    )
