from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_pm_quality_fairness_analysis_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityFairnessPreviewResponse,
)
from src.api.routers.pm_operating_quality_fairness_builder import (
    build_fairness_analysis_response_model,
)
from src.api.routers.pm_operating_quality_fairness_read_routes import (
    router as fairness_read_router,
)
from src.api.routers.pm_operating_quality_http import pm_quality_conflict_http_exception
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.core.pm_quality import (
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
    fairness_analysis = build_fairness_analysis_response_model(
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
    fairness_analysis = build_fairness_analysis_response_model(
        request=request,
        x_correlation_id=x_correlation_id,
        repository=score_run_repository,
    )
    try:
        fairness_repository.save_fairness_analysis(analysis=fairness_analysis)
    except DpmPmQualityFairnessAnalysisConflictError as exc:
        raise pm_quality_conflict_http_exception(exc) from exc
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


router.include_router(fairness_read_router)
