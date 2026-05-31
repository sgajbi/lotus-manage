"""Detail timeline route for RFC-0040 portfolio memory."""

from typing import Annotated

from fastapi import Depends, Path, Query

from src.api.routers.portfolio_memory import get_portfolio_memory_source_repositories, router
from src.core.portfolio_memory import DpmPortfolioMemory
from src.core.portfolio_memory.read_request import (
    PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX,
    PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_READ_LIMIT_MIN,
)
from src.core.portfolio_memory.service import build_portfolio_memory_from_sources
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories


@router.get(
    "/{portfolio_id}",
    response_model=DpmPortfolioMemory,
    summary="Get source-backed portfolio memory",
    description=(
        "What: Return a deterministic, source-backed portfolio timeline across manage-owned "
        "mandate health, monitoring exceptions, construction alternative decisions, proof packs, "
        "rebalance waves, internal handoffs, and outcome reviews.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need a "
        "single queryable memory view for a portfolio without reconstructing source truth.\n"
        "How: The endpoint composes persisted RFC-0038, RFC-0039, RFC-0040, RFC-0041, and "
        "RFC-0042 records, including bounded campaign-definition workflow evidence. It preserves "
        "source refs, hashes, states, and reason codes, and "
        "publishes source-event family posture for supported and deferred source owners; it does "
        "not compute risk, performance, execution, tax, cash, mandate-health, PM quality scores, "
        "PM review decisions, external order truth, or client communication truth locally."
    ),
)
def get_portfolio_memory(
    portfolio_id: Annotated[
        str,
        Path(
            description=(
                "Portfolio identifier for the Manage-local source-backed memory timeline."
            ),
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ],
    limit: int = Query(
        default=PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
        ge=PORTFOLIO_MEMORY_READ_LIMIT_MIN,
        le=PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX,
        description="Maximum source-backed memory events to return in the portfolio timeline.",
    ),
    repositories: PortfolioMemorySourceRepositories = Depends(
        get_portfolio_memory_source_repositories
    ),
) -> DpmPortfolioMemory:
    return build_portfolio_memory_from_sources(
        portfolio_id=portfolio_id,
        repositories=repositories,
        limit=limit,
    )
