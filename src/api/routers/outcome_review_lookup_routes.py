from fastapi import Depends

from src.api.dependencies import get_outcome_review_repository
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_http import outcome_review_not_found_http_exception
from src.api.routers.outcome_review_models import DpmOutcomeReviewLookupResponse
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@shared.router.get(
    "/{outcome_review_id}",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get post-trade outcome review",
    description=(
        "What: Retrieve one immutable RFC-0042 outcome review by id.\n"
        "When: Use after create, search, run lookup, or wave lookup to inspect persisted "
        "expected-versus-realized evidence.\n"
        "How: Provide the manage-owned outcome review id. The endpoint returns stored review "
        "truth and does not refresh sources or recalculate source-owner values."
    ),
)
def get_outcome_review_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        raise outcome_review_not_found_http_exception()
    return DpmOutcomeReviewLookupResponse(outcome_review=review)
