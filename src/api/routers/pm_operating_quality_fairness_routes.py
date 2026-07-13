from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_pm_quality_fairness_application_service,
    get_pm_quality_fairness_preview_application_service,
)
from src.api.routers.pm_operating_quality_command_mapping import (
    fairness_analysis_command_from_request,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityFairnessPreviewResponse,
)
from src.api.routers.pm_operating_quality_fairness_read_routes import (
    router as fairness_read_router,
)
from src.api.routers.pm_operating_quality_http import (
    pm_quality_conflict_http_exception,
    pm_quality_service_http_exception,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedFairnessRequest,
    fairness_request_with_trusted_identity,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import DpmPmQualityFairnessAnalysisConflictError


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
        "Methodology: docs/methodologies/pm-quality/scoring-and-fairness.md. This endpoint does "
        "not infer protected classes, rank PMs, administer compensation or HR decisions, perform "
        "conduct enforcement, or calculate source-owned risk/performance facts."
    ),
)
def preview_pm_quality_fairness_analysis_endpoint(
    trusted_request: PmQualityTrustedFairnessRequest = Depends(
        fairness_request_with_trusted_identity
    ),
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_fairness_preview_application_service
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    try:
        fairness_analysis = application_service.preview_fairness_analysis(
            fairness_analysis_command_from_request(
                tenant_id=trusted_request.identity.tenant_id,
                request=trusted_request.request,
                x_correlation_id=x_correlation_id,
            )
        )
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
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
        "content-addressed and can be listed or retrieved for governance review. Methodology: "
        "docs/methodologies/pm-quality/scoring-and-fairness.md. This endpoint does not infer "
        "protected classes, rank PMs, administer compensation or HR decisions, perform conduct "
        "enforcement, or calculate source-owned risk/performance facts."
    ),
)
def create_pm_quality_fairness_analysis_endpoint(
    trusted_request: PmQualityTrustedFairnessRequest = Depends(
        fairness_request_with_trusted_identity
    ),
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_fairness_application_service
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    try:
        fairness_analysis = application_service.create_fairness_analysis(
            fairness_analysis_command_from_request(
                tenant_id=trusted_request.identity.tenant_id,
                request=trusted_request.request,
                x_correlation_id=x_correlation_id,
            )
        )
    except DpmPmQualityFairnessAnalysisConflictError as exc:
        raise pm_quality_conflict_http_exception(exc) from exc
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


router.include_router(fairness_read_router)
