from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_pm_quality_score_run_preview_application_service,
    get_pm_quality_score_run_application_service,
)
from src.api.routers.pm_operating_quality_command_mapping import score_run_command_from_request
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewResponse,
)
from src.api.routers.pm_operating_quality_http import (
    pm_quality_conflict_http_exception,
    pm_quality_service_http_exception,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_score_run_read_routes import (
    register_pm_quality_score_run_read_routes as register_pm_quality_score_run_read_routes,
)
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedScoreRunRequest,
    score_run_request_with_trusted_identity,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import DpmPmQualityScoreRunConflictError


def register_pm_quality_score_run_command_routes(
    router: APIRouter,
) -> None:
    @router.post(
        "/score-runs/preview",
        response_model=DpmPmOperatingQualityScorePreviewResponse,
        status_code=status.HTTP_200_OK,
        summary="Preview PM operating quality score run",
        description=(
            "What: Build a deterministic, explainable PM operating quality score run from an "
            "explicit bank-owned policy, source-owned evidence signals, and optional persisted "
            "outcome reviews.\n"
            "When: Use for DPM supervisory control, operations support, or evidence review after "
            "the bank has enabled a governed scoring policy.\n"
            "How: Supply the policy, source-backed evidence, and optional outcome-review ids. "
            "Disabled policies return a DISABLED run with no score; missing required evidence "
            "blocks the run. Optionally supply pm_book_scope to attach source-owned lotus-core "
            "PM-book membership evidence; unavailable, incomplete, degraded, or empty membership "
            "fails closed. Methodology: docs/methodologies/pm-quality/scoring-and-fairness.md. "
            "The endpoint does not create HR, compensation, conduct-enforcement, "
            "autonomous ranking, AI-generated, risk, performance, execution, or tax methodology."
        ),
    )
    def preview_pm_operating_quality_score_run_endpoint(
        trusted_request: PmQualityTrustedScoreRunRequest = Depends(
            score_run_request_with_trusted_identity
        ),
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_score_run_preview_application_service
        ),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        try:
            score_run = application_service.preview_score_run(
                score_run_command_from_request(
                    tenant_id=trusted_request.identity.tenant_id,
                    request=trusted_request.request,
                    x_correlation_id=x_correlation_id,
                )
            )
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)

    @router.post(
        "/score-runs",
        response_model=DpmPmOperatingQualityScorePreviewResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create persisted PM operating quality score run",
        description=(
            "What: Build and persist an immutable PM operating quality score run from an explicit "
            "bank-owned policy, source-owned evidence signals, and optional persisted outcome "
            "reviews.\n"
            "When: Use after a bank has approved PM operating quality scoring and needs auditable "
            "score-run lifecycle evidence.\n"
            "How: Supply the same evidence contract as preview. The persisted run is "
            "content-addressed and can be retrieved or listed for governance review. This endpoint "
            "uses methodology docs/methodologies/pm-quality/scoring-and-fairness.md and does not "
            "administer policies, create HR or compensation decisions, perform conduct "
            "enforcement, autonomously rank PMs, or calculate source-owned "
            "risk/performance/tax facts."
        ),
    )
    def create_pm_operating_quality_score_run_endpoint(
        trusted_request: PmQualityTrustedScoreRunRequest = Depends(
            score_run_request_with_trusted_identity
        ),
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_score_run_application_service
        ),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        try:
            score_run = application_service.create_score_run(
                score_run_command_from_request(
                    tenant_id=trusted_request.identity.tenant_id,
                    request=trusted_request.request,
                    x_correlation_id=x_correlation_id,
                )
            )
        except DpmPmQualityScoreRunConflictError as exc:
            raise pm_quality_conflict_http_exception(exc) from exc
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
