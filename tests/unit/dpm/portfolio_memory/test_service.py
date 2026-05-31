from datetime import datetime, timezone

import pytest

from src.core.portfolio_memory.service import (
    build_portfolio_memory_from_sources,
    search_portfolio_memory_from_sources,
)
from src.core.portfolio_memory.source_repositories import (
    build_portfolio_memory_source_repositories,
)
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _repositories


def test_search_portfolio_memory_from_sources_uses_repository_bundle() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    page = search_portfolio_memory_from_sources(
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            mandate_repository=mandate_repository,
        ),
        portfolio_ids=[PORTFOLIO_ID],
        event_type="PROOF_PACK_CREATED",
        generated_at=datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc),
    )

    assert page.returned_count == 1
    assert page.scanned_portfolio_count == 1
    assert page.items[0].portfolio_id == PORTFOLIO_ID
    assert page.items[0].latest_matching_event_type == "PROOF_PACK_CREATED"


@pytest.mark.parametrize("limit", [0, 1001])
def test_build_portfolio_memory_from_sources_rejects_unsafe_event_limits(limit: int) -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    with pytest.raises(ValueError, match="portfolio-memory event limit"):
        build_portfolio_memory_from_sources(
            portfolio_id=PORTFOLIO_ID,
            repositories=build_portfolio_memory_source_repositories(
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_repository,
                mandate_repository=mandate_repository,
            ),
            limit=limit,
        )
