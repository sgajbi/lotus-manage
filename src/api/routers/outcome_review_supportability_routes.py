import logging

from fastapi import Depends

from src.api.dependencies import get_outcome_review_repository
from src.api.observability import record_outcome_review_supportability
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_http import outcome_review_not_found_http_exception
from src.api.routers.outcome_review_models import DpmOutcomeReviewSupportabilityResponse
from src.api.routers.outcome_review_observability import (
    OUTCOME_SUPPORTABILITY_SURFACE,
    outcome_review_metric_reason,
    outcome_review_metric_state,
)
from src.core.outcomes import (
    DpmPostTradeOutcomeReview,
    build_outcome_client_communication_boundary,
    build_outcome_external_execution_boundary,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository

logger = logging.getLogger("lotus-manage.outcome_reviews")


@shared.router.get(
    "/{outcome_review_id}/supportability",
    response_model=DpmOutcomeReviewSupportabilityResponse,
    summary="Get outcome-review supportability",
    description=(
        "What: Return operator-safe RFC-0042 state, source posture, source-owner families, "
        "dimension counts, freshness counts, and reason codes.\n"
        "When: Use when PMs, operations, support, Gateway, or Workbench need to distinguish source "
        "gaps from manage defects.\n"
        "How: Provide the outcome review id. The response emits bounded diagnostics and "
        "remediation routes without raw source payloads or sensitive identifiers."
    ),
)
def get_outcome_review_supportability_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewSupportabilityResponse:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        record_outcome_review_supportability(
            surface=OUTCOME_SUPPORTABILITY_SURFACE,
            supportability_state="not_found",
            reason="outcome_review_not_found",
        )
        raise outcome_review_not_found_http_exception()
    response = _supportability_response(review)
    record_outcome_review_supportability(
        surface=OUTCOME_SUPPORTABILITY_SURFACE,
        supportability_state=outcome_review_metric_state(review.state),
        reason=outcome_review_metric_reason(review.state),
    )
    logger.info(
        "outcome_review.supportability.inspected",
        extra={
            "extra_fields": {
                "outcome_state": outcome_review_metric_state(review.state),
                "reason": outcome_review_metric_reason(review.state),
                "dimension_count": len(review.dimension_results),
                "blocked_dimension_count": response.blocked_dimension_count,
                "degraded_dimension_count": response.degraded_dimension_count,
                "unsupported_dimension_count": response.unsupported_dimension_count,
                "source_ref_count": response.source_ref_count,
            }
        },
    )
    return response


def _supportability_response(
    review: DpmPostTradeOutcomeReview,
) -> DpmOutcomeReviewSupportabilityResponse:
    dimension_state_counts: dict[str, int] = {}
    freshness_state_counts: dict[str, int] = {}
    for result in review.dimension_results:
        dimension_state_counts[result.state] = dimension_state_counts.get(result.state, 0) + 1
        for freshness in result.source_freshness:
            freshness_state_counts[freshness.freshness_state] = (
                freshness_state_counts.get(freshness.freshness_state, 0) + 1
            )
    return DpmOutcomeReviewSupportabilityResponse(
        outcome_review_id=review.outcome_review_id,
        supportability=review.supportability,
        state=review.state,
        reason_codes=review.supportability.reason_codes,
        source_ref_count=len(review.source_lineage),
        source_owners=sorted({ref.source_system for ref in review.source_lineage}),
        dimension_state_counts=dimension_state_counts,
        blocked_dimension_count=dimension_state_counts.get("BLOCKED", 0),
        degraded_dimension_count=dimension_state_counts.get("DEGRADED", 0),
        unsupported_dimension_count=dimension_state_counts.get("NOT_SUPPORTED", 0),
        freshness_state_counts=freshness_state_counts,
        remediation_routes=_remediation_routes(review),
        external_execution_boundary=build_outcome_external_execution_boundary(review),
        client_communication_boundary=build_outcome_client_communication_boundary(review),
    )


def _remediation_routes(review: DpmPostTradeOutcomeReview) -> list[str]:
    routes: set[str] = set()
    for reason in review.supportability.reason_codes:
        if "RISK" in reason:
            routes.add("lotus-risk:refresh-post-trade-risk-source")
        elif "PERFORMANCE" in reason:
            routes.add("lotus-performance:refresh-post-trade-performance-source")
        elif "EXECUTION" in reason:
            routes.add("execution-owner:certify-fill-and-order-evidence")
        elif "SOURCE" in reason or "CASH" in reason or "FX" in reason or "TAX" in reason:
            routes.add("source-owner:refresh-realized-outcome-source")
    return sorted(routes)
