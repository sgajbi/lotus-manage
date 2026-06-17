from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException

from src.api.routers.pm_operating_quality_models import DpmPmQualityReviewActionRequest
from src.api.routers.pm_operating_quality_review_action_builder import build_review_action
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessSegmentInput,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityReviewAction,
    DpmPmQualityWeight,
    PmQualityReviewActionTargetType,
    build_pm_operating_quality_fairness_analysis,
    build_pm_operating_quality_score_run,
    build_pm_quality_review_action,
)
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)


def _policy() -> DpmPmOperatingQualityPolicy:
    return DpmPmOperatingQualityPolicy(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="SOURCE_QUALITY",
                weight=Decimal("100"),
                minimum_evidence_count=1,
            )
        ],
        governance_approval=DpmPmQualityGovernanceApproval(
            approval_ref="PMQ-APPROVAL-2026-05",
            approved_by="pm_quality_committee",
            approved_at="2026-05-10T09:00:00Z",
            fairness_review_ref="FAIRNESS-PMQ-2026-05",
            fairness_reviewed_by="model_risk_governance",
            fairness_reviewed_at="2026-05-10T10:00:00Z",
        ),
    )


def _score_run(
    *,
    pm_id: str = "pm_001",
    score: Decimal = Decimal("91"),
    correlation_id: str = "corr-score",
) -> DpmPmOperatingQualityScoreRun:
    return build_pm_operating_quality_score_run(
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=_policy(),
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="SOURCE_QUALITY",
                evidence_state="READY",
                score=score,
                source_system="lotus-risk",
                source_type="RiskMetricsReport",
                source_id=f"risk-{pm_id}",
            )
        ],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id=correlation_id,
    )


def _fairness_analysis() -> DpmPmQualityFairnessAnalysis:
    return build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[
            DpmPmQualityFairnessSegmentInput(
                segment_id="balanced",
                segment_type="MANDATE_TYPE",
                display_name="Balanced mandates",
                score_runs=[_score_run(pm_id="pm_001", score=Decimal("91"))],
                source_refs=[],
            ),
            DpmPmQualityFairnessSegmentInput(
                segment_id="growth",
                segment_type="MANDATE_TYPE",
                display_name="Growth mandates",
                score_runs=[_score_run(pm_id="pm_002", score=Decimal("89"))],
                source_refs=[],
            ),
        ],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("15"),
        generated_by="ops",
        correlation_id="corr-fairness",
    )


def _review_action_request(
    *,
    target_type: PmQualityReviewActionTargetType = "SCORE_RUN",
    target_id: str,
    actor_id: str = "ops",
) -> DpmPmQualityReviewActionRequest:
    return DpmPmQualityReviewActionRequest(
        target_type=target_type,
        target_id=target_id,
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged.",
        actor_id=actor_id,
        source_refs=[],
    )


def test_build_review_action_resolves_score_run_target_and_uses_header_correlation_id() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run()
    score_run_repository.save_score_run(score_run=score_run)

    review_action = build_review_action(
        request=_review_action_request(target_id=score_run.score_run_id),
        x_correlation_id="corr-header",
        score_run_repository=score_run_repository,
        fairness_repository=InMemoryDpmPmQualityFairnessAnalysisRepository(),
        review_action_builder=build_pm_quality_review_action,
    )

    assert review_action.target_type == "SCORE_RUN"
    assert review_action.target_id == score_run.score_run_id
    assert review_action.correlation_id == "corr-header"


def test_build_review_action_resolves_fairness_target_and_falls_back_to_actor_id() -> None:
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    analysis = _fairness_analysis()
    fairness_repository.save_fairness_analysis(analysis=analysis)

    review_action = build_review_action(
        request=_review_action_request(
            target_type="FAIRNESS_ANALYSIS",
            target_id=analysis.fairness_analysis_id,
            actor_id="supervisor",
        ),
        x_correlation_id=None,
        score_run_repository=InMemoryDpmPmQualityScoreRunRepository(),
        fairness_repository=fairness_repository,
        review_action_builder=build_pm_quality_review_action,
    )

    assert review_action.target_type == "FAIRNESS_ANALYSIS"
    assert review_action.target_id == analysis.fairness_analysis_id
    assert review_action.correlation_id == "supervisor"


@pytest.mark.parametrize(
    ("target_type", "detail"),
    [
        ("SCORE_RUN", "PM_QUALITY_SCORE_RUN_NOT_FOUND:missing"),
        ("FAIRNESS_ANALYSIS", "PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:missing"),
    ],
)
def test_build_review_action_reports_missing_targets_with_stable_http_codes(
    target_type: PmQualityReviewActionTargetType,
    detail: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        build_review_action(
            request=_review_action_request(target_type=target_type, target_id="missing"),
            x_correlation_id="corr",
            score_run_repository=InMemoryDpmPmQualityScoreRunRepository(),
            fairness_repository=InMemoryDpmPmQualityFairnessAnalysisRepository(),
            review_action_builder=build_pm_quality_review_action,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == detail


def test_build_review_action_translates_domain_validation_errors() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run()
    score_run_repository.save_score_run(score_run=score_run)

    def rejected_review_action_builder(**_: Any) -> DpmPmQualityReviewAction:
        raise ValueError("PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH")

    with pytest.raises(HTTPException) as exc_info:
        build_review_action(
            request=_review_action_request(target_id=score_run.score_run_id),
            x_correlation_id="corr",
            score_run_repository=score_run_repository,
            fairness_repository=InMemoryDpmPmQualityFairnessAnalysisRepository(),
            review_action_builder=rejected_review_action_builder,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH"
