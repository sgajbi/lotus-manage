import pytest

from src.core.portfolio_memory.candidate_portfolios import (
    _campaign_definition_candidate_ids,
    _explicit_candidate_ids,
    _mandate_exception_candidate_ids,
    _pm_quality_candidate_ids,
    candidate_portfolio_ids,
    candidate_portfolio_ids_from_sources,
)
from src.core.portfolio_memory.search_request import (
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN,
)
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _campaign_definition,
    _pm_quality_score_run,
    _repositories,
)


def test_candidate_portfolio_ids_merge_explicit_and_source_backed_portfolios() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())

    candidates = candidate_portfolio_ids_from_sources(
        repositories=PortfolioMemorySourceRepositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            mandate_repository=mandate_repository,
            campaign_definition_repository=campaign_repository,
            pm_quality_score_run_repository=pm_quality_repository,
        ),
        portfolio_ids=[" PB_MANUAL_001 ", "", PORTFOLIO_ID],
        source_scan_limit=100,
    )

    assert candidates == sorted({PORTFOLIO_ID, "PB_MANUAL_001", "PB_SG_GLOBAL_INC_002"})


def test_candidate_portfolio_ids_support_optional_repositories() -> None:
    proof_pack_repository, wave_repository, outcome_repository, _mandate_repository = (
        _repositories()
    )

    candidates = candidate_portfolio_ids(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=None,
        campaign_definition_repository=None,
        pm_quality_score_run_repository=None,
        portfolio_ids=None,
        source_scan_limit=100,
    )

    assert candidates == [PORTFOLIO_ID]


def test_candidate_portfolio_ids_default_optional_repositories_to_empty_sources() -> None:
    proof_pack_repository, wave_repository, outcome_repository, _mandate_repository = (
        _repositories()
    )

    candidates = candidate_portfolio_ids(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        portfolio_ids=None,
        source_scan_limit=100,
    )

    assert candidates == [PORTFOLIO_ID]


def test_candidate_portfolio_source_helpers_preserve_family_boundaries() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())
    repositories = PortfolioMemorySourceRepositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        campaign_definition_repository=campaign_repository,
        pm_quality_score_run_repository=pm_quality_repository,
    )

    assert _explicit_candidate_ids([" PB_MANUAL_001 ", "", "PB_MANUAL_002"]) == {
        "PB_MANUAL_001",
        "PB_MANUAL_002",
    }
    assert _mandate_exception_candidate_ids(repositories, 100) == {PORTFOLIO_ID}
    assert _campaign_definition_candidate_ids(repositories, 100) == {PORTFOLIO_ID}
    assert _pm_quality_candidate_ids(repositories, 100) == {
        PORTFOLIO_ID,
        "PB_SG_GLOBAL_INC_002",
    }


@pytest.mark.parametrize(
    "source_scan_limit",
    [
        PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN - 1,
        PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX + 1,
    ],
)
def test_candidate_portfolio_ids_reject_unsafe_source_scan_limits(
    source_scan_limit: int,
) -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    with pytest.raises(ValueError, match="source_scan_limit must be between 1 and 1000"):
        candidate_portfolio_ids_from_sources(
            repositories=PortfolioMemorySourceRepositories(
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_repository,
                mandate_repository=mandate_repository,
            ),
            portfolio_ids=None,
            source_scan_limit=source_scan_limit,
        )
