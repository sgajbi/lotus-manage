"""PM operating-quality projection helpers for portfolio memory."""

from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.source_refs import from_outcome_source_ref
from src.core.portfolio_memory.supportability import (
    pm_quality_review_action_state,
    pm_quality_summary_invocation_state,
    source_supportability_state,
)


def score_run_includes_portfolio(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    portfolio_id: str,
) -> bool:
    """Return whether PM-book evidence links a score run to a portfolio."""

    if score_run.book_scope_evidence is None:
        return False
    if portfolio_id in score_run.book_scope_evidence.member_portfolio_ids:
        return True
    return any(
        ref.source_type == "PORTFOLIO_MANAGER_BOOK_MEMBER"
        and (ref.source_id == portfolio_id or ref.source_id.endswith(f":{portfolio_id}"))
        for ref in score_run.book_scope_evidence.source_refs
    )


def pm_quality_score_run_event(
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [from_outcome_source_ref(ref) for ref in score_run.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality:{score_run.score_run_id}",
        event_type="PM_QUALITY_SCORE_RUN",
        event_time=score_run.generated_at.isoformat(),
        actor=score_run.generated_by,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_SCORE_RUN",
        source_id=score_run.score_run_id,
        status=score_run.state,
        supportability_state=source_supportability_state(score_run.state),
        summary=(
            f"PM operating quality score run {score_run.score_run_id} is available for "
            f"PM {score_run.pm_id} under policy {score_run.policy_id}:{score_run.policy_version}."
        ),
        reason_codes=score_run.reason_codes,
        source_refs=source_refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityScoreRun",
                source_id=score_run.score_run_id,
                source_version=score_run.product_version,
                content_hash=score_run.content_hash,
            )
        ],
        content_hash=score_run.content_hash,
        metadata={
            "pm_id": score_run.pm_id,
            "book_id": score_run.book_id,
            "as_of_date": score_run.as_of_date,
            "policy_id": score_run.policy_id,
            "policy_version": score_run.policy_version,
            "score_state": score_run.state,
            "indicator_count": len(score_run.indicator_results),
            "numeric_score_projected": False,
            "portfolio_scope_source": "PortfolioManagerBookMembership:v1",
            "forbidden_uses": score_run.forbidden_uses,
        },
    )


def pm_quality_review_action_event(
    *,
    action: DpmPmQualityReviewAction,
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [from_outcome_source_ref(ref) for ref in action.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality_review_action:{action.review_action_id}",
        event_type="PM_QUALITY_REVIEW_ACTION",
        event_time=action.generated_at.isoformat(),
        actor=action.actor_id,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_REVIEW_ACTION",
        source_id=action.review_action_id,
        status=action.action_state,
        supportability_state=pm_quality_review_action_state(action),
        summary=(
            f"PM operating quality review action {action.action_type} recorded for "
            f"{action.target_type} {action.target_id}."
        ),
        reason_codes=sorted({*action.reason_codes, action.action_type, action.action_state}),
        source_refs=source_refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityReviewAction",
                source_id=action.review_action_id,
                source_version=action.product_version,
                content_hash=action.content_hash,
            ),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityScoreRun",
                source_id=score_run.score_run_id,
                source_version=score_run.product_version,
                content_hash=score_run.content_hash,
            ),
        ],
        content_hash=action.content_hash,
        metadata={
            "review_action_ref": action.review_action_ref,
            "target_type": action.target_type,
            "target_id": action.target_id,
            "target_content_hash": action.target_content_hash,
            "target_state": action.target_state,
            "policy_id": action.policy_id,
            "policy_version": action.policy_version,
            "as_of_date": action.as_of_date,
            "action_type": action.action_type,
            "action_state": action.action_state,
            "remediation_due_date": action.remediation_due_date,
            "correlation_id": action.correlation_id,
            "review_reason_projected": False,
            "numeric_score_projected": False,
            "score_recalculated": False,
            "fairness_recomputed": False,
            "pm_ranking_created": False,
            "client_contact_claimed": False,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
            "forbidden_uses": action.forbidden_uses,
            "operating_boundaries": action.operating_boundaries,
        },
    )


def pm_quality_summary_invocation_event(
    *,
    invocation: DpmPmQualitySummaryInvocation,
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [from_outcome_source_ref(ref) for ref in invocation.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    artifact_refs = [
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualitySummaryInvocation",
            source_id=invocation.summary_invocation_id,
            source_version=invocation.product_version,
            content_hash=invocation.content_hash,
        ),
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityScoreRun",
            source_id=score_run.score_run_id,
            source_version=score_run.product_version,
            content_hash=score_run.content_hash,
        ),
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityReviewAction",
            source_id=invocation.review_action_id,
            source_version="v1",
            content_hash=invocation.review_action_content_hash,
        ),
    ]
    if invocation.summary_artifact_ref is not None or invocation.summary_content_hash is not None:
        artifact_refs.append(
            DpmPortfolioMemorySourceRef(
                source_system="lotus-ai",
                source_type=invocation.workflow_pack_name,
                source_id=(
                    invocation.summary_artifact_ref
                    or invocation.workflow_run_id
                    or invocation.summary_invocation_id
                ),
                source_version=invocation.workflow_pack_version,
                content_hash=invocation.summary_content_hash,
            )
        )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality_summary_invocation:{invocation.summary_invocation_id}",
        event_type="PM_QUALITY_SUMMARY_INVOCATION",
        event_time=invocation.generated_at.isoformat(),
        actor=invocation.requested_by,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_SUMMARY_INVOCATION",
        source_id=invocation.summary_invocation_id,
        status=invocation.invocation_state,
        supportability_state=pm_quality_summary_invocation_state(invocation),
        summary=(
            "PM operating quality summary invocation history recorded for score run "
            f"{invocation.score_run_id} and review action {invocation.review_action_id}."
        ),
        reason_codes=sorted({*invocation.reason_codes, invocation.invocation_state}),
        source_refs=source_refs,
        artifact_refs=artifact_refs,
        content_hash=invocation.content_hash,
        metadata={
            "summary_ref": invocation.summary_ref,
            "score_run_id": invocation.score_run_id,
            "score_run_content_hash": invocation.score_run_content_hash,
            "review_action_id": invocation.review_action_id,
            "review_action_content_hash": invocation.review_action_content_hash,
            "policy_id": invocation.policy_id,
            "policy_version": invocation.policy_version,
            "as_of_date": invocation.as_of_date,
            "invocation_state": invocation.invocation_state,
            "workflow_pack_name": invocation.workflow_pack_name,
            "workflow_pack_version": invocation.workflow_pack_version,
            "workflow_run_id": invocation.workflow_run_id,
            "summary_artifact_ref": invocation.summary_artifact_ref,
            "summary_content_hash": invocation.summary_content_hash,
            "correlation_id": invocation.correlation_id,
            "summary_text_stored": False,
            "summary_text_exposed": False,
            "summary_text_projected": False,
            "downstream_summary_ux_projected": False,
            "prompt_reconstructed": False,
            "model_response_reconstructed": False,
            "review_reason_projected": False,
            "numeric_score_projected": False,
            "score_recalculated": False,
            "fairness_recomputed": False,
            "pm_ranking_created": False,
            "client_contact_claimed": False,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
            "summary_text_boundary_id": invocation.summary_text_boundary.boundary_id,
            "summary_text_boundary_content_hash": invocation.summary_text_boundary.content_hash,
            "forbidden_uses": invocation.forbidden_uses,
            "operating_boundaries": invocation.operating_boundaries,
        },
    )
