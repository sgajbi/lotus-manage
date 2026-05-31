from datetime import datetime, timezone

from src.core.portfolio_memory.aggregate import build_portfolio_memory_aggregate
from src.core.portfolio_memory.event_lookup import build_portfolio_memory_event_lookup
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent


def test_build_portfolio_memory_event_lookup_returns_exact_event_envelope() -> None:
    memory = build_portfolio_memory_aggregate(
        portfolio_id="PB_LOOKUP_001",
        events=[
            _event(
                event_id="memory:test:older",
                event_time="2026-05-31T09:00:00+00:00",
            ),
            _event(
                event_id="memory:test:target",
                event_time="2026-05-31T10:00:00+00:00",
            ),
        ],
        limit=100,
        generated_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    lookup = build_portfolio_memory_event_lookup(
        memory=memory,
        event_id="memory:test:target",
        support_boundary="Manage-local lookup test boundary.",
    )

    assert lookup is not None
    assert lookup.portfolio_id == "PB_LOOKUP_001"
    assert lookup.event_id == "memory:test:target"
    assert lookup.event.event_id == "memory:test:target"
    assert lookup.event_identity == lookup.event.event_identity
    assert lookup.memory_content_hash == memory.content_hash
    assert lookup.support_boundary == "Manage-local lookup test boundary."
    assert lookup.content_hash.startswith("sha256:")


def test_build_portfolio_memory_event_lookup_returns_none_for_missing_event() -> None:
    memory = build_portfolio_memory_aggregate(
        portfolio_id="PB_LOOKUP_001",
        events=[
            _event(
                event_id="memory:test:available",
                event_time="2026-05-31T10:00:00+00:00",
            )
        ],
        limit=100,
        generated_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert (
        build_portfolio_memory_event_lookup(
            memory=memory,
            event_id="memory:test:missing",
            support_boundary="Manage-local lookup test boundary.",
        )
        is None
    )


def _event(*, event_id: str, event_time: str) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type="WAVE_HANDOFF_READY",
        event_time=event_time,
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id=event_id,
        status="READY",
        supportability_state="READY",
        summary="Internal handoff recorded.",
        reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
        content_hash=f"sha256:{event_id}",
    )
