from __future__ import annotations

from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityReviewActionRequest,
    DpmPmQualitySummaryInvocationRequest,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmQualityBookScopeCommand,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    DpmPmQualityReviewActionCommand,
    DpmPmQualityScoreRunCommand,
    DpmPmQualitySummaryInvocationCommand,
)


def score_run_command_from_request(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: str | None,
) -> DpmPmQualityScoreRunCommand:
    return DpmPmQualityScoreRunCommand(
        pm_id=request.pm_id,
        book_id=request.book_id,
        as_of_date=request.as_of_date,
        policy=request.policy,
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        evidence_items=list(request.evidence_items),
        outcome_review_ids=list(request.outcome_review_ids),
        actor_id=request.actor_id,
        correlation_id=x_correlation_id or request.actor_id,
        book_scope=(
            DpmPmQualityBookScopeCommand(
                tenant_id=request.pm_book_scope.tenant_id,
                booking_center_code=request.pm_book_scope.booking_center_code,
                portfolio_types=list(request.pm_book_scope.portfolio_types),
                include_inactive=request.pm_book_scope.include_inactive,
            )
            if request.pm_book_scope is not None
            else None
        ),
    )


def fairness_analysis_command_from_request(
    *,
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: str | None,
) -> DpmPmQualityFairnessAnalysisCommand:
    return DpmPmQualityFairnessAnalysisCommand(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        as_of_date=request.as_of_date,
        segments=[
            DpmPmQualityFairnessSegmentCommand(
                segment_id=segment.segment_id,
                segment_type=segment.segment_type,
                display_name=segment.display_name,
                score_run_ids=list(segment.score_run_ids),
                source_refs=list(segment.source_refs),
            )
            for segment in request.segments
        ],
        minimum_segment_score_run_count=request.minimum_segment_score_run_count,
        maximum_average_score_spread=request.maximum_average_score_spread,
        actor_id=request.actor_id,
        correlation_id=x_correlation_id or request.actor_id,
    )


def review_action_command_from_request(
    *,
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
) -> DpmPmQualityReviewActionCommand:
    return DpmPmQualityReviewActionCommand(
        target_type=request.target_type,
        target_id=request.target_id,
        action_type=request.action_type,
        review_action_ref=request.review_action_ref,
        review_reason=request.review_reason,
        actor_id=request.actor_id,
        remediation_due_date=request.remediation_due_date,
        source_refs=list(request.source_refs),
        correlation_id=x_correlation_id or request.actor_id,
    )


def summary_invocation_command_from_request(
    *,
    request: DpmPmQualitySummaryInvocationRequest,
    x_correlation_id: str | None,
) -> DpmPmQualitySummaryInvocationCommand:
    return DpmPmQualitySummaryInvocationCommand(
        score_run_id=request.score_run_id,
        review_action_id=request.review_action_id,
        invocation_state=request.invocation_state,
        summary_ref=request.summary_ref,
        workflow_pack_name=request.workflow_pack_name,
        workflow_pack_version=request.workflow_pack_version,
        requested_by=request.requested_by,
        workflow_run_id=request.workflow_run_id,
        summary_artifact_ref=request.summary_artifact_ref,
        summary_content_hash=request.summary_content_hash,
        source_refs=list(request.source_refs),
        correlation_id=x_correlation_id or request.requested_by,
    )
