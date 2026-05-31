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
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis | None
    if request.target_type == "SCORE_RUN":
        target = score_run_repository.get_score_run(score_run_id=request.target_id)
        if target is None:
            raise pm_quality_not_found_http_exception(
                code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
                identifier=request.target_id,
            )
    else:
        target = fairness_repository.get_fairness_analysis(fairness_analysis_id=request.target_id)
        if target is None:
            raise pm_quality_not_found_http_exception(
                code="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND",
                identifier=request.target_id,
            )
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
            correlation_id=x_correlation_id or request.actor_id,
        )
    except ValueError as exc:
        raise pm_quality_validation_http_exception(exc) from exc
