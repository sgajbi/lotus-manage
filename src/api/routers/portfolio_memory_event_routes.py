"""Exact event lookup route for RFC-0040 portfolio memory."""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status

from src.api.routers.portfolio_memory import get_portfolio_memory_source_repositories, router
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedIdentity,
    pm_quality_trusted_identity_required,
)
from src.core.portfolio_memory.event_lookup import build_portfolio_memory_event_lookup
from src.core.portfolio_memory.models import DpmPortfolioMemoryEventLookup
from src.core.portfolio_memory.read_request import (
    PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_MAX,
    PORTFOLIO_MEMORY_READ_LIMIT_MIN,
)
from src.core.portfolio_memory.service import build_portfolio_memory_from_sources
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories


@router.get(
    "/{portfolio_id}/events/{event_id}",
    response_model=DpmPortfolioMemoryEventLookup,
    summary="Get one portfolio-memory event",
    description=(
        "What: Return one exact source-backed portfolio-memory event for a portfolio using the "
        "stable event id surfaced by the timeline or search API.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need to "
        "drill down from a search hit into the exact event row without loading unrelated "
        "portfolio-memory rows.\n"
        "How: The endpoint composes the same Manage-local memory view as the detail route, "
        "selects the requested event id, and returns the event with the memory content hash for "
        "reconciliation. It does not discover the global portfolio universe, query external "
        "source-owner event stores, project OMS acknowledgement/fill/settlement events, project "
        "client contact/message/delivery/approval events, or recalculate risk, performance, "
        "execution, tax, cash, FX, mandate-health, PM-quality, report, archive, or AI truth."
    ),
)
def get_portfolio_memory_event(
    portfolio_id: Annotated[
        str,
        Path(
            description=(
                "Portfolio identifier for the Manage-local source-backed memory timeline."
            ),
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ],
    event_id: Annotated[
        str,
        Path(
            description=(
                "Stable portfolio-memory event id returned by the timeline or search result."
            ),
            examples=["memory:proof-pack:dpp_c09f73d0"],
        ),
    ],
    limit: int = Query(
        default=PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_DEFAULT,
        ge=PORTFOLIO_MEMORY_READ_LIMIT_MIN,
        le=PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_MAX,
        description="Maximum source-backed memory events to scan while locating the requested event.",
    ),
    repositories: PortfolioMemorySourceRepositories = Depends(
        get_portfolio_memory_source_repositories
    ),
    identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
) -> DpmPortfolioMemoryEventLookup:
    memory = build_portfolio_memory_from_sources(
        tenant_id=identity.tenant_id,
        portfolio_id=portfolio_id,
        repositories=repositories,
        limit=limit,
    )
    lookup = build_portfolio_memory_event_lookup(
        memory=memory,
        event_id=event_id,
        support_boundary=(
            "Manage-local memory event lookup selects exact events from persisted Manage "
            "evidence only; it does not discover the global portfolio universe, query "
            "external source-owner event stores, project OMS acknowledgement/fill/"
            "settlement events, or recalculate source truth."
        ),
    )
    if lookup is not None:
        return lookup
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            f"PORTFOLIO_MEMORY_EVENT_NOT_FOUND: {event_id}; "
            f"portfolio_id={portfolio_id}; scanned_event_count={memory.event_count}; "
            "Manage-local lookup does not query external source-owner event stores."
        ),
    )
