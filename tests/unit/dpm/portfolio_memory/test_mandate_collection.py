from src.core.portfolio_memory.mandate_collection import mandate_memory_events
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _health_snapshot,
    _mandate_twin,
    _monitoring_exception,
)


def test_mandate_memory_events_projects_latest_health_and_monitoring_exceptions() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_mandate_twin())
    repository.save_health_snapshot(_health_snapshot())
    repository.save_monitoring_exception(_monitoring_exception())

    events = mandate_memory_events(
        portfolio_id=PORTFOLIO_ID,
        mandate_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "MANDATE_HEALTH_SNAPSHOT",
        "MANDATE_MONITORING_EXCEPTION",
    ]
    assert events[0].source_id == _health_snapshot().health_snapshot_id
    assert events[0].source_refs[0].source_type == "CoreMandateBinding"
    assert events[1].source_id == _monitoring_exception().exception_id
    assert events[1].metadata["monitoring_run_id"] == "dmr_memory_001"


def test_mandate_memory_events_keeps_portfolio_exception_when_mandate_twin_absent() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_health_snapshot(_health_snapshot())
    repository.save_monitoring_exception(_monitoring_exception())

    events = mandate_memory_events(
        portfolio_id=PORTFOLIO_ID,
        mandate_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == ["MANDATE_MONITORING_EXCEPTION"]
    assert events[0].source_id == _monitoring_exception().exception_id
