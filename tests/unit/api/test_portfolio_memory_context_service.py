from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
    build_report_portfolio_memory_context_from_sources,
)
from src.core.portfolio_memory.source_repositories import (
    build_portfolio_memory_source_repositories,
)
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _repositories


def test_build_report_portfolio_memory_context_from_sources_matches_facade() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    repositories = build_portfolio_memory_source_repositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
    )

    from_sources = build_report_portfolio_memory_context_from_sources(
        portfolio_id=PORTFOLIO_ID,
        repositories=repositories,
    )
    from_facade = build_report_portfolio_memory_context(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
    )

    assert from_sources == from_facade
    assert from_sources.portfolio_id == PORTFOLIO_ID
    assert from_sources.event_refs_returned == len(from_sources.event_refs)
