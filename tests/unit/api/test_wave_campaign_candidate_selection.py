from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.api.routers.wave_campaign_candidate_selection import (
    select_bulk_review_campaign_candidates,
)
from src.api.services import wave_service


@dataclass(frozen=True)
class Candidate:
    portfolio_id: str
    portfolio_type: str | None
    source_refs: list[object] = field(default_factory=list)


def test_select_bulk_review_campaign_candidates_includes_eligible_candidates() -> None:
    candidate = Candidate(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        portfolio_type=" discretionary ",
        source_refs=[{"source_id": "candidate-source"}],
    )

    selection = select_bulk_review_campaign_candidates(
        candidates=[candidate],
        eligible_portfolio_types={"DISCRETIONARY"},
    )

    assert selection.included_candidates == [candidate]
    assert selection.excluded_count == 0


def test_select_bulk_review_campaign_candidates_counts_ineligible_candidates() -> None:
    eligible = Candidate(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        portfolio_type="DISCRETIONARY",
        source_refs=[{"source_id": "candidate-source"}],
    )
    ineligible = Candidate(
        portfolio_id="PB_SG_ADVISORY_001",
        portfolio_type="ADVISORY",
        source_refs=[{"source_id": "candidate-source"}],
    )

    selection = select_bulk_review_campaign_candidates(
        candidates=[eligible, ineligible],
        eligible_portfolio_types={"DISCRETIONARY"},
    )

    assert selection.included_candidates == [eligible]
    assert selection.excluded_count == 1


def test_select_bulk_review_campaign_candidates_requires_portfolio_type() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        select_bulk_review_campaign_candidates(
            candidates=[
                Candidate(
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                    portfolio_type=" ",
                    source_refs=[{"source_id": "candidate-source"}],
                )
            ],
            eligible_portfolio_types={"DISCRETIONARY"},
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED"
    assert (
        exc_info.value.message
        == "BULK_REVIEW_CAMPAIGN candidate portfolios require source-owned portfolio_type."
    )


def test_select_bulk_review_campaign_candidates_requires_source_refs() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        select_bulk_review_campaign_candidates(
            candidates=[
                Candidate(
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                    portfolio_type="DISCRETIONARY",
                    source_refs=[],
                )
            ],
            eligible_portfolio_types={"DISCRETIONARY"},
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED"
    assert (
        exc_info.value.message == "BULK_REVIEW_CAMPAIGN candidate portfolios require source_refs."
    )
