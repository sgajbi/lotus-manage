from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.api.dependencies import get_outcome_review_repository
from src.api.observability import record_outcome_review_supportability
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewCreateRequest,
    DpmOutcomeReviewCreateResponse,
)
from src.api.routers.outcome_review_observability import (
    OUTCOME_CREATE_SURFACE,
    outcome_review_metric_reason,
    outcome_review_metric_state,
)
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewValidationError,
    create_outcome_review,
)
from src.core.outcomes.repository import DpmOutcomeReviewConflictError, DpmOutcomeReviewRepository


@shared.router.post(
    "",
    response_model=DpmOutcomeReviewCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create immutable post-trade outcome review",
    description=(
        "What: Persist an immutable RFC-0042 outcome review with source lineage, hashes, "
        "dimension states, supportability, and append-only creation event.\n"
        "When: Use after preview once source-owner evidence has been reviewed.\n"
        "How: Provide `Idempotency-Key`; same-key same-evidence replay returns the original review, "
        "while same-key changed evidence is rejected as an idempotency conflict."
    ),
)
def create_outcome_review_endpoint(
    request: DpmOutcomeReviewCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for durable outcome-review creation.",
            examples=["outcome-review-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        str | None,
        Header(description="Optional correlation id.", examples=["corr-outcome-001"]),
    ] = None,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewCreateResponse:
    try:
        review = create_outcome_review(
            expected_snapshot=request.expected_snapshot,
            realized_snapshot=request.realized_snapshot,
            dimension_configs=[config.to_domain() for config in request.dimension_configs],
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or idempotency_key,
            idempotency_key=idempotency_key,
            repository=repository,
        )
    except DpmOutcomeReviewValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except DpmOutcomeReviewConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    record_outcome_review_supportability(
        surface=OUTCOME_CREATE_SURFACE,
        supportability_state=outcome_review_metric_state(review.state),
        reason=outcome_review_metric_reason(review.state),
    )
    return DpmOutcomeReviewCreateResponse(outcome_review=review)
