from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_review_action_repository
from src.api.routers.pm_operating_quality_http import pm_quality_not_found_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityReviewActionListResponse,
    DpmPmQualityReviewActionResponse,
)
from src.core.pm_quality import (
    DpmPmQualityReviewActionRepository,
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
        as_of_date: Annotated[
            str | None,
            Query(description="Filter by business as-of date."),
        ] = None,
        action_state: Annotated[
            PmQualityReviewActionState | None,
            Query(description="Filter by bounded review-action state."),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
        repository: DpmPmQualityReviewActionRepository = Depends(
            get_pm_quality_review_action_repository
        ),
    ) -> DpmPmQualityReviewActionListResponse:
        review_actions = repository.list_review_actions(
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
        repository: DpmPmQualityReviewActionRepository = Depends(
            get_pm_quality_review_action_repository
        ),
    ) -> DpmPmQualityReviewActionResponse:
        review_action = repository.get_review_action(review_action_id=review_action_id)
        if review_action is None:
            raise pm_quality_not_found_http_exception(
                code="PM_QUALITY_REVIEW_ACTION_NOT_FOUND",
                identifier=review_action_id,
            )
        return DpmPmQualityReviewActionResponse(review_action=review_action)
