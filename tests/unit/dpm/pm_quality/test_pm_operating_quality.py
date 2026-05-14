from decimal import Decimal

import pytest

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityEvidenceItem,
    DpmPmQualityIndicatorResult,
    DpmPmQualityValidationError,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from src.core.pm_quality import scoring
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
        governance_approval=_governance_approval(),
    )


def _governance_approval() -> DpmPmQualityGovernanceApproval:
    return DpmPmQualityGovernanceApproval(
        approval_ref="PMQ-APPROVAL-2026-05",
        approved_by="pm_quality_committee",
        approved_at="2026-05-10T09:00:00Z",
        fairness_review_ref="FAIRNESS-PMQ-2026-05",
        fairness_reviewed_by="model_risk_governance",
        fairness_reviewed_at="2026-05-10T10:00:00Z",
        expires_on="2026-06-30",
        entitled_actor_ids=["ops"],
        source_refs=[
            DpmOutcomeSourceRef(
                source_system="bank-governance",
                source_type="PM_QUALITY_POLICY_APPROVAL",
                source_id="PMQ-APPROVAL-2026-05",
            )
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
    assert score_run.governance_evidence is None


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
    assert score_run.governance_evidence is not None
    assert score_run.governance_evidence.approval_ref == "PMQ-APPROVAL-2026-05"
    assert score_run.governance_evidence.fairness_review_ref == "FAIRNESS-PMQ-2026-05"
    assert score_run.governance_evidence.actor_entitlement_state == "AUTHORIZED"
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
        governance_approval=_governance_approval(),
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
            governance_approval=_governance_approval(),
            allowed_uses=["portfolio_management_review", "compensation"],
        )


def test_pm_quality_scoring_guard_edges_are_source_safe() -> None:
    ready_result = DpmPmQualityIndicatorResult(
        indicator="SOURCE_QUALITY",
        score=Decimal("80"),
        weight=Decimal("100"),
        state="READY",
        evidence_count=1,
        reason_codes=["SOURCE_READY"],
        source_refs=[],
    )
    degraded_result = ready_result.model_copy(
        update={"state": "DEGRADED", "reason_codes": ["SOURCE_DEGRADED"]}
    )
    breached_result = ready_result.model_copy(
        update={"state": "BREACHED", "reason_codes": ["POLICY_BREACHED"]}
    )

    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_NO_SCORABLE_INDICATORS",
    ):
        scoring._weighted_score([])

    assert (
        scoring._score_state(
            score=Decimal("80"), policy=_enabled_policy(), results=[breached_result]
        )
        == "BREACHED"
    )
    assert (
        scoring._score_state(
            score=Decimal("80"), policy=_enabled_policy(), results=[degraded_result]
        )
        == "DEGRADED"
    )
    assert (
        scoring._score_state(score=Decimal("75"), policy=_enabled_policy(), results=[ready_result])
        == "PENDING_REVIEW"
    )
    assert (
        scoring._score_state(score=Decimal("40"), policy=_enabled_policy(), results=[ready_result])
        == "BREACHED"
    )
    assert scoring._score_reason_codes(state="DEGRADED", results=[degraded_result]) == [
        "PM_QUALITY_DEGRADED_SOURCE_POSTURE",
        "SOURCE_DEGRADED",
    ]
    assert scoring._worst_state(["DISABLED"]) == "DISABLED"
    assert scoring._worst_state(["BLOCKED"]) == "BLOCKED"
    assert scoring._worst_state(["BREACHED"]) == "BREACHED"
    assert scoring._worst_state(["DEGRADED"]) == "DEGRADED"
    assert scoring._worst_state(["PENDING_REVIEW"]) == "PENDING_REVIEW"
    assert scoring._worst_state(["UNKNOWN"]) == "DEGRADED"
    assert scoring._mean([]) == Decimal("0")


def test_pm_quality_governance_evidence_rejects_stale_or_unauthorized_policy() -> None:
    policy = _enabled_policy().model_copy(update={"governance_approval": None})
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED",
    ):
        scoring._governance_evidence(policy=policy, as_of_date="2026-05-12", generated_by="ops")

    expired_policy = _enabled_policy().model_copy(
        update={
            "governance_approval": _governance_approval().model_copy(
                update={"expires_on": "2026-05-01"}
            )
        }
    )
    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_GOVERNANCE_EXPIRED"):
        scoring._governance_evidence(
            policy=expired_policy,
            as_of_date="2026-05-12",
            generated_by="ops",
        )

    unauthorized_policy = _enabled_policy()
    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_ACTOR_NOT_ENTITLED"):
        scoring._governance_evidence(
            policy=unauthorized_policy,
            as_of_date="2026-05-12",
            generated_by="unauthorized",
        )

    with pytest.raises(ValueError, match="PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_missing_governance",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("100"))],
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
