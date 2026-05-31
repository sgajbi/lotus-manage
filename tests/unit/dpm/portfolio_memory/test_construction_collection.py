from src.core.portfolio_memory.construction_collection import construction_memory_events
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _construction_repository,
)


def test_construction_memory_events_projects_alternative_set_and_selection() -> None:
    repository = _construction_repository()

    events = construction_memory_events(
        portfolio_id=PORTFOLIO_ID,
        construction_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "CONSTRUCTION_ALTERNATIVE_SET",
        "CONSTRUCTION_ALTERNATIVE_SELECTED",
    ]
    assert events[0].source_id == "cas_memory_001"
    assert events[0].metadata["alternative_count"] == 1
    assert events[1].source_id == "casel_memory_001"
    assert events[1].metadata["selected_method"] == "DO_NOTHING_BASELINE"


def test_construction_memory_events_keeps_alternative_set_without_selection() -> None:
    repository = _construction_repository()

    events = construction_memory_events(
        portfolio_id=PORTFOLIO_ID,
        construction_repository=repository,
        limit=100,
    )

    alternative_only_events = construction_memory_events(
        portfolio_id=PORTFOLIO_ID,
        construction_repository=_AlternativeOnlyConstructionRepository(repository),
        limit=100,
    )

    assert len(events) == 2
    assert [event.event_type for event in alternative_only_events] == [
        "CONSTRUCTION_ALTERNATIVE_SET"
    ]


class _AlternativeOnlyConstructionRepository:
    def __init__(self, wrapped) -> None:
        self._wrapped = wrapped

    def list_alternative_sets(self, *, portfolio_id: str, limit: int):
        return self._wrapped.list_alternative_sets(portfolio_id=portfolio_id, limit=limit)

    def get_selection(self, *, alternative_set_id: str):
        return None
