from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_fairness_application_service
from src.api.routers.pm_operating_quality_http import pm_quality_service_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityFairnessAnalysisListResponse,
    DpmPmQualityFairnessPreviewResponse,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)

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
        "fairness-analysis evidence only, follows methodology "
        "docs/methodologies/pm-quality/scoring-and-fairness.md, and does not recompute score runs "
        "or segment posture."
    ),
)
def list_pm_quality_fairness_analyses_endpoint(
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    policy_version: Annotated[str | None, Query(description="Filter by policy version.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    state: Annotated[str | None, Query(description="Filter by fairness-analysis state.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_fairness_application_service
    ),
) -> DpmPmQualityFairnessAnalysisListResponse:
    fairness_analyses = application_service.list_fairness_analyses(
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
        "recompute score runs, infer protected classes, or rank PMs. Methodology: "
        "docs/methodologies/pm-quality/scoring-and-fairness.md."
    ),
)
def get_pm_quality_fairness_analysis_endpoint(
    fairness_analysis_id: str,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_fairness_application_service
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    try:
        fairness_analysis = application_service.get_fairness_analysis(
            fairness_analysis_id=fairness_analysis_id
        )
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)
