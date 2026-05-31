"""Construction repository collection for portfolio-memory events."""

from src.core.construction.repository import ConstructionRepository
from src.core.portfolio_memory.construction_projection import (
    construction_alternative_set_event,
    construction_selection_event,
)
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent


def construction_memory_events(
    *,
    portfolio_id: str,
    construction_repository: ConstructionRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect construction alternative-set and selection memory events for one portfolio."""

    alternative_sets = construction_repository.list_alternative_sets(
        portfolio_id=portfolio_id,
        limit=limit,
    )
    events: list[DpmPortfolioMemoryEvent] = []
    for alternative_set in alternative_sets:
        events.append(construction_alternative_set_event(alternative_set))
        selection = construction_repository.get_selection(
            alternative_set_id=alternative_set.alternative_set_id
        )
        if selection is not None:
            events.append(
                construction_selection_event(
                    alternative_set=alternative_set,
                    selection=selection,
                )
            )
    return events
