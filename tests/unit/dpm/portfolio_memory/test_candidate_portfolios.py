from src.core.portfolio_memory.candidate_portfolios import candidate_portfolio_ids
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

    candidates = candidate_portfolio_ids(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        campaign_definition_repository=campaign_repository,
        pm_quality_score_run_repository=pm_quality_repository,
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
