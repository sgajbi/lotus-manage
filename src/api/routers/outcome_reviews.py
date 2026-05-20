from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewCreateRequest,
    DpmOutcomeReviewCreateResponse,
    DpmOutcomeReviewListResponse,
    DpmOutcomeReviewLookupResponse,
    DpmOutcomeReviewPreviewRequest,
    DpmOutcomeReviewPreviewResponse,
    DpmOutcomeReviewRefreshSourcesRequest,
    DpmOutcomeReviewRefreshSourcesResponse,
    DpmOutcomeReviewSupportabilityResponse,
)
from src.api.observability import record_outcome_review_supportability
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewNotFoundError,
    DpmOutcomeReviewValidationError,
    create_outcome_review,
    get_ai_evidence_input,
    get_report_input,
    preview_outcome_review,
    refresh_outcome_review_sources,
)
from src.core.outcomes import (
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeReportInput,
    DpmPostTradeOutcomeReview,
    OutcomeReviewState,
    build_outcome_client_communication_boundary,
    build_outcome_external_execution_boundary,
)
from src.core.outcomes.repository import DpmOutcomeReviewConflictError, DpmOutcomeReviewRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository

logger = logging.getLogger("lotus-manage.outcome_reviews")
OUTCOME_CREATE_SURFACE = "rebalance/outcome-reviews/create"
OUTCOME_REFRESH_SURFACE = "rebalance/outcome-reviews/refresh-sources"
OUTCOME_SUPPORTABILITY_SURFACE = "rebalance/outcome-reviews/supportability"


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
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
        supportability_state=_metric_state(review.state),
        reason=_metric_reason(review.state),
    )
    return DpmOutcomeReviewCreateResponse(outcome_review=review)


@router.get(
    "",
    response_model=DpmOutcomeReviewListResponse,
    summary="Search post-trade outcome reviews",
    description=(
        "What: Search persisted RFC-0042 outcome reviews using bounded metadata filters.\n"
        "When: Use for PM, CIO, operations, report, or AI consumers that need outcome-review "
        "memory without recomputing source truth.\n"
        "How: Apply portfolio, mandate, wave, run, state, limit, and offset filters. The response "
        "returns immutable review records from manage persistence."
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
        supportability_state=_metric_state(comparison.state),
        reason="outcome_review_source_refreshed",
    )
    return DpmOutcomeReviewRefreshSourcesResponse(event=event, comparison=comparison)


@router.get(
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        )
    response = _supportability_response(review)
    record_outcome_review_supportability(
        surface=OUTCOME_SUPPORTABILITY_SURFACE,
        supportability_state=_metric_state(review.state),
        reason=_metric_reason(review.state),
    )
    logger.info(
        "outcome_review.supportability.inspected",
        extra={
            "extra_fields": {
                "outcome_state": _metric_state(review.state),
                "reason": _metric_reason(review.state),
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


def _metric_state(state: str) -> str:
    return state.lower()


def _metric_reason(state: str) -> str:
    return {
        "READY": "outcome_review_ready",
        "PENDING_REVIEW": "outcome_review_pending_review",
        "BREACHED": "outcome_review_breached",
        "DEGRADED": "outcome_review_degraded",
        "BLOCKED": "outcome_review_blocked",
        "NOT_SUPPORTED": "outcome_review_not_supported",
    }.get(state, "outcome_review_error")


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
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmOutcomeReportInput:
    try:
        return get_report_input(
            outcome_review_id=outcome_review_id,
            repository=repository,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            mandate_repository=mandate_repository,
        )
    except DpmOutcomeReviewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        ) from exc


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        ) from exc


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
    items = repository.list_outcome_reviews(wave_id=wave_id, limit=limit, offset=offset)
    return DpmOutcomeReviewListResponse(items=items, total=len(items))
