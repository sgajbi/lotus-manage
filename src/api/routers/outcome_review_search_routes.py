from fastapi import Depends, Query

from src.api.dependencies import get_outcome_review_repository
from src.api.routers import outcome_reviews as shared
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewListAppliedFilters,
    DpmOutcomeReviewListResponse,
)
from src.api.services.outcome_review_service import search_outcome_reviews
from src.core.outcomes import OutcomeReviewState
from src.core.outcomes.repository import DpmOutcomeReviewRepository


@shared.router.get(
    "",
    response_model=DpmOutcomeReviewListResponse,
    summary="Search post-trade outcome reviews",
    description=(
        "What: Search persisted RFC-0042 outcome reviews using bounded metadata filters.\n"
        "When: Use for PM, CIO, operations, report, or AI consumers that need outcome-review "
        "memory without recomputing source truth.\n"
        "How: Apply portfolio, mandate, wave, run, state, source-owner, source-type, limit, and "
        "offset filters. The response returns immutable review records and source-lineage facets "
        "from manage persistence without querying source-owner stores."
    ),
)
def list_outcome_reviews_endpoint(
    portfolio_id: str | None = Query(default=None, description="Optional portfolio id filter."),
    mandate_id: str | None = Query(default=None, description="Optional mandate id filter."),
    wave_id: str | None = Query(default=None, description="Optional wave id filter."),
    rebalance_run_id: str | None = Query(
        default=None, description="Optional rebalance run id filter."
    ),
    state: OutcomeReviewState | None = Query(
        default=None,
        description="Optional review state filter.",
        examples=["READY"],
    ),
    source_system: str | None = Query(
        default=None,
        description=(
            "Optional source-owner system filter over persisted outcome-review source lineage. "
            "Leading and trailing whitespace is normalized before matching."
        ),
        examples=["lotus-risk"],
    ),
    source_type: str | None = Query(
        default=None,
        description=(
            "Optional source-type filter over persisted outcome-review source lineage. Leading "
            "and trailing whitespace is normalized before matching."
        ),
        examples=["RiskMetricsReport:v1"],
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    source_scan_limit: int = Query(
        default=500,
        ge=1,
        le=1000,
        description="Maximum persisted outcome-review rows to scan before source-lineage filtering.",
    ),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    (
        items,
        total,
        source_owner_counts,
        source_type_counts,
        normalized_source_system,
        normalized_source_type,
    ) = search_outcome_reviews(
        repository=repository,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        wave_id=wave_id,
        rebalance_run_id=rebalance_run_id,
        state=state,
        limit=limit,
        offset=offset,
        source_system=source_system,
        source_type=source_type,
        source_scan_limit=source_scan_limit,
    )
    return DpmOutcomeReviewListResponse(
        items=items,
        total=total,
        applied_filters=DpmOutcomeReviewListAppliedFilters(
            portfolio_id=portfolio_id,
            mandate_id=mandate_id,
            wave_id=wave_id,
            rebalance_run_id=rebalance_run_id,
            state=state,
            source_system=normalized_source_system,
            source_type=normalized_source_type,
        ),
        source_owner_counts=source_owner_counts,
        source_type_counts=source_type_counts,
    )
