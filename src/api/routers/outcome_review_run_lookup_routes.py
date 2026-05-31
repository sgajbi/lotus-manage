from fastapi import Depends, HTTPException, status

from src.api.dependencies import get_outcome_review_repository
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_models import DpmOutcomeReviewLookupResponse
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@shared.run_lookup_router.get(
    "/{rebalance_run_id}/outcome-review",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get outcome review by rebalance run",
    description=(
        "What: Return the first persisted outcome review for a rebalance run when one exists.\n"
        "When: Use to connect RFC-0039/RFC-0040/RFC-0041 run evidence to the RFC-0042 outcome "
        "review that closed the loop.\n"
        "How: Provide the rebalance run id. The endpoint searches persisted manage outcome-review "
        "truth and returns 404 when no review has been created."
    ),
)
def get_outcome_review_by_run_endpoint(
    rebalance_run_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    items = repository.list_outcome_reviews(rebalance_run_id=rebalance_run_id, limit=1)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        )
    return DpmOutcomeReviewLookupResponse(outcome_review=items[0])
