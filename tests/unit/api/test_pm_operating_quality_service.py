from __future__ import annotations

from decimal import Decimal

import pytest

from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityServiceError,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    build_pm_quality_fairness_analysis_from_command,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityEvidenceItem,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository


def _score_run(*, pm_id: str, score: Decimal, correlation_id: str):
    policy = DpmPmOperatingQualityPolicy(
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
    return build_pm_operating_quality_score_run(
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=policy,
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


def test_pm_quality_service_builds_fairness_analysis_from_persisted_score_runs() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    balanced = _score_run(pm_id="pm_balanced", score=Decimal("91"), correlation_id="corr-1")
    growth = _score_run(pm_id="pm_growth", score=Decimal("59"), correlation_id="corr-2")
    repository.save_score_run(score_run=balanced)
    repository.save_score_run(score_run=growth)

    analysis = build_pm_quality_fairness_analysis_from_command(
        command=DpmPmQualityFairnessAnalysisCommand(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="balanced",
                    segment_type="MANDATE_TYPE",
                    display_name="Balanced mandates",
                    score_run_ids=[balanced.score_run_id],
                ),
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="growth",
                    segment_type="MANDATE_TYPE",
                    display_name="Growth mandates",
                    score_run_ids=[growth.score_run_id],
                ),
            ],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("15"),
            actor_id="ops",
            correlation_id="corr-fairness",
        ),
        score_run_repository=repository,
    )

    assert analysis.policy_id == "pmq_sg_dpm"
    assert analysis.state == "PENDING_REVIEW"
    assert analysis.observed_average_score_spread == Decimal("32.00")
    assert analysis.correlation_id == "corr-fairness"


def test_pm_quality_service_reports_missing_score_run_with_stable_code() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SCORE_RUN_NOT_FOUND:missing",
    ):
        build_pm_quality_fairness_analysis_from_command(
            command=DpmPmQualityFairnessAnalysisCommand(
                policy_id="pmq_sg_dpm",
                policy_version="2026.05",
                as_of_date="2026-05-12",
                segments=[
                    DpmPmQualityFairnessSegmentCommand(
                        segment_id="balanced",
                        segment_type="MANDATE_TYPE",
                        display_name="Balanced mandates",
                        score_run_ids=["missing"],
                    ),
                    DpmPmQualityFairnessSegmentCommand(
                        segment_id="growth",
                        segment_type="MANDATE_TYPE",
                        display_name="Growth mandates",
                        score_run_ids=["also-missing"],
                    ),
                ],
                minimum_segment_score_run_count=1,
                maximum_average_score_spread=Decimal("15"),
                actor_id="ops",
                correlation_id="corr-fairness",
            ),
            score_run_repository=repository,
        )
