from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_review_action_application_service
from src.api.routers.pm_operating_quality_http import pm_quality_service_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityReviewActionListResponse,
    DpmPmQualityReviewActionResponse,
)
from src.api.routers.pm_operating_quality_temporal_filters import pm_quality_as_of_date_filter
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedIdentity,
    pm_quality_trusted_identity_required,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import (
    PmQualityReviewActionState,
    PmQualityReviewActionTargetType,
)


def register_pm_quality_review_action_read_routes(router: APIRouter) -> None:
    @router.get(
        "/review-actions",
        response_model=DpmPmQualityReviewActionListResponse,
        status_code=status.HTTP_200_OK,
        summary="List persisted PM operating quality review actions",
        description=(
            "What: Return a bounded page of persisted PM operating-quality review actions.\n"
            "When: Use for supervisory control, model-risk review, audit, and supportability "
            "diagnostics.\n"
            "How: Filter by target, policy, as-of date, or action state. The response returns "
            "stored review-action evidence only and does not recompute or mutate score runs or "
            "fairness analyses."
        ),
    )
    def list_pm_quality_review_actions_endpoint(
        target_type: Annotated[
            PmQualityReviewActionTargetType | None,
            Query(description="Filter by reviewed product family."),
        ] = None,
        target_id: Annotated[
            str | None,
            Query(description="Filter by reviewed evidence id."),
        ] = None,
        policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
        as_of_date: Annotated[str | None, Depends(pm_quality_as_of_date_filter)] = None,
        action_state: Annotated[
            PmQualityReviewActionState | None,
            Query(description="Filter by bounded review-action state."),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_review_action_application_service
        ),
        identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
    ) -> DpmPmQualityReviewActionListResponse:
        review_actions = application_service.list_review_actions(
            tenant_id=identity.tenant_id,
            target_type=target_type,
            target_id=target_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            action_state=action_state,
            limit=limit,
            offset=offset,
        )
        return DpmPmQualityReviewActionListResponse(
            review_actions=review_actions,
            count=len(review_actions),
            limit=limit,
            offset=offset,
        )

    @router.get(
        "/review-actions/{review_action_id}",
        response_model=DpmPmQualityReviewActionResponse,
        status_code=status.HTTP_200_OK,
        summary="Get persisted PM operating quality review action",
        description=(
            "What: Return one persisted PM operating-quality review action by stable id.\n"
            "When: Use for audit, supervisory control, model-risk review, and downstream "
            "governance evidence retrieval.\n"
            "How: The endpoint returns immutable stored review-action evidence and does not "
            "recompute or mutate the reviewed score run or fairness analysis."
        ),
    )
    def get_pm_quality_review_action_endpoint(
        review_action_id: str,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_review_action_application_service
        ),
        identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
    ) -> DpmPmQualityReviewActionResponse:
        try:
            review_action = application_service.get_review_action(
                tenant_id=identity.tenant_id,
                review_action_id=review_action_id,
            )
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmQualityReviewActionResponse(review_action=review_action)
