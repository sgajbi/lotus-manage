from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_pm_quality_fairness_analysis_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityFairnessAnalysisListResponse,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityFairnessPreviewResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityServiceError,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    build_pm_quality_fairness_analysis_from_command,
)
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityScoreRunRepository,
)


router = APIRouter()


@router.post(
    "/fairness-analyses/preview",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview PM operating quality cross-segment fairness analysis",
    description=(
        "What: Build a bounded cross-segment fairness analysis from persisted PM operating "
        "quality score runs and source-defined segment assignments.\n"
        "When: Use for bank model-risk, fairness, supervisory-control, or governance review "
        "after score runs have been created under one approved policy.\n"
        "How: Supply two or more source-defined segments with persisted score-run ids and segment "
        "source refs. Manage validates the score runs share policy and as-of date, requires a "
        "minimum scorable count per segment, compares segment average scores against a governed "
        "spread threshold, and returns review-required posture when the spread exceeds policy. "
        "This endpoint does not infer protected classes, rank PMs, administer compensation or HR "
        "decisions, perform conduct enforcement, or calculate source-owned risk/performance facts."
    ),
)
def preview_pm_quality_fairness_analysis_endpoint(
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = _build_fairness_analysis(
        request=request,
        x_correlation_id=x_correlation_id,
        repository=repository,
    )
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


@router.post(
    "/fairness-analyses",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persisted PM operating quality fairness analysis",
    description=(
        "What: Build and persist an immutable PM operating quality cross-segment fairness "
        "analysis from persisted score runs and source-defined segment assignments.\n"
        "When: Use after a bank needs auditable fairness governance evidence for PM operating "
        "quality score runs created under one approved policy.\n"
        "How: Supply the same source-segment contract as preview. The persisted analysis is "
        "content-addressed and can be listed or retrieved for governance review. This endpoint "
        "does not infer protected classes, rank PMs, administer compensation or HR decisions, "
        "perform conduct enforcement, or calculate source-owned risk/performance facts."
    ),
)
def create_pm_quality_fairness_analysis_endpoint(
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    fairness_repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = _build_fairness_analysis(
        request=request,
        x_correlation_id=x_correlation_id,
        repository=score_run_repository,
    )
    try:
        fairness_repository.save_fairness_analysis(analysis=fairness_analysis)
    except DpmPmQualityFairnessAnalysisConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


@router.get(
    "/fairness-analyses",
    response_model=DpmPmQualityFairnessAnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality fairness analyses",
    description=(
        "What: Return a bounded page of persisted PM operating quality fairness analyses.\n"
        "When: Use for PM operating-quality governance review, supportability diagnostics, and "
        "model-risk evidence retrieval.\n"
        "How: Filter by policy, as-of date, or bounded state. The response returns stored "
        "fairness-analysis evidence only and does not recompute score runs or segment posture."
    ),
)
def list_pm_quality_fairness_analyses_endpoint(
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    policy_version: Annotated[str | None, Query(description="Filter by policy version.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    state: Annotated[str | None, Query(description="Filter by fairness-analysis state.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessAnalysisListResponse:
    fairness_analyses = repository.list_fairness_analyses(
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        state=state,
        limit=limit,
        offset=offset,
    )
    return DpmPmQualityFairnessAnalysisListResponse(
        fairness_analyses=fairness_analyses,
        count=len(fairness_analyses),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/fairness-analyses/{fairness_analysis_id}",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality fairness analysis",
    description=(
        "What: Return one persisted PM operating quality fairness analysis by stable id.\n"
        "When: Use for audit, model-risk review, and downstream governance evidence retrieval.\n"
        "How: The endpoint returns immutable stored fairness-analysis evidence and does not "
        "recompute score runs, infer protected classes, or rank PMs."
    ),
)
def get_pm_quality_fairness_analysis_endpoint(
    fairness_analysis_id: str,
    repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = repository.get_fairness_analysis(fairness_analysis_id=fairness_analysis_id)
    if fairness_analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:{fairness_analysis_id}",
        )
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


def _build_fairness_analysis(
    *,
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: str | None,
    repository: DpmPmQualityScoreRunRepository,
) -> DpmPmQualityFairnessAnalysis:
    command = DpmPmQualityFairnessAnalysisCommand(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        as_of_date=request.as_of_date,
        segments=[
            DpmPmQualityFairnessSegmentCommand(
                segment_id=segment.segment_id,
                segment_type=segment.segment_type,
                display_name=segment.display_name,
                score_run_ids=segment.score_run_ids,
                source_refs=segment.source_refs,
            )
            for segment in request.segments
        ],
        minimum_segment_score_run_count=request.minimum_segment_score_run_count,
        maximum_average_score_spread=request.maximum_average_score_spread,
        actor_id=request.actor_id,
        correlation_id=x_correlation_id or request.actor_id,
    )
    try:
        return build_pm_quality_fairness_analysis_from_command(
            command=command,
            score_run_repository=repository,
        )
    except DpmPmOperatingQualityServiceError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code.startswith("PM_QUALITY_SCORE_RUN_NOT_FOUND:")
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail=exc.code,
        ) from exc
