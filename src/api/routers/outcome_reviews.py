from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_outcome_review_repository
from src.api.services.outcome_review_service import (
    DpmOutcomeDimensionConfig,
    DpmOutcomeReviewNotFoundError,
    DpmOutcomeReviewValidationError,
    create_outcome_review,
    get_ai_evidence_input,
    get_report_input,
    preview_outcome_review,
    refresh_outcome_review_sources,
)
from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeEvent,
    DpmOutcomeReviewComparison,
    DpmOutcomeReportInput,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    OutcomeComparisonDirection,
    OutcomeDimension,
)
from src.core.outcomes.repository import DpmOutcomeReviewConflictError, DpmOutcomeReviewRepository


class DpmOutcomeDimensionConfigRequest(BaseModel):
    dimension: OutcomeDimension = Field(
        description="Outcome dimension to compare.",
        examples=["DRIFT_REDUCTION"],
    )
    tolerance: DpmOutcomeTolerance = Field(description="Soft and hard tolerance for the dimension.")
    materiality: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Materiality threshold used in comparison output.",
        examples=["0.0050"],
    )
    direction: OutcomeComparisonDirection = Field(
        description="Comparison direction for the dimension.",
        examples=["LOWER_IS_BETTER"],
    )

    def to_domain(self) -> DpmOutcomeDimensionConfig:
        return DpmOutcomeDimensionConfig(
            dimension=self.dimension,
            tolerance=self.tolerance,
            materiality=self.materiality,
            direction=self.direction,
        )


class DpmOutcomeReviewPreviewRequest(BaseModel):
    expected_snapshot: DpmExpectedOutcomeSnapshot = Field(
        description="Expected snapshot assembled from pre-trade manage evidence.",
    )
    realized_snapshot: DpmRealizedOutcomeSnapshot = Field(
        description="Realized snapshot assembled from source-owner evidence.",
    )
    dimension_configs: list[DpmOutcomeDimensionConfigRequest] = Field(
        min_length=1,
        description="Dimensions to compare and their tolerance policy.",
    )


class DpmOutcomeReviewPreviewResponse(BaseModel):
    comparison: DpmOutcomeReviewComparison = Field(description="Deterministic comparison result.")


class DpmOutcomeReviewCreateRequest(DpmOutcomeReviewPreviewRequest):
    actor_id: str = Field(description="Actor creating the outcome review.", examples=["pm_001"])


class DpmOutcomeReviewCreateResponse(BaseModel):
    outcome_review: DpmPostTradeOutcomeReview = Field(description="Persisted immutable review.")


class DpmOutcomeReviewLookupResponse(BaseModel):
    outcome_review: DpmPostTradeOutcomeReview = Field(description="Persisted immutable review.")


class DpmOutcomeReviewListResponse(BaseModel):
    items: list[DpmPostTradeOutcomeReview] = Field(description="Bounded review search results.")
    total: int = Field(description="Returned item count.", examples=[1])


class DpmOutcomeReviewSupportabilityResponse(BaseModel):
    outcome_review_id: str = Field(description="Outcome review identifier.", examples=["dor_001"])
    supportability: DpmOutcomeSupportability = Field(description="Operator-safe supportability.")
    state: str = Field(description="Outcome review state.", examples=["DEGRADED"])
    reason_codes: list[str] = Field(description="Bounded supportability reason codes.")


class DpmOutcomeReviewRefreshSourcesRequest(BaseModel):
    actor_id: str = Field(description="Actor requesting source refresh.", examples=["pm_001"])
    realized_snapshot: DpmRealizedOutcomeSnapshot = Field(
        description="New realized source-owner snapshot to compare against the immutable expected snapshot.",
    )
    dimension_configs: list[DpmOutcomeDimensionConfigRequest] = Field(
        min_length=1,
        description="Dimensions to re-evaluate and their tolerance policy.",
    )


class DpmOutcomeReviewRefreshSourcesResponse(BaseModel):
    event: DpmOutcomeEvent = Field(description="Appended source-refresh event.")
    comparison: DpmOutcomeReviewComparison = Field(
        description="Fresh expected-versus-realized comparison produced from the supplied source snapshot.",
    )


router = APIRouter(
    prefix="/rebalance/outcome-reviews",
    tags=["lotus-manage Outcome Reviews"],
)


@router.post(
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return DpmOutcomeReviewPreviewResponse(comparison=comparison)


@router.post(
    "",
    response_model=DpmOutcomeReviewCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create immutable post-trade outcome review",
    description=(
        "What: Persist an immutable RFC-0042 outcome review with source lineage, hashes, "
        "dimension states, supportability, and append-only creation event.\n"
        "When: Use after preview once source-owner evidence has been reviewed.\n"
        "How: Provide `Idempotency-Key`; replay returns the original review for the same key."
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except DpmOutcomeReviewConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DpmOutcomeReviewCreateResponse(outcome_review=review)


@router.get(
    "",
    response_model=DpmOutcomeReviewListResponse,
    summary="Search post-trade outcome reviews",
    description="Search persisted RFC-0042 outcome reviews using bounded metadata filters.",
)
def list_outcome_reviews_endpoint(
    portfolio_id: str | None = Query(default=None, description="Optional portfolio id filter."),
    mandate_id: str | None = Query(default=None, description="Optional mandate id filter."),
    wave_id: str | None = Query(default=None, description="Optional wave id filter."),
    rebalance_run_id: str | None = Query(default=None, description="Optional rebalance run id filter."),
    state: str | None = Query(default=None, description="Optional review state filter."),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    items = repository.list_outcome_reviews(
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        wave_id=wave_id,
        rebalance_run_id=rebalance_run_id,
        state=state,
        limit=limit,
        offset=offset,
    )
    return DpmOutcomeReviewListResponse(items=items, total=len(items))


@router.get(
    "/{outcome_review_id}",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get post-trade outcome review",
    description="Retrieve one immutable RFC-0042 outcome review by id.",
)
def get_outcome_review_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND")
    return DpmOutcomeReviewLookupResponse(outcome_review=review)


@router.post(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND") from exc
    except DpmOutcomeReviewValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return DpmOutcomeReviewRefreshSourcesResponse(event=event, comparison=comparison)


@router.get(
    "/{outcome_review_id}/supportability",
    response_model=DpmOutcomeReviewSupportabilityResponse,
    summary="Get outcome-review supportability",
    description="Return operator-safe RFC-0042 state, source posture, and reason codes.",
)
def get_outcome_review_supportability_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewSupportabilityResponse:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND")
    return DpmOutcomeReviewSupportabilityResponse(
        outcome_review_id=outcome_review_id,
        supportability=review.supportability,
        state=review.state,
        reason_codes=review.supportability.reason_codes,
    )


@router.get(
    "/{outcome_review_id}/report-input",
    response_model=DpmOutcomeReportInput,
    summary="Get outcome-review report input",
    description=(
        "What: Return deterministic report-ready facts for a persisted RFC-0042 outcome review.\n"
        "When: Use when `lotus-report`, `lotus-render`, or `lotus-archive` needs bounded outcome "
        "evidence without recomputing review truth.\n"
        "How: The response is derived from the immutable review, source hashes, dimension results, "
        "and supportability. `lotus-manage` does not generate rendered reports or archive records."
    ),
)
def get_outcome_review_report_input_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReportInput:
    try:
        return get_report_input(outcome_review_id=outcome_review_id, repository=repository)
    except DpmOutcomeReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND") from exc


@router.get(
    "/{outcome_review_id}/ai-evidence-input",
    response_model=DpmOutcomeAiEvidenceInput,
    summary="Get outcome-review AI evidence input",
    description=(
        "What: Return bounded AI evidence for RFC-0043 and `lotus-ai` workflows.\n"
        "When: Use when AI assistance needs provenance-rich outcome facts without raw source "
        "payloads, investment authority, or client-contact authority.\n"
        "How: The response includes permitted use, forbidden actions, source refs, dimension facts, "
        "and a canonical content hash. `lotus-manage` does not generate AI prompts, PM memos, "
        "recommendations, approvals, or execution instructions."
    ),
)
def get_outcome_review_ai_evidence_input_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeAiEvidenceInput:
    try:
        return get_ai_evidence_input(outcome_review_id=outcome_review_id, repository=repository)
    except DpmOutcomeReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND") from exc


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


@run_lookup_router.get(
    "/{rebalance_run_id}/outcome-review",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get outcome review by rebalance run",
    description="Return the first persisted outcome review for a rebalance run when one exists.",
)
def get_outcome_review_by_run_endpoint(
    rebalance_run_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    items = repository.list_outcome_reviews(rebalance_run_id=rebalance_run_id, limit=1)
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND")
    return DpmOutcomeReviewLookupResponse(outcome_review=items[0])


@wave_lookup_router.get(
    "/{wave_id}/outcome-reviews",
    response_model=DpmOutcomeReviewListResponse,
    summary="List outcome reviews by rebalance wave",
    description="Return persisted outcome reviews associated with a rebalance wave.",
)
def list_outcome_reviews_by_wave_endpoint(
    wave_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    items = repository.list_outcome_reviews(wave_id=wave_id, limit=limit, offset=offset)
    return DpmOutcomeReviewListResponse(items=items, total=len(items))
