from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_pm_quality_fairness_analysis_repository,
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityReviewActionListResponse,
    DpmPmQualityReviewActionRequest,
    DpmPmQualityReviewActionResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    PmQualityReviewActionState,
    PmQualityReviewActionTargetType,
)


ReviewActionBuilder = Callable[
    [
        DpmPmQualityReviewActionRequest,
        str | None,
        DpmPmQualityScoreRunRepository,
        DpmPmQualityFairnessAnalysisRepository,
    ],
    DpmPmQualityReviewAction,
]


def register_pm_quality_review_action_routes(
    router: APIRouter,
    build_review_action: ReviewActionBuilder,
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
        score_run_repository: DpmPmQualityScoreRunRepository = Depends(
            get_pm_quality_score_run_repository
        ),
        fairness_repository: DpmPmQualityFairnessAnalysisRepository = Depends(
            get_pm_quality_fairness_analysis_repository
        ),
    ) -> DpmPmQualityReviewActionResponse:
        review_action = build_review_action(
            request,
            x_correlation_id,
            score_run_repository,
            fairness_repository,
        )
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
        score_run_repository: DpmPmQualityScoreRunRepository = Depends(
            get_pm_quality_score_run_repository
        ),
        fairness_repository: DpmPmQualityFairnessAnalysisRepository = Depends(
            get_pm_quality_fairness_analysis_repository
        ),
        review_action_repository: DpmPmQualityReviewActionRepository = Depends(
            get_pm_quality_review_action_repository
        ),
    ) -> DpmPmQualityReviewActionResponse:
        review_action = build_review_action(
            request,
            x_correlation_id,
            score_run_repository,
            fairness_repository,
        )
        try:
            review_action_repository.save_review_action(action=review_action)
        except DpmPmQualityReviewActionConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        return DpmPmQualityReviewActionResponse(review_action=review_action)

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PM_QUALITY_REVIEW_ACTION_NOT_FOUND:{review_action_id}",
            )
        return DpmPmQualityReviewActionResponse(review_action=review_action)
