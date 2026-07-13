from __future__ import annotations

from decimal import Decimal

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityEvidenceItem,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from src.core.pm_quality.fairness_analysis import (
    DpmPmQualityFairnessSegmentInput,
    build_pm_operating_quality_fairness_analysis,
)


def test_pm_quality_methodology_score_run_worked_example_matches_document() -> None:
    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_methodology",
        book_id="book_methodology",
        as_of_date="2026-05-12",
        policy=_policy(ready_threshold="85", watch_threshold="70"),
        evidence_items=[
            _evidence(
                indicator="OUTCOME_DISCIPLINE",
                state="READY",
                score="90",
                source_id="outcome-ready",
                source_version="2026-05-10",
            ),
            _evidence(
                indicator="OUTCOME_DISCIPLINE",
                state="PENDING_REVIEW",
                score=None,
                source_id="outcome-review",
                source_version="2026-05-11",
            ),
            _evidence(
                indicator="SOURCE_QUALITY",
                state="READY",
                score="75",
                source_id="source-ready",
                source_version="2026-05-11",
            ),
        ],
        outcome_reviews=[],
        generated_by="pm_quality_methodology_test",
        correlation_id="corr-methodology-score",
    )

    assert score_run.score == Decimal("78.00")
    assert score_run.state == "PENDING_REVIEW"
    assert "PM_QUALITY_REQUIRES_REVIEW" in score_run.reason_codes
    assert "OUTCOME_DISCIPLINE_SOURCE_SIGNAL" in score_run.reason_codes
    assert {
        result.indicator: (result.score, result.weight, result.evidence_count)
        for result in score_run.indicator_results
    } == {
        "OUTCOME_DISCIPLINE": (Decimal("80"), Decimal("60"), 2),
        "SOURCE_QUALITY": (Decimal("75"), Decimal("40"), 1),
    }


def test_pm_quality_methodology_score_run_rounds_half_up_at_two_decimals() -> None:
    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_methodology_rounding",
        book_id="book_methodology",
        as_of_date="2026-05-12",
        policy=_policy(ready_threshold="90", watch_threshold="70"),
        evidence_items=[
            _evidence(
                indicator="OUTCOME_DISCIPLINE",
                state="READY",
                score="78.005",
                source_id="rounding-outcome",
                source_version="2026-05-12",
            ),
            _evidence(
                indicator="SOURCE_QUALITY",
                state="READY",
                score="78.005",
                source_id="rounding-source",
                source_version="2026-05-12",
            ),
        ],
        outcome_reviews=[],
        generated_by="pm_quality_methodology_test",
        correlation_id="corr-methodology-rounding",
    )

    assert score_run.score == Decimal("78.01")


def test_pm_quality_methodology_fairness_worked_example_matches_document() -> None:
    policy = _policy(ready_threshold="90", watch_threshold="70")
    analysis = build_pm_operating_quality_fairness_analysis(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        as_of_date="2026-05-12",
        minimum_segment_score_run_count=2,
        maximum_average_score_spread=Decimal("10"),
        segments=[
            _segment(
                segment_id="sg-core",
                display_name="Singapore Core",
                scores=["88", "84"],
                policy=policy,
            ),
            _segment(
                segment_id="hk-core",
                display_name="Hong Kong Core",
                scores=["76", "74"],
                policy=policy,
            ),
        ],
        generated_by="pm_quality_methodology_test",
        correlation_id="corr-methodology-fairness",
    )

    assert analysis.state == "PENDING_REVIEW"
    assert analysis.observed_average_score_spread == Decimal("11.00")
    assert analysis.reason_codes == ["PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED"]
    assert {
        result.segment_id: (result.average_score, result.minimum_score, result.maximum_score)
        for result in analysis.segment_results
    } == {
        "sg-core": (Decimal("86"), Decimal("84"), Decimal("88")),
        "hk-core": (Decimal("75"), Decimal("74"), Decimal("76")),
    }


def _policy(*, ready_threshold: str, watch_threshold: str) -> DpmPmOperatingQualityPolicy:
    return DpmPmOperatingQualityPolicy(
        policy_id="pmq_methodology",
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="OUTCOME_DISCIPLINE",
                weight=Decimal("60"),
                minimum_evidence_count=1,
            ),
            DpmPmQualityWeight(
                indicator="SOURCE_QUALITY",
                weight=Decimal("40"),
                minimum_evidence_count=1,
            ),
        ],
        ready_threshold=Decimal(ready_threshold),
        watch_threshold=Decimal(watch_threshold),
        governance_approval=DpmPmQualityGovernanceApproval(
            approval_ref="PMQ-METHODOLOGY-APPROVAL",
            approved_by="pm_quality_committee",
            approved_at="2026-05-01T00:00:00Z",
            fairness_review_ref="PMQ-METHODOLOGY-FAIRNESS",
            fairness_reviewed_by="model_risk_committee",
            fairness_reviewed_at="2026-05-01T00:00:00Z",
            source_refs=[_source_ref("policy-governance", "2026-05-01")],
        ),
    )


def _segment(
    *,
    segment_id: str,
    display_name: str,
    scores: list[str],
    policy: DpmPmOperatingQualityPolicy,
) -> DpmPmQualityFairnessSegmentInput:
    return DpmPmQualityFairnessSegmentInput(
        segment_id=segment_id,
        segment_type="REGION",
        display_name=display_name,
        source_refs=[_source_ref(f"{segment_id}-source", "2026-05-12")],
        score_runs=[
            build_pm_operating_quality_score_run(
                pm_id=f"pm_{segment_id}_{index}",
                book_id=f"book_{segment_id}",
                as_of_date="2026-05-12",
                policy=policy,
                evidence_items=[
                    _evidence(
                        indicator="OUTCOME_DISCIPLINE",
                        state="READY",
                        score=score,
                        source_id=f"{segment_id}-{index}-outcome",
                        source_version="2026-05-12",
                    ),
                    _evidence(
                        indicator="SOURCE_QUALITY",
                        state="READY",
                        score=score,
                        source_id=f"{segment_id}-{index}-source",
                        source_version="2026-05-12",
                    ),
                ],
                outcome_reviews=[],
                generated_by="pm_quality_methodology_test",
                correlation_id=f"corr-{segment_id}-{index}",
            )
            for index, score in enumerate(scores, start=1)
        ],
    )


def _evidence(
    *,
    indicator: str,
    state: str,
    score: str | None,
    source_id: str,
    source_version: str,
) -> DpmPmQualityEvidenceItem:
    return DpmPmQualityEvidenceItem(
        indicator=indicator,
        evidence_state=state,
        score=Decimal(score) if score is not None else None,
        source_system="methodology-fixture",
        source_type="PM_QUALITY_METHODOLOGY_EXAMPLE",
        source_id=source_id,
        source_refs=[_source_ref(source_id, source_version)],
    )


def _source_ref(source_id: str, source_version: str) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="methodology-fixture",
        source_type="PM_QUALITY_METHODOLOGY_EXAMPLE",
        source_id=source_id,
        source_version=source_version,
        content_hash=f"sha256:{source_id}",
    )
