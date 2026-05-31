from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
    get_pm_quality_summary_invocation_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualitySummaryInvocationRequest,
    DpmPmQualitySummaryInvocationResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_summary_invocation_builder import (
    build_summary_invocation_response_model,
)
from src.api.routers.pm_operating_quality_summary_read_routes import (
    router as summary_read_router,
)
from src.core.pm_quality import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationRepository,
)


router = APIRouter()


@router.post(
    "/summary-invocations/preview",
    response_model=DpmPmQualitySummaryInvocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview PM operating quality support-summary invocation history",
    description=(
        "What: Build append-only PM operating-quality support-summary invocation history over a "
        "persisted score run and persisted review action without saving it.\n"
        "When: Use before recording a review-gated support-summary request or downstream workflow "
        "result for audit and supportability.\n"
        "How: Supply the score-run id, review-action id, summary reference, workflow metadata, "
        "artifact refs or hashes when available, and actor. Manage validates the review action "
        "targets the score run and records only bounded invocation evidence. It does not store "
        "AI-generated narrative text, recalculate scores, recompute fairness, rank PMs, create "
        "HR/compensation/conduct decisions, contact clients, approve trades, route orders, or "
        "claim OMS execution."
    ),
)
def preview_pm_quality_summary_invocation_endpoint(
    request: DpmPmQualitySummaryInvocationRequest,
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    invocation = build_summary_invocation_response_model(
        request=request,
        x_correlation_id=x_correlation_id,
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
    )
    return DpmPmQualitySummaryInvocationResponse(summary_invocation=invocation)


@router.post(
    "/summary-invocations",
    response_model=DpmPmQualitySummaryInvocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persisted PM operating quality support-summary invocation history",
    description=(
        "What: Build and persist append-only PM operating-quality support-summary invocation "
        "history over a persisted score run and persisted review action.\n"
        "When: Use when a bank needs durable evidence that a support-only summary was requested "
        "or completed under review-gated governance.\n"
        "How: Supply the same contract as preview. The history row is content-addressed and can "
        "be listed or retrieved for audit. It stores workflow and artifact identity only, not "
        "generated summary text, and it does not mutate score runs or review actions."
    ),
)
def create_pm_quality_summary_invocation_endpoint(
    request: DpmPmQualitySummaryInvocationRequest,
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
    summary_repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    invocation = build_summary_invocation_response_model(
        request=request,
        x_correlation_id=x_correlation_id,
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
    )
    try:
        summary_repository.save_summary_invocation(invocation=invocation)
    except DpmPmQualitySummaryInvocationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DpmPmQualitySummaryInvocationResponse(summary_invocation=invocation)


router.include_router(summary_read_router)
