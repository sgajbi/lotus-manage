"""Search request normalization for portfolio-memory queries."""

from dataclasses import dataclass
from typing import cast

from src.core.portfolio_memory.models import PortfolioMemorySupportabilityState
from src.core.portfolio_memory.search_filters import normalize_portfolio_memory_search_filter
from src.core.portfolio_memory.search_page import PortfolioMemorySearchFilters

PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT = 50
PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN = 1
PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX = 200
PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT = 0
PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN = 0
PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT = 500
PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN = 1
PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX = 1000


@dataclass(frozen=True)
class PortfolioMemorySearchQuery:
    filters: PortfolioMemorySearchFilters
    explicit_candidate_ids: set[str]
    limit: int
    offset: int
    source_scan_limit: int


def build_portfolio_memory_search_query(
    *,
    portfolio_ids: list[str] | None,
    event_type: str | None,
    supportability_state: PortfolioMemorySupportabilityState | None,
    source_system: str | None,
    source_type: str | None,
    limit: int,
    offset: int,
    source_scan_limit: int,
) -> PortfolioMemorySearchQuery:
    _validate_search_pagination(
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
    )
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
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
    )


def _validate_search_pagination(
    *,
    limit: int,
    offset: int,
    source_scan_limit: int,
) -> None:
    if limit < PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN or limit > PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX:
        raise ValueError(
            "portfolio-memory search limit must be between "
            f"{PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN} and {PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX}"
        )
    if offset < PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN:
        raise ValueError("portfolio-memory search offset must be greater than or equal to 0")
    validate_portfolio_memory_source_scan_limit(source_scan_limit=source_scan_limit)


def validate_portfolio_memory_source_scan_limit(*, source_scan_limit: int) -> int:
    if (
        source_scan_limit < PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN
        or source_scan_limit > PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX
    ):
        raise ValueError(
            "portfolio-memory source_scan_limit must be between "
            f"{PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN} and "
            f"{PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX}"
        )
    return source_scan_limit
