"""API routes for RFC-0040 portfolio memory."""

import importlib
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from src.api.dependencies import (
    get_construction_repository,
    get_campaign_definition_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
    get_pm_quality_summary_invocation_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.portfolio_memory import DpmPortfolioMemory
from src.core.portfolio_memory.read_request import (
    PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX,
    PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_READ_LIMIT_MIN,
)
from src.core.portfolio_memory.service import build_portfolio_memory_from_sources
from src.core.portfolio_memory.source_repositories import (
    PortfolioMemorySourceRepositories,
    build_portfolio_memory_source_repositories,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


router = APIRouter(
    prefix="/rebalance/portfolio-memory",
    tags=["lotus-manage Portfolio Memory"],
)


def get_portfolio_memory_source_repositories(
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> PortfolioMemorySourceRepositories:
    """Resolve portfolio-memory source repositories once per API request."""

    return build_portfolio_memory_source_repositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        pm_quality_review_action_repository=pm_quality_review_action_repository,
        pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
    )


importlib.import_module("src.api.routers.portfolio_memory_search_routes")
importlib.import_module("src.api.routers.portfolio_memory_event_routes")


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
