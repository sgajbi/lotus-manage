from src.core.portfolio_memory.source_repositories import (
    build_portfolio_memory_source_repositories,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository
from tests.unit.dpm.api.test_portfolio_memory_api import _repositories


def test_build_portfolio_memory_source_repositories_preserves_required_repositories() -> None:
    proof_pack_repository, wave_repository, outcome_repository, _ = _repositories()

    repositories = build_portfolio_memory_source_repositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
    )

    assert repositories.proof_pack_repository is proof_pack_repository
    assert repositories.wave_repository is wave_repository
    assert repositories.outcome_review_repository is outcome_repository
    assert repositories.mandate_repository is None
    assert repositories.construction_repository is None
    assert repositories.pm_quality_score_run_repository is None
    assert repositories.pm_quality_review_action_repository is None
    assert repositories.pm_quality_summary_invocation_repository is None
    assert repositories.campaign_definition_repository is None


def test_build_portfolio_memory_source_repositories_preserves_optional_repositories() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    construction_repository = InMemoryConstructionRepository()
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    summary_invocation_repository = InMemoryDpmPmQualitySummaryInvocationRepository()
    campaign_definition_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()

    repositories = build_portfolio_memory_source_repositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=score_run_repository,
        pm_quality_review_action_repository=review_action_repository,
        pm_quality_summary_invocation_repository=summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
    )

    assert repositories.proof_pack_repository is proof_pack_repository
    assert repositories.wave_repository is wave_repository
    assert repositories.outcome_review_repository is outcome_repository
    assert repositories.mandate_repository is mandate_repository
    assert repositories.construction_repository is construction_repository
    assert repositories.pm_quality_score_run_repository is score_run_repository
    assert repositories.pm_quality_review_action_repository is review_action_repository
    assert repositories.pm_quality_summary_invocation_repository is summary_invocation_repository
    assert repositories.campaign_definition_repository is campaign_definition_repository
