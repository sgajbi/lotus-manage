from datetime import datetime, timezone

from src.core.portfolio_memory.aggregate import build_portfolio_memory_aggregate
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)


def test_build_portfolio_memory_aggregate_dedupes_sorts_and_limits_events() -> None:
    memory = build_portfolio_memory_aggregate(
        portfolio_id="PB_AGG_001",
        events=[
            _event(
                event_id="memory:test:older",
                event_type="PROOF_PACK_CREATED",
                event_time="2026-05-31T08:00:00+00:00",
                supportability_state="READY",
                reason_codes=["PROOF_PACK_AVAILABLE"],
            ),
            _event(
                event_id="memory:test:duplicate",
                event_type="WAVE_HANDOFF_READY",
                event_time="2026-05-31T09:00:00+00:00",
                supportability_state="READY",
                reason_codes=["STALE_DUPLICATE"],
            ),
            _event(
                event_id="memory:test:duplicate",
                event_type="MANDATE_MONITORING_EXCEPTION",
                event_time="2026-05-31T10:00:00+00:00",
                supportability_state="DEGRADED",
                reason_codes=["MANDATE_BREACH_OPEN"],
            ),
        ],
        limit=1,
        generated_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert memory.event_count == 1
    assert [event.event_id for event in memory.events] == ["memory:test:duplicate"]
    assert memory.event_type_counts == {"MANDATE_MONITORING_EXCEPTION": 1}
    assert memory.supportability_state == "DEGRADED"
    assert memory.reason_codes == ["MANDATE_BREACH_OPEN"]
    assert memory.content_hash.startswith("sha256:")


def test_build_portfolio_memory_aggregate_projects_governance_and_source_facets() -> None:
    memory = build_portfolio_memory_aggregate(
        portfolio_id="PB_AGG_002",
        events=[
            _event(
                event_id="memory:test:ready",
                event_type="WAVE_HANDOFF_READY",
                event_time="2026-05-31T10:00:00+00:00",
                supportability_state="READY",
                reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
                source_refs=[
                    DpmPortfolioMemorySourceRef(
                        source_system="lotus-core",
                        source_type="PortfolioManagerBookMembership",
                        source_id="pm-book:PB_AGG_002",
                    )
                ],
                artifact_refs=[
                    DpmPortfolioMemorySourceRef(
                        source_system="lotus-ai",
                        source_type="PortfolioMemorySummary",
                        source_id="summary-001",
                        content_hash="sha256:summary",
                    )
                ],
            )
        ],
        limit=100,
        generated_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert memory.source_systems == ["lotus-ai", "lotus-core", "lotus-manage"]
    assert memory.governance_policy["retention_policy"] == "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y"
    assert memory.external_execution_boundary.external_execution_events_projected is False
    assert memory.client_communication_boundary.client_communication_events_projected is False
    assert memory.source_event_family_posture


def test_build_portfolio_memory_aggregate_marks_empty_memory_explicitly() -> None:
    memory = build_portfolio_memory_aggregate(
        portfolio_id="PB_EMPTY_001",
        events=[],
        limit=100,
        generated_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert memory.event_count == 0
    assert memory.supportability_state == "EMPTY"
    assert memory.event_type_counts == {}
    assert memory.source_systems == []


def _event(
    *,
    event_id: str,
    event_type: str,
    event_time: str,
    supportability_state: str,
    reason_codes: list[str],
    source_refs: list[DpmPortfolioMemorySourceRef] | None = None,
    artifact_refs: list[DpmPortfolioMemorySourceRef] | None = None,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type=event_type,
        event_time=event_time,
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_MEMORY_TEST_SOURCE",
        source_id=event_id,
        status=supportability_state,
        supportability_state=supportability_state,
        summary="Portfolio memory aggregate test event.",
        reason_codes=reason_codes,
        source_refs=source_refs or [],
        artifact_refs=artifact_refs or [],
        content_hash=f"sha256:{event_id}",
    )
