from __future__ import annotations

from dataclasses import dataclass

from src.core.outcomes import DpmPostTradeOutcomeReview
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@dataclass(frozen=True)
class OutcomeReviewSearchPage:
    items: list[DpmPostTradeOutcomeReview]
    total: int
    source_owner_counts: dict[str, int]
    source_type_counts: dict[str, int]
    normalized_source_system: str | None
    normalized_source_type: str | None


def search_outcome_review_page(
    *,
    repository: DpmOutcomeReviewRepository,
    portfolio_id: str | None = None,
    mandate_id: str | None = None,
    wave_id: str | None = None,
    rebalance_run_id: str | None = None,
    state: str | None = None,
    source_system: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    source_scan_limit: int = 500,
) -> OutcomeReviewSearchPage:
    normalized_source_system = normalize_outcome_review_search_filter(source_system)
    normalized_source_type = normalize_outcome_review_search_filter(source_type)
    candidate_reviews = repository.list_outcome_reviews(
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        wave_id=wave_id,
        rebalance_run_id=rebalance_run_id,
        state=state,
        limit=source_scan_limit,
        offset=0,
    )
    matching_reviews = [
        review
        for review in candidate_reviews
        if review_matches_source_lineage_filters(
            review=review,
            source_system=normalized_source_system,
            source_type=normalized_source_type,
        )
    ]
    source_owner_counts: dict[str, int] = {}
    source_type_counts: dict[str, int] = {}
    for review in matching_reviews:
        for represented_source_system in review_source_systems(review):
            source_owner_counts[represented_source_system] = (
                source_owner_counts.get(represented_source_system, 0) + 1
            )
        for represented_source_type in review_source_types(review):
            source_type_counts[represented_source_type] = (
                source_type_counts.get(represented_source_type, 0) + 1
            )
    return OutcomeReviewSearchPage(
        items=matching_reviews[offset : offset + limit],
        total=len(matching_reviews),
        source_owner_counts=dict(sorted(source_owner_counts.items())),
        source_type_counts=dict(sorted(source_type_counts.items())),
        normalized_source_system=normalized_source_system,
        normalized_source_type=normalized_source_type,
    )


def normalize_outcome_review_search_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def review_matches_source_lineage_filters(
    *,
    review: DpmPostTradeOutcomeReview,
    source_system: str | None,
    source_type: str | None,
) -> bool:
    if source_system is not None and source_system not in review_source_systems(review):
        return False
    if source_type is not None and source_type not in review_source_types(review):
        return False
    return True


def review_source_systems(review: DpmPostTradeOutcomeReview) -> set[str]:
    return {ref.source_system for ref in review.source_lineage if ref.source_system}


def review_source_types(review: DpmPostTradeOutcomeReview) -> set[str]:
    return {ref.source_type for ref in review.source_lineage if ref.source_type}
