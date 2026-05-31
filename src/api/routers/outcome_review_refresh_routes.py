from fastapi import Depends, HTTPException, status

from src.api.dependencies import get_outcome_review_repository
from src.api.observability import record_outcome_review_supportability
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewRefreshSourcesRequest,
    DpmOutcomeReviewRefreshSourcesResponse,
)
from src.api.routers.outcome_review_observability import (
    OUTCOME_REFRESH_SURFACE,
    outcome_review_metric_state,
)
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewNotFoundError,
    DpmOutcomeReviewValidationError,
    refresh_outcome_review_sources,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@shared.router.post(
    "/{outcome_review_id}/refresh-sources",
    response_model=DpmOutcomeReviewRefreshSourcesResponse,
    summary="Refresh outcome-review source evidence",
    description=(
        "What: Re-evaluate a persisted review using the immutable expected snapshot and newly supplied "
        "source-owner realized evidence.\n"
        "When: Use after execution, risk, performance, cost, tax, FX, or cash source owners refresh "
        "post-trade evidence.\n"
        "How: Supply the refreshed realized snapshot and explicit dimension policy. The endpoint appends "
        "a source-refresh event with refreshed state and source refs; it does not mutate the immutable "
        "review body."
    ),
)
def refresh_outcome_review_sources_endpoint(
    outcome_review_id: str,
    request: DpmOutcomeReviewRefreshSourcesRequest,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewRefreshSourcesResponse:
    try:
        event, comparison = refresh_outcome_review_sources(
            outcome_review_id=outcome_review_id,
            realized_snapshot=request.realized_snapshot,
            dimension_configs=[config.to_domain() for config in request.dimension_configs],
            actor_id=request.actor_id,
            repository=repository,
        )
    except DpmOutcomeReviewNotFoundError as exc:
        record_outcome_review_supportability(
            surface=OUTCOME_REFRESH_SURFACE,
            supportability_state="not_found",
            reason="outcome_review_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        ) from exc
    except DpmOutcomeReviewValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    record_outcome_review_supportability(
        surface=OUTCOME_REFRESH_SURFACE,
        supportability_state=outcome_review_metric_state(comparison.state),
        reason="outcome_review_source_refreshed",
    )
    return DpmOutcomeReviewRefreshSourcesResponse(event=event, comparison=comparison)
