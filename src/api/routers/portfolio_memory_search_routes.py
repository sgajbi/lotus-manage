"""Search route for RFC-0040 portfolio memory."""

from typing import NoReturn

from fastapi import Depends, HTTPException, Query, status

from src.api.routers.portfolio_memory import get_portfolio_memory_source_repositories, router
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedIdentity,
    pm_quality_trusted_identity_required,
)
from src.core.portfolio_memory import DpmPortfolioMemorySearchPage
from src.core.portfolio_memory.search_request import (
    PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX,
    PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN,
    PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
    PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN,
    PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPES,
    PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES,
    normalize_portfolio_memory_event_type_filter,
    normalize_portfolio_memory_supportability_state_filter,
)
from src.core.portfolio_memory.service import search_portfolio_memory_from_sources
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories


_SUPPORTED_EVENT_TYPE_DESCRIPTION = ", ".join(
    f"`{event_type}`" for event_type in PORTFOLIO_MEMORY_SUPPORTED_EVENT_TYPES
)
_SUPPORTED_SUPPORTABILITY_STATE_DESCRIPTION = ", ".join(
    f"`{state}`" for state in PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES
)
_SUPPORTED_SUPPORTABILITY_STATE_PATTERN = (
    r"^\s*(" + "|".join(PORTFOLIO_MEMORY_SUPPORTED_SUPPORTABILITY_STATES) + r")\s*$"
)


def _raise_portfolio_memory_search_validation_error(exc: ValueError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    ) from exc


@router.get(
    "/search",
    response_model=DpmPortfolioMemorySearchPage,
    summary="Search Manage-local portfolio memory",
    description=(
        "What: Return a bounded search page of portfolio-memory summaries built from persisted "
        "Manage evidence and optional caller-supplied portfolio identifiers.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need to find "
        "portfolios with existing Manage memory evidence before loading a single portfolio "
        "timeline.\n"
        "How: The endpoint scans each supported Manage-local source family once per bounded "
        "request, groups projected memory events by candidate portfolio, and returns exact totals "
        "and facets over that bounded scan. It can filter by event type, aggregate supportability "
        "state, represented source system, and represented source type. Aggregate supportability "
        "filtering is applied to portfolio-memory summaries only; matching-event metadata and "
        "facets remain driven by event/source filters. It does "
        "not discover the global portfolio universe, "
        "query external source-owner event stores, project OMS acknowledgement/fill/settlement "
        "events, project client contact/message/delivery/approval events, or recalculate risk, "
        "performance, execution, tax, cash, FX, mandate-health, PM-quality score/review-action, "
        "report, archive, or AI truth."
    ),
)
def search_portfolio_memory_index(
    portfolio_ids: list[str] | None = Query(
        default=None,
        description=(
            "Optional portfolio identifiers to include in addition to portfolios discovered from "
            "Manage-local persisted evidence. This is not a global portfolio-universe selector."
        ),
    ),
    event_type: str | None = Query(
        default=None,
        description=(
            "Optional portfolio-memory event type filter. Unsupported event types are rejected "
            "instead of being interpreted as an empty source result. Supported event types: "
            f"{_SUPPORTED_EVENT_TYPE_DESCRIPTION}."
        ),
        examples=["WAVE_HANDOFF_READY"],
    ),
    supportability_state: str | None = Query(
        default=None,
        pattern=_SUPPORTED_SUPPORTABILITY_STATE_PATTERN,
        description=(
            "Optional aggregate portfolio-memory supportability-state filter applied to search "
            "summaries only; it does not filter matching-event metadata or matching-event facets. "
            "Leading and trailing whitespace is normalized before matching. Supported states: "
            f"{_SUPPORTED_SUPPORTABILITY_STATE_DESCRIPTION}."
        ),
        examples=["READY"],
    ),
    source_system: str | None = Query(
        default=None,
        description=(
            "Optional represented source-system filter. Leading and trailing whitespace is "
            "normalized before matching."
        ),
        examples=["lotus-manage"],
    ),
    source_type: str | None = Query(
        default=None,
        description=(
            "Optional represented source-type filter across matching events, source refs, and "
            "artifact refs. Leading and trailing whitespace is normalized before matching."
        ),
        examples=["DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF"],
    ),
    limit: int = Query(
        default=PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
        ge=PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN,
        le=PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX,
        description="Maximum summaries to return.",
    ),
    offset: int = Query(
        default=PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
        ge=PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN,
        description="Zero-based page offset.",
    ),
    source_scan_limit: int = Query(
        default=PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
        ge=PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN,
        le=PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX,
        description=(
            "Maximum rows to scan from each Manage-local evidence repository. Search totals and "
            "facet counts are exact over the bounded source-family scan, not over a global "
            "portfolio universe."
        ),
    ),
    repositories: PortfolioMemorySourceRepositories = Depends(
        get_portfolio_memory_source_repositories
    ),
    identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
) -> DpmPortfolioMemorySearchPage:
    try:
        normalized_event_type = normalize_portfolio_memory_event_type_filter(event_type)
        normalized_supportability_state = normalize_portfolio_memory_supportability_state_filter(
            supportability_state
        )
    except ValueError as exc:
        _raise_portfolio_memory_search_validation_error(exc)
    try:
        return search_portfolio_memory_from_sources(
            tenant_id=identity.tenant_id,
            repositories=repositories,
            portfolio_ids=portfolio_ids,
            event_type=normalized_event_type,
            supportability_state=normalized_supportability_state,
            source_system=source_system,
            source_type=source_type,
            limit=limit,
            offset=offset,
            source_scan_limit=source_scan_limit,
        )
    except ValueError as exc:
        _raise_portfolio_memory_search_validation_error(exc)
