"""Search request normalization for portfolio-memory queries."""

from dataclasses import dataclass
from typing import cast

from src.core.portfolio_memory.models import PortfolioMemorySupportabilityState
from src.core.portfolio_memory.search_filters import normalize_portfolio_memory_search_filter
from src.core.portfolio_memory.search_page import PortfolioMemorySearchFilters


@dataclass(frozen=True)
class PortfolioMemorySearchQuery:
    filters: PortfolioMemorySearchFilters
    explicit_candidate_ids: set[str]


def build_portfolio_memory_search_query(
    *,
    portfolio_ids: list[str] | None,
    event_type: str | None,
    supportability_state: PortfolioMemorySupportabilityState | None,
    source_system: str | None,
    source_type: str | None,
) -> PortfolioMemorySearchQuery:
    return PortfolioMemorySearchQuery(
        filters=PortfolioMemorySearchFilters(
            event_type=normalize_portfolio_memory_search_filter(event_type),
            supportability_state=cast(
                PortfolioMemorySupportabilityState | None,
                normalize_portfolio_memory_search_filter(cast(str | None, supportability_state)),
            ),
            source_system=normalize_portfolio_memory_search_filter(source_system),
            source_type=normalize_portfolio_memory_search_filter(source_type),
        ),
        explicit_candidate_ids={
            portfolio_id.strip() for portfolio_id in (portfolio_ids or []) if portfolio_id.strip()
        },
    )
