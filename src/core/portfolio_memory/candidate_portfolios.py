"""Candidate portfolio discovery for portfolio-memory search."""

from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import DpmPmQualityScoreRunRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.portfolio_memory.source_repositories import (
    PortfolioMemorySourceRepositories,
    build_portfolio_memory_source_repositories,
)
from src.core.portfolio_memory.search_request import validate_portfolio_memory_source_scan_limit
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


def candidate_portfolio_ids(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    portfolio_ids: list[str] | None,
    source_scan_limit: int,
    mandate_repository: DpmMandateRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
) -> list[str]:
    return candidate_portfolio_ids_from_sources(
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            campaign_definition_repository=campaign_definition_repository,
            pm_quality_score_run_repository=pm_quality_score_run_repository,
        ),
        portfolio_ids=portfolio_ids,
        source_scan_limit=source_scan_limit,
    )


def candidate_portfolio_ids_from_sources(
    *,
    repositories: PortfolioMemorySourceRepositories,
    portfolio_ids: list[str] | None,
    source_scan_limit: int,
) -> list[str]:
    source_scan_limit = validate_portfolio_memory_source_scan_limit(
        source_scan_limit=source_scan_limit
    )
    candidates = _explicit_candidate_ids(portfolio_ids)
    candidates.update(_proof_pack_candidate_ids(repositories, source_scan_limit))
    candidates.update(_wave_candidate_ids(repositories, source_scan_limit))
    candidates.update(_outcome_review_candidate_ids(repositories, source_scan_limit))
    candidates.update(_mandate_exception_candidate_ids(repositories, source_scan_limit))
    candidates.update(_campaign_definition_candidate_ids(repositories, source_scan_limit))
    candidates.update(_pm_quality_candidate_ids(repositories, source_scan_limit))
    return sorted(candidates)


def _explicit_candidate_ids(portfolio_ids: list[str] | None) -> set[str]:
    return {portfolio_id.strip() for portfolio_id in (portfolio_ids or []) if portfolio_id.strip()}


def _proof_pack_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    return {
        proof_pack.portfolio_id
        for proof_pack in repositories.proof_pack_repository.list_proof_packs(
            limit=source_scan_limit
        )
    }


def _wave_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    return {
        item.portfolio_id
        for wave in repositories.wave_repository.list_waves(limit=source_scan_limit)
        for item in wave.items
    }


def _outcome_review_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    return {
        review.portfolio_id
        for review in repositories.outcome_review_repository.list_outcome_reviews(
            limit=source_scan_limit
        )
    }


def _mandate_exception_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    if repositories.mandate_repository is None:
        return set()
    exceptions, _cursor = repositories.mandate_repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=None,
        portfolio_id=None,
        state=None,
        limit=source_scan_limit,
        cursor=None,
    )
    return {exception.portfolio_id for exception in exceptions}


def _campaign_definition_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    if repositories.campaign_definition_repository is None:
        return set()
    return {
        candidate.portfolio_id
        for definition in repositories.campaign_definition_repository.list_definitions(
            limit=source_scan_limit
        )
        for candidate in definition.candidates
    }


def _pm_quality_candidate_ids(
    repositories: PortfolioMemorySourceRepositories,
    source_scan_limit: int,
) -> set[str]:
    if repositories.pm_quality_score_run_repository is None:
        return set()
    return {
        portfolio_id
        for score_run in repositories.pm_quality_score_run_repository.list_score_runs(
            limit=source_scan_limit
        )
        if score_run.book_scope_evidence is not None
        for portfolio_id in score_run.book_scope_evidence.member_portfolio_ids
    }
