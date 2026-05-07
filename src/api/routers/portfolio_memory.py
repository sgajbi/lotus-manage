"""API routes for RFC-0040 portfolio memory."""

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import (
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory import DpmPortfolioMemory
from src.core.portfolio_memory.service import build_portfolio_memory
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository


router = APIRouter(
    prefix="/rebalance/portfolio-memory",
    tags=["lotus-manage Portfolio Memory"],
)


@router.get(
    "/{portfolio_id}",
    response_model=DpmPortfolioMemory,
    summary="Get source-backed portfolio memory",
    description=(
        "What: Return a deterministic, source-backed portfolio timeline across manage-owned "
        "proof packs, rebalance waves, internal handoffs, and outcome reviews.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need a "
        "single queryable memory view for a portfolio without reconstructing source truth.\n"
        "How: The endpoint composes persisted RFC-0040, RFC-0041, and RFC-0042 records. It "
        "preserves source refs, hashes, states, and reason codes; it does not compute risk, "
        "performance, execution, tax, cash, or external order truth locally."
    ),
)
def get_portfolio_memory(
    portfolio_id: str,
    limit: int = Query(default=100, ge=1, le=500, description="Maximum events to return."),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmPortfolioMemory:
    return build_portfolio_memory(
        portfolio_id=portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        limit=limit,
    )
