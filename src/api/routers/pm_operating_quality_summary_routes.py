from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_pm_quality_summary_invocation_application_service,
    get_pm_quality_summary_invocation_preview_application_service,
)
from src.api.routers.pm_operating_quality_command_mapping import (
    summary_invocation_command_from_request,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualitySummaryInvocationRequest,
    DpmPmQualitySummaryInvocationResponse,
)
from src.api.routers.pm_operating_quality_http import (
    pm_quality_conflict_http_exception,
    pm_quality_service_http_exception,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_summary_read_routes import (
    router as summary_read_router,
)
from src.api.routers.pm_operating_quality_trusted_identity import (
    summary_invocation_request_with_trusted_identity,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import (
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationIntegrityError,
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
    request: DpmPmQualitySummaryInvocationRequest = Depends(
        summary_invocation_request_with_trusted_identity
    ),
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_summary_invocation_preview_application_service
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    try:
        invocation = application_service.preview_summary_invocation(
            summary_invocation_command_from_request(
                request=request,
                x_correlation_id=x_correlation_id,
            )
        )
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
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
    request: DpmPmQualitySummaryInvocationRequest = Depends(
        summary_invocation_request_with_trusted_identity
    ),
    x_correlation_id: PmQualityCorrelationIdHeader = None,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_summary_invocation_application_service
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    try:
        invocation = application_service.create_summary_invocation(
            summary_invocation_command_from_request(
                request=request,
                x_correlation_id=x_correlation_id,
            )
        )
    except (
        DpmPmQualitySummaryInvocationConflictError,
        DpmPmQualitySummaryInvocationIntegrityError,
    ) as exc:
        raise pm_quality_conflict_http_exception(exc) from exc
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
    return DpmPmQualitySummaryInvocationResponse(summary_invocation=invocation)


router.include_router(summary_read_router)
