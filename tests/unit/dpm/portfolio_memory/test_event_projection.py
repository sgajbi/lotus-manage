from src.core.portfolio_memory.event_projection import (
    event_source_systems,
    event_source_types,
    portfolio_memory_supportability_state,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)


def _event(
    *,
    event_id: str = "event_001",
    supportability_state: str = "READY",
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type="WAVE_EVENT",
        event_time="2026-05-31T00:00:00+00:00",
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DpmRebalanceWave",
        source_id=event_id,
        status=supportability_state,
        supportability_state=supportability_state,
        summary="Portfolio memory projection helper test event.",
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


def test_event_projection_collects_source_systems_and_types() -> None:
    event = _event()

    assert event_source_systems(event) == {"lotus-manage", "lotus-core", "lotus-report"}
    assert event_source_types(event) == {
        "DpmRebalanceWave",
        "PortfolioManagerBookMembership",
        "REPORT_INPUT",
    }


def test_portfolio_memory_supportability_state_uses_fail_closed_precedence() -> None:
    assert portfolio_memory_supportability_state([]) == "EMPTY"
    assert portfolio_memory_supportability_state([_event()]) == "READY"
    assert (
        portfolio_memory_supportability_state(
            [
                _event(event_id="event_ready"),
                _event(event_id="event_review", supportability_state="PENDING_REVIEW"),
                _event(event_id="event_degraded", supportability_state="DEGRADED"),
            ]
        )
        == "DEGRADED"
    )
    assert (
        portfolio_memory_supportability_state(
            [
                _event(event_id="event_degraded", supportability_state="DEGRADED"),
                _event(event_id="event_blocked", supportability_state="BLOCKED"),
            ]
        )
        == "BLOCKED"
    )
