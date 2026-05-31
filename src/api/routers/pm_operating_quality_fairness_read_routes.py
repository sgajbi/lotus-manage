from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_fairness_analysis_repository
from src.api.routers.pm_operating_quality_http import pm_quality_not_found_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityFairnessAnalysisListResponse,
    DpmPmQualityFairnessPreviewResponse,
)
from src.core.pm_quality import DpmPmQualityFairnessAnalysisRepository

router = APIRouter()


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
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND",
            identifier=fairness_analysis_id,
        )
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)
