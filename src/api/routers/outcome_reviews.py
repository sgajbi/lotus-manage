from __future__ import annotations

import importlib

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_outcome_review_repository
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewListAppliedFilters,
    DpmOutcomeReviewListResponse,
    DpmOutcomeReviewLookupResponse,
)
from src.api.services.outcome_review_service import search_outcome_reviews
from src.core.outcomes import OutcomeReviewState
from src.core.outcomes.repository import DpmOutcomeReviewRepository

router = APIRouter(
    prefix="/rebalance/outcome-reviews",
    tags=["lotus-manage Outcome Reviews"],
)


importlib.import_module("src.api.routers.outcome_review_preview_routes")
importlib.import_module("src.api.routers.outcome_review_create_routes")


@router.get(
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


@router.get(
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        )
    return DpmOutcomeReviewLookupResponse(outcome_review=review)


importlib.import_module("src.api.routers.outcome_review_refresh_routes")
importlib.import_module("src.api.routers.outcome_review_supportability_routes")
importlib.import_module("src.api.routers.outcome_review_handoff_routes")


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


@run_lookup_router.get(
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


@wave_lookup_router.get(
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
