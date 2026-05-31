import pytest

from src.core.portfolio_memory.source_collection import collect_portfolio_memory_events
from src.core.portfolio_memory.source_repositories import (
    PortfolioMemorySourceRepositories,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _campaign_definition,
    _construction_repository,
    _pm_quality_score_run,
    _repositories,
)


def test_collect_portfolio_memory_events_collects_required_source_families() -> None:
    proof_pack_repository, wave_repository, outcome_repository, _mandate_repository = (
        _repositories()
    )

    events = collect_portfolio_memory_events(
        portfolio_id=PORTFOLIO_ID,
        repositories=PortfolioMemorySourceRepositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
        ),
        limit=100,
    )

    event_types = {event.event_type for event in events}
    assert "PROOF_PACK_CREATED" in event_types
    assert "WAVE_CREATED" in event_types
    assert "OUTCOME_REVIEW_CREATED" in event_types
    assert "MANDATE_HEALTH_SNAPSHOT" not in event_types


def test_collect_portfolio_memory_events_includes_optional_source_families() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())

    events = collect_portfolio_memory_events(
        portfolio_id=PORTFOLIO_ID,
        repositories=PortfolioMemorySourceRepositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            mandate_repository=mandate_repository,
            construction_repository=_construction_repository(),
            campaign_definition_repository=campaign_repository,
            pm_quality_score_run_repository=pm_quality_repository,
        ),
        limit=100,
    )

    event_types = {event.event_type for event in events}
    assert "MANDATE_HEALTH_SNAPSHOT" in event_types
    assert "CONSTRUCTION_ALTERNATIVE_SET" in event_types
    assert "BULK_REVIEW_CAMPAIGN_DEFINITION" in event_types
    assert "PM_QUALITY_SCORE_RUN" in event_types


def test_collect_portfolio_memory_events_skips_optional_empty_repositories() -> None:
    proof_pack_repository, wave_repository, outcome_repository, _mandate_repository = (
        _repositories()
    )

    events = collect_portfolio_memory_events(
        portfolio_id=PORTFOLIO_ID,
        repositories=PortfolioMemorySourceRepositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            construction_repository=InMemoryConstructionRepository(),
        ),
        limit=100,
    )

    assert "CONSTRUCTION_ALTERNATIVE_SET" not in {event.event_type for event in events}


@pytest.mark.parametrize("limit", [0, 1001])
def test_collect_portfolio_memory_events_rejects_unsafe_source_scan_limits(
    limit: int,
) -> None:
    proof_pack_repository, wave_repository, outcome_repository, _mandate_repository = (
        _repositories()
    )

    with pytest.raises(ValueError, match="portfolio-memory event limit"):
        collect_portfolio_memory_events(
            portfolio_id=PORTFOLIO_ID,
            repositories=PortfolioMemorySourceRepositories(
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_repository,
            ),
            limit=limit,
        )
