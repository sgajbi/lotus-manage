"""Mandate repository collection for portfolio-memory events."""

from src.core.mandate_repository import DpmMandateRepository
from src.core.portfolio_memory.mandate_projection import (
    mandate_exception_event,
    mandate_health_event,
)
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent


def mandate_memory_events(
    *,
    portfolio_id: str,
    mandate_repository: DpmMandateRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect mandate-health and mandate-monitoring memory events for one portfolio."""

    twin = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    events: list[DpmPortfolioMemoryEvent] = []
    if twin is not None:
        health_snapshot = mandate_repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
        if health_snapshot is not None:
            events.append(
                mandate_health_event(
                    health_snapshot=health_snapshot,
                    source_lineage=twin.source_lineage,
                )
            )

    exceptions, _cursor = mandate_repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=twin.mandate_id if twin is not None else None,
        portfolio_id=portfolio_id,
        state=None,
        limit=limit,
        cursor=None,
    )
    events.extend(mandate_exception_event(exception) for exception in exceptions)
    return events
