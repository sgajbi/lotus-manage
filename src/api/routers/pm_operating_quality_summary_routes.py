from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
    get_pm_quality_summary_invocation_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualitySummaryInvocationListResponse,
    DpmPmQualitySummaryInvocationRequest,
    DpmPmQualitySummaryInvocationResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_summary_invocation_builder import (
    build_summary_invocation_response_model,
)
from src.core.pm_quality import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationRepository,
    PmQualitySummaryInvocationState,
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


@router.get(
    "/summary-invocations",
    response_model=DpmPmQualitySummaryInvocationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality support-summary invocation history",
    description=(
        "What: Return a bounded page of persisted PM operating-quality support-summary "
        "invocation history.\n"
        "When: Use for audit, supportability diagnostics, and review-gated AI workflow evidence "
        "retrieval.\n"
        "How: Filter by score run, review action, policy, as-of date, or invocation state. The "
        "response returns stored workflow and artifact identity only and does not expose generated "
        "summary text, raw review rationale, score values, rankings, client-contact, trade, order, "
        "or OMS execution claims."
    ),
)
def list_pm_quality_summary_invocations_endpoint(
    score_run_id: Annotated[str | None, Query(description="Filter by score-run id.")] = None,
    review_action_id: Annotated[
        str | None,
        Query(description="Filter by review-action id."),
    ] = None,
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    invocation_state: Annotated[
        PmQualitySummaryInvocationState | None,
        Query(description="Filter by bounded summary-invocation state."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
) -> DpmPmQualitySummaryInvocationListResponse:
    invocations = repository.list_summary_invocations(
        score_run_id=score_run_id,
        review_action_id=review_action_id,
        policy_id=policy_id,
        as_of_date=as_of_date,
        invocation_state=invocation_state,
        limit=limit,
        offset=offset,
    )
    return DpmPmQualitySummaryInvocationListResponse(
        summary_invocations=invocations,
        count=len(invocations),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary-invocations/{summary_invocation_id}",
    response_model=DpmPmQualitySummaryInvocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality support-summary invocation history",
    description=(
        "What: Return one persisted PM operating-quality support-summary invocation history row "
        "by stable id.\n"
        "When: Use for audit, supportability diagnostics, and review-gated workflow evidence "
        "retrieval.\n"
        "How: The endpoint returns immutable stored invocation evidence and does not recompute or "
        "mutate the score run, review action, or downstream summary artifact."
    ),
)
def get_pm_quality_summary_invocation_endpoint(
    summary_invocation_id: str,
    repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    invocation = repository.get_summary_invocation(summary_invocation_id=summary_invocation_id)
    if invocation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_SUMMARY_INVOCATION_NOT_FOUND:{summary_invocation_id}",
        )
    return DpmPmQualitySummaryInvocationResponse(summary_invocation=invocation)
