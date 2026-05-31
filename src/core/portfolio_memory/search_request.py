"""Search request normalization for portfolio-memory queries."""

from dataclasses import dataclass
from typing import cast, get_args

from src.core.portfolio_memory.models import (
    PortfolioMemoryEventType,
    PortfolioMemorySupportabilityState,
)
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
PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPES = tuple(get_args(PortfolioMemoryEventType))
PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES = tuple(
    get_args(PortfolioMemorySupportabilityState)
)
_PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPE_SET = set(PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPES)
_PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATE_SET = set(
    PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES
)


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
            event_type=normalize_portfolio_memory_event_type_filter(event_type),
            supportability_state=normalize_portfolio_memory_supportability_state_filter(
                cast(str | None, supportability_state)
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


def normalize_portfolio_memory_event_type_filter(
    event_type: str | None,
) -> PortfolioMemoryEventType | None:
    normalized_event_type = normalize_portfolio_memory_search_filter(event_type)
    if normalized_event_type is None:
        return None
    if normalized_event_type not in _PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPE_SET:
        raise ValueError(
            f"UNSUPPORTED_PORTFOLIO_MEMORY_EVENT_TYPE: {normalized_event_type}; "
            f"supported_event_types={','.join(PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPES)}"
        )
    return cast(PortfolioMemoryEventType, normalized_event_type)


def normalize_portfolio_memory_supportability_state_filter(
    supportability_state: str | None,
) -> PortfolioMemorySupportabilityState | None:
    normalized_supportability_state = normalize_portfolio_memory_search_filter(supportability_state)
    if normalized_supportability_state is None:
        return None
    if normalized_supportability_state not in _PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATE_SET:
        raise ValueError(
            "UNSUPPORTED_PORTFOLIO_MEMORY_SUPPORTABILITY_STATE: "
            f"{normalized_supportability_state}; supported_supportability_states="
            f"{','.join(PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES)}"
        )
    return cast(PortfolioMemorySupportabilityState, normalized_supportability_state)


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
