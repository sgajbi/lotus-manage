"""API routes for RFC-0040 portfolio memory."""

from fastapi import APIRouter, Depends

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
from src.api.routers.route_registration import register_route_modules
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
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


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.portfolio_memory_search_routes",
    "src.api.routers.portfolio_memory_event_routes",
    "src.api.routers.portfolio_memory_detail_routes",
)

register_route_modules(_ROUTE_MODULES)
