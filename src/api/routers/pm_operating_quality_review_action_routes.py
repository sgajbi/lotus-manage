from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    get_pm_quality_fairness_analysis_repository,
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualityReviewActionRequest,
    DpmPmQualityReviewActionResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_review_action_read_routes import (
    register_pm_quality_review_action_read_routes,
)
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
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

    register_pm_quality_review_action_read_routes(router)
