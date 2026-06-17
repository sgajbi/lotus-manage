from __future__ import annotations

from collections.abc import Callable

from src.api.routers.pm_operating_quality_http import (
    pm_quality_not_found_http_exception,
    pm_quality_validation_http_exception,
)
from src.api.routers.pm_operating_quality_models import DpmPmQualityReviewActionRequest
from src.core.pm_quality import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityScoreRunRepository,
)


def build_review_action(
    *,
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
    review_action_builder: Callable[..., DpmPmQualityReviewAction],
) -> DpmPmQualityReviewAction:
    target = _review_action_target(
        request=request,
        score_run_repository=score_run_repository,
        fairness_repository=fairness_repository,
    )
    return _build_review_action_with_validation(
        request=request,
        target=target,
        x_correlation_id=x_correlation_id,
        review_action_builder=review_action_builder,
    )


def _review_action_target(
    *,
    request: DpmPmQualityReviewActionRequest,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
) -> DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis:
    if request.target_type == "SCORE_RUN":
        return _score_run_review_action_target(
            score_run_id=request.target_id,
            score_run_repository=score_run_repository,
        )
    return _fairness_review_action_target(
        fairness_analysis_id=request.target_id,
        fairness_repository=fairness_repository,
    )


def _score_run_review_action_target(
    *,
    score_run_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
) -> DpmPmOperatingQualityScoreRun:
    target = score_run_repository.get_score_run(score_run_id=score_run_id)
    if target is None:
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
            identifier=score_run_id,
        )
    return target


def _fairness_review_action_target(
    *,
    fairness_analysis_id: str,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
) -> DpmPmQualityFairnessAnalysis:
    target = fairness_repository.get_fairness_analysis(fairness_analysis_id=fairness_analysis_id)
    if target is None:
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND",
            identifier=fairness_analysis_id,
        )
    return target


def _build_review_action_with_validation(
    *,
    request: DpmPmQualityReviewActionRequest,
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis,
    x_correlation_id: str | None,
    review_action_builder: Callable[..., DpmPmQualityReviewAction],
) -> DpmPmQualityReviewAction:
    try:
        return review_action_builder(
            target=target,
            target_type=request.target_type,
            action_type=request.action_type,
            review_action_ref=request.review_action_ref,
            review_reason=request.review_reason,
            actor_id=request.actor_id,
            source_refs=request.source_refs,
            remediation_due_date=request.remediation_due_date,
            correlation_id=_review_action_correlation_id(
                request=request,
                x_correlation_id=x_correlation_id,
            ),
        )
    except ValueError as exc:
        raise pm_quality_validation_http_exception(exc) from exc


def _review_action_correlation_id(
    *,
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
) -> str:
    return x_correlation_id or request.actor_id
