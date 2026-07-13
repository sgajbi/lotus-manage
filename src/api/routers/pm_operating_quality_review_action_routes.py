from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_pm_quality_review_action_application_service,
    get_pm_quality_review_action_preview_application_service,
)
from src.api.routers.pm_operating_quality_command_mapping import (
    review_action_command_from_request,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityReviewActionRequest,
    DpmPmQualityReviewActionResponse,
)
from src.api.routers.pm_operating_quality_http import (
    pm_quality_conflict_http_exception,
    pm_quality_service_http_exception,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_review_action_read_routes import (
    register_pm_quality_review_action_read_routes,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import (
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionIntegrityError,
)


def register_pm_quality_review_action_routes(
    router: APIRouter,
) -> None:
    @router.post(
        "/review-actions/preview",
        response_model=DpmPmQualityReviewActionResponse,
        status_code=status.HTTP_200_OK,
        summary="Preview PM operating quality review action",
        description=(
            "What: Build an immutable PM operating-quality review action over an existing "
            "persisted score run or fairness analysis without saving it.\n"
            "When: Use for supervisory, model-risk, evidence-remediation, or governance review "
            "before recording the action.\n"
            "How: Supply a persisted score-run or fairness-analysis id, a bounded action type, "
            "a bank review reference, rationale, actor, and optional source refs. The response "
            "preserves the target content hash and does not recalculate scores, recompute "
            "fairness, rank PMs, create HR/compensation/conduct decisions, contact clients, "
            "approve trades, route orders, or claim OMS execution."
        ),
    )
    def preview_pm_quality_review_action_endpoint(
        request: DpmPmQualityReviewActionRequest,
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_review_action_preview_application_service
        ),
    ) -> DpmPmQualityReviewActionResponse:
        try:
            review_action = application_service.preview_review_action(
                review_action_command_from_request(
                    request=request,
                    x_correlation_id=x_correlation_id,
                )
            )
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmQualityReviewActionResponse(review_action=review_action)

    @router.post(
        "/review-actions",
        response_model=DpmPmQualityReviewActionResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create persisted PM operating quality review action",
        description=(
            "What: Build and persist an immutable PM operating-quality review action over an "
            "existing score run or fairness analysis.\n"
            "When: Use when a bank needs auditable review, remediation, escalation, exception, "
            "or closure evidence for PM operating-quality outputs.\n"
            "How: Supply the same contract as preview. The action is content-addressed and can "
            "be listed or retrieved for governance review. It does not mutate the reviewed score "
            "run or fairness analysis and does not create HR, compensation, conduct, "
            "client-contact, trade, order, OMS, or autonomous-ranking decisions."
        ),
    )
    def create_pm_quality_review_action_endpoint(
        request: DpmPmQualityReviewActionRequest,
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_review_action_application_service
        ),
    ) -> DpmPmQualityReviewActionResponse:
        try:
            review_action = application_service.create_review_action(
                review_action_command_from_request(
                    request=request,
                    x_correlation_id=x_correlation_id,
                )
            )
        except (
            DpmPmQualityReviewActionConflictError,
            DpmPmQualityReviewActionIntegrityError,
        ) as exc:
            raise pm_quality_conflict_http_exception(exc) from exc
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmQualityReviewActionResponse(review_action=review_action)

    register_pm_quality_review_action_read_routes(router)
