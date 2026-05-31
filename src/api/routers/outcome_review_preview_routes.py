from fastapi import status

from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_http import outcome_review_validation_http_exception
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewPreviewRequest,
    DpmOutcomeReviewPreviewResponse,
)
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewValidationError,
    preview_outcome_review,
)


@shared.router.post(
    "/preview",
    response_model=DpmOutcomeReviewPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview post-trade outcome comparison",
    description=(
        "What: Compare expected pre-trade manage evidence with realized source-owner evidence "
        "without persisting a review.\n"
        "When: Use before durable creation to inspect variance, degraded source posture, blocked "
        "dimensions, and unsupported dimensions.\n"
        "How: Supply implementation-backed expected and realized snapshots plus explicit tolerance "
        "configuration. The endpoint does not calculate source-owner truth locally."
    ),
)
def preview_outcome_review_endpoint(
    request: DpmOutcomeReviewPreviewRequest,
) -> DpmOutcomeReviewPreviewResponse:
    try:
        comparison = preview_outcome_review(
            expected_snapshot=request.expected_snapshot,
            realized_snapshot=request.realized_snapshot,
            dimension_configs=[config.to_domain() for config in request.dimension_configs],
        )
    except DpmOutcomeReviewValidationError as exc:
        raise outcome_review_validation_http_exception(exc) from exc
    return DpmOutcomeReviewPreviewResponse(comparison=comparison)
