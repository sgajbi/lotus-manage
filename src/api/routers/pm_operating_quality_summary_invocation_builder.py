from __future__ import annotations

from src.api.routers.pm_operating_quality_http import (
    pm_quality_not_found_http_exception,
    pm_quality_validation_http_exception,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualitySummaryInvocationRequest,
)
from src.core.pm_quality import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocation,
    build_pm_quality_summary_invocation,
)


def build_summary_invocation_response_model(
    *,
    request: DpmPmQualitySummaryInvocationRequest,
    x_correlation_id: str | None,
    score_run_repository: DpmPmQualityScoreRunRepository,
    review_action_repository: DpmPmQualityReviewActionRepository,
) -> DpmPmQualitySummaryInvocation:
    score_run = score_run_repository.get_score_run(score_run_id=request.score_run_id)
    if score_run is None:
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
            identifier=request.score_run_id,
        )
    review_action = review_action_repository.get_review_action(
        review_action_id=request.review_action_id
    )
    if review_action is None:
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_REVIEW_ACTION_NOT_FOUND",
            identifier=request.review_action_id,
        )
    try:
        return build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action,
            invocation_state=request.invocation_state,
            summary_ref=request.summary_ref,
            workflow_pack_name=request.workflow_pack_name,
            workflow_pack_version=request.workflow_pack_version,
            workflow_run_id=request.workflow_run_id,
            summary_artifact_ref=request.summary_artifact_ref,
            summary_content_hash=request.summary_content_hash,
            requested_by=request.requested_by,
            source_refs=request.source_refs,
            correlation_id=x_correlation_id or request.requested_by,
        )
    except ValueError as exc:
        raise pm_quality_validation_http_exception(exc) from exc
