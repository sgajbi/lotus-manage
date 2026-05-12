from decimal import Decimal

import pytest

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityEvidenceItem,
    DpmPmQualityValidationError,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from tests.unit.infrastructure.test_outcome_review_repository import _review


def _enabled_policy() -> DpmPmOperatingQualityPolicy:
    return DpmPmOperatingQualityPolicy(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("50")),
            DpmPmQualityWeight(indicator="SOURCE_QUALITY", weight=Decimal("30")),
            DpmPmQualityWeight(indicator="EVIDENCE_COMPLETENESS", weight=Decimal("20")),
        ],
    )


def test_pm_operating_quality_score_run_is_disabled_by_default() -> None:
    policy = DpmPmOperatingQualityPolicy(
        policy_id="pmq_disabled",
        policy_version="2026.05",
        enabled=False,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
    )

    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_001",
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=policy,
        evidence_items=[],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id="corr-001",
    )

    assert score_run.state == "DISABLED"
    assert score_run.score is None
    assert score_run.indicator_results == []
    assert score_run.reason_codes == ["PM_QUALITY_POLICY_DISABLED"]
    assert "compensation_decision" in score_run.forbidden_uses


def test_pm_operating_quality_score_run_uses_configured_policy_and_source_refs() -> None:
    review = _review().model_copy(
        update={
            "report_input_ref": DpmOutcomeSourceRef(
                source_system="lotus-report",
                source_type="DPM_OUTCOME_REPORT_INPUT",
                source_id="report_001",
                content_hash="sha256:report",
            )
        }
    )

    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_001",
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=_enabled_policy(),
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="EXCEPTION_DISCIPLINE",
                evidence_state="READY",
                score=Decimal("90"),
                source_system="lotus-manage",
                source_type="MonitoringExceptionQueue",
                source_id="exception_posture_001",
                reason_codes=["EXCEPTIONS_REVIEWED_ON_TIME"],
            )
        ],
        outcome_reviews=[review],
        generated_by="ops",
        correlation_id="corr-002",
    )

    assert score_run.product_name == "PmOperatingQualityScoreRun"
    assert score_run.state == "READY"
    assert score_run.score == Decimal("100.00")
    assert score_run.score_run_id.startswith("pmq_")
    assert score_run.content_hash.startswith("sha256:")
    assert [result.indicator for result in score_run.indicator_results] == [
        "OUTCOME_DISCIPLINE",
        "SOURCE_QUALITY",
        "EVIDENCE_COMPLETENESS",
    ]
    assert any(ref.source_type == "PostTradeOutcomeReview" for ref in score_run.source_refs)
    assert any(ref.source_type == "DPM_OUTCOME_REPORT_INPUT" for ref in score_run.source_refs)


def test_pm_operating_quality_score_run_blocks_when_required_evidence_is_missing() -> None:
    policy = DpmPmOperatingQualityPolicy(
        policy_id="pmq_missing",
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="EXCEPTION_DISCIPLINE",
                weight=Decimal("100"),
                minimum_evidence_count=2,
            )
        ],
    )

    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_001",
        book_id=None,
        as_of_date="2026-05-12",
        policy=policy,
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="EXCEPTION_DISCIPLINE",
                evidence_state="READY",
                score=Decimal("88"),
                source_system="lotus-manage",
                source_type="MonitoringExceptionQueue",
                source_id="exception_posture_001",
            )
        ],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id="corr-003",
    )

    assert score_run.state == "BLOCKED"
    assert score_run.score is None
    assert score_run.indicator_results[0].reason_codes == [
        "EXCEPTION_DISCIPLINE_REQUIRED_EVIDENCE_MISSING"
    ]
    assert "PM_QUALITY_REQUIRED_EVIDENCE_MISSING" in score_run.reason_codes


def test_pm_operating_quality_policy_rejects_prohibited_uses_and_date_mismatch() -> None:
    with pytest.raises(ValueError, match="prohibited use"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_bad",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("100"))],
            allowed_uses=["portfolio_management_review", "compensation"],
        )

    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH"):
        build_pm_operating_quality_score_run(
            pm_id="pm_001",
            book_id=None,
            as_of_date="2026-05-13",
            policy=_enabled_policy(),
            evidence_items=[],
            outcome_reviews=[],
            generated_by="ops",
            correlation_id="corr-004",
        )
