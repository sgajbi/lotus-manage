from fastapi import Depends, Query

from src.api.dependencies import get_outcome_review_repository
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewListAppliedFilters,
    DpmOutcomeReviewListResponse,
)
from src.api.services.outcome_review_service import search_outcome_reviews
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@shared.wave_lookup_router.get(
    "/{wave_id}/outcome-reviews",
    response_model=DpmOutcomeReviewListResponse,
    summary="List outcome reviews by rebalance wave",
    description=(
        "What: Return persisted outcome reviews associated with a rebalance wave.\n"
        "When: Use after RFC-0041 wave approval, staging, or handoff to inspect post-trade "
        "reviews for affected portfolios.\n"
        "How: Provide the manage-owned wave id plus optional pagination. The endpoint lists "
        "stored review records without deriving wave state locally."
    ),
)
def list_outcome_reviews_by_wave_endpoint(
    wave_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    (
        items,
        total,
        source_owner_counts,
        source_type_counts,
        _,
        _,
    ) = search_outcome_reviews(
        repository=repository,
        wave_id=wave_id,
        limit=limit,
        offset=offset,
    )
    return DpmOutcomeReviewListResponse(
        items=items,
        total=total,
        applied_filters=DpmOutcomeReviewListAppliedFilters(wave_id=wave_id),
        source_owner_counts=source_owner_counts,
        source_type_counts=source_type_counts,
    )
