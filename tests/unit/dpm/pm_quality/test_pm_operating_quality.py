from datetime import date
from decimal import Decimal

import pytest

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityFairnessSegmentInput,
    DpmPmQualityFairnessSegmentResult,
    DpmPmOperatingQualityPolicy,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityEvidenceItem,
    DpmPmQualityIndicatorResult,
    DpmPmQualityLookbackWindowPolicy,
    DpmPmQualityPeerGroupPolicy,
    DpmPmQualityValidationError,
    DpmPmQualityWeight,
    build_pm_operating_quality_fairness_analysis,
    build_pm_operating_quality_score_run,
    build_pm_quality_review_action,
    build_pm_quality_summary_invocation,
)
from src.core.pm_quality import scoring
from src.core.pm_quality import summary_history
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


def _scope_policy() -> DpmPmOperatingQualityPolicy:
    payload = _enabled_policy().model_dump(mode="python")
    payload.update(
        {
            "peer_group_policy": {
                "peer_group_id": "sg_dpm_balanced",
                "display_name": "Singapore DPM balanced mandates",
                "segment_type": "MANDATE_TYPE",
                "minimum_peer_count": 3,
                "source_refs": [
                    DpmOutcomeSourceRef(
                        source_system="lotus-core",
                        source_type="PM_QUALITY_PEER_GROUP_DEFINITION",
                        source_id="sg_dpm_balanced",
                        source_version="2026.05",
                    )
                ],
            },
            "lookback_window_policy": {
                "window_id": "pmq_30d_20260512",
                "start_date": "2026-04-13",
                "end_date": "2026-05-12",
                "timezone": "Asia/Singapore",
                "source_refs": [
                    DpmOutcomeSourceRef(
                        source_system="bank-governance",
                        source_type="PM_QUALITY_LOOKBACK_WINDOW",
                        source_id="pmq_30d_20260512",
                        source_version="2026.05",
                    )
                ],
            },
        }
    )
    return DpmPmOperatingQualityPolicy.model_validate(payload)


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


def _source_ref(*, source_version: str = "2026-05-12") -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="PM_QUALITY_TEST_SOURCE",
        source_id="pm-quality-test-source",
        source_version=source_version,
    )


def _ready_score_run(
    *,
    pm_id: str = "pm_001",
    score: Decimal = Decimal("90"),
    policy_id: str = "pmq_sg_dpm",
    policy_version: str = "2026.05",
    as_of_date: str = "2026-05-12",
    state: str = "READY",
) -> DpmPmOperatingQualityScoreRun:
    score_run = build_pm_operating_quality_score_run(
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=_enabled_policy(),
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="OUTCOME_DISCIPLINE",
                evidence_state="READY",
                score=score,
                source_system="lotus-performance",
                source_type="PM_OUTCOME_DISCIPLINE",
                source_id=f"{pm_id}-outcome",
                source_refs=[_source_ref()],
            ),
            DpmPmQualityEvidenceItem(
                indicator="SOURCE_QUALITY",
                evidence_state="READY",
                score=score,
                source_system="lotus-risk",
                source_type="PM_SOURCE_QUALITY",
                source_id=f"{pm_id}-source",
                source_refs=[_source_ref()],
            ),
            DpmPmQualityEvidenceItem(
                indicator="EVIDENCE_COMPLETENESS",
                evidence_state="READY",
                score=score,
                source_system="lotus-manage",
                source_type="PM_EVIDENCE_COMPLETENESS",
                source_id=f"{pm_id}-evidence",
                source_refs=[_source_ref()],
            ),
        ],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id=f"corr-{pm_id}",
    )
    return score_run.model_copy(
        update={
            "policy_id": policy_id,
            "policy_version": policy_version,
            "as_of_date": as_of_date,
            "state": state,
            "score": None if state in {"DISABLED", "BLOCKED"} else score,
        }
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


def test_pm_quality_review_action_records_bounded_target_evidence() -> None:
    score_run = _ready_score_run()

    action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="REQUEST_EVIDENCE_REMEDIATION",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Evidence remediation requested before supervisory closure.",
        actor_id="ops",
        source_refs=[
            DpmOutcomeSourceRef(
                source_system="bank-governance",
                source_type="PM_QUALITY_REVIEW_MINUTES",
                source_id="pmq-review-minutes-001",
            )
        ],
        remediation_due_date="2026-06-15",
        correlation_id="corr-review-action",
    )

    assert action.product_name == "PmOperatingQualityReviewAction"
    assert action.review_action_id.startswith("pmq_review_")
    assert action.target_type == "SCORE_RUN"
    assert action.target_id == score_run.score_run_id
    assert action.target_content_hash == score_run.content_hash
    assert action.action_state == "REVIEW_REQUIRED"
    assert action.reason_codes == [
        "PM_QUALITY_REVIEW_ACTION_REQUEST_EVIDENCE_REMEDIATION",
        "PM_QUALITY_REVIEW_ACTION_STATE_REVIEW_REQUIRED",
    ]
    assert any(ref.source_type == "PmOperatingQualityScoreRun" for ref in action.source_refs)
    assert "NO_APPROVAL_WORKFLOW" in action.operating_boundaries
    assert "NO_SCORE_RECALCULATION" in action.operating_boundaries
    assert action.approval_workflow_boundary.boundary_id == (
        "PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY"
    )
    assert action.approval_workflow_boundary.supportability_state == "BLOCKED"
    assert action.approval_workflow_boundary.approval_workflow_projected is False
    assert action.approval_workflow_boundary.trade_approval_projected is False
    assert "cio_approval_workflow" in action.approval_workflow_boundary.blocked_capabilities
    assert action.approval_workflow_boundary.required_source_product == (
        "PmQualityApprovalWorkflowRecord:v1"
    )
    assert action.approval_workflow_boundary.content_hash.startswith("sha256:")
    assert "compensation_decision" in action.forbidden_uses

    with pytest.raises(ValueError, match="PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH"):
        build_pm_quality_review_action(
            target=score_run,
            target_type="FAIRNESS_ANALYSIS",
            action_type="ACKNOWLEDGE",
            review_action_ref="PMQ-REVIEW-2026-05-002",
            review_reason="Mismatched target type.",
            actor_id="ops",
            source_refs=[],
            remediation_due_date=None,
            correlation_id="corr-review-action-mismatch",
        )


def test_pm_quality_summary_invocation_records_history_without_summary_text() -> None:
    score_run = _ready_score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )

    invocation = build_pm_quality_summary_invocation(
        score_run=score_run,
        review_action=review_action,
        invocation_state="COMPLETED",
        summary_ref="PMQ-SUMMARY-2026-05-001",
        workflow_pack_name="pm_quality_summary.pack",
        workflow_pack_version="v1",
        workflow_run_id="pmq-summary-run-001",
        summary_artifact_ref="pmq-summary-artifact-001",
        summary_content_hash="sha256:pmq-summary",
        requested_by="ops",
        source_refs=[],
        correlation_id="corr-summary",
    )

    assert invocation.product_name == "PmOperatingQualitySummaryInvocation"
    assert invocation.summary_invocation_id.startswith("pmq_summary_")
    assert invocation.score_run_id == score_run.score_run_id
    assert invocation.review_action_id == review_action.review_action_id
    assert invocation.reason_codes == [
        "PM_QUALITY_SUMMARY_INVOCATION_COMPLETED",
        "PM_QUALITY_SUMMARY_REVIEW_GATED",
        "PM_QUALITY_SUMMARY_HISTORY_NO_TEXT_STORED",
    ]
    assert any(ref.source_type == "PmOperatingQualityScoreRun" for ref in invocation.source_refs)
    assert any(
        ref.source_type == "PmOperatingQualityReviewAction" for ref in invocation.source_refs
    )
    assert "NO_SUMMARY_TEXT_STORAGE" in invocation.operating_boundaries
    assert "NO_SUMMARY_TEXT_EXPOSURE" in invocation.operating_boundaries
    assert "NO_DOWNSTREAM_SUMMARY_UX_CLAIM" in invocation.operating_boundaries
    assert invocation.summary_text_boundary.boundary_id == "PM_QUALITY_SUMMARY_TEXT_BOUNDARY"
    assert invocation.summary_text_boundary.supportability_state == "BLOCKED"
    assert invocation.summary_text_boundary.summary_text_stored is False
    assert invocation.summary_text_boundary.summary_text_exposed is False
    assert invocation.summary_text_boundary.downstream_ux_projected is False
    assert "downstream_summary_ux" in invocation.summary_text_boundary.blocked_capabilities
    assert invocation.summary_text_boundary.required_source_product == (
        "PmQualityGeneratedSummaryArtifact:v1"
    )
    assert invocation.summary_text_boundary.content_hash.startswith("sha256:")
    assert "summary_text_storage" in invocation.forbidden_uses

    with pytest.raises(ValueError, match="PM_QUALITY_SUMMARY_REVIEW_ACTION_TARGET_MISMATCH"):
        build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action.model_copy(update={"target_id": "other"}),
            invocation_state="REQUESTED",
            summary_ref="PMQ-SUMMARY-2026-05-002",
            requested_by="ops",
            source_refs=[],
            correlation_id="corr-summary-mismatch",
        )

    with pytest.raises(ValueError, match="PM_QUALITY_SUMMARY_REVIEW_ACTION_HASH_MISMATCH"):
        build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action.model_copy(update={"target_content_hash": "sha256:other"}),
            invocation_state="REQUESTED",
            summary_ref="PMQ-SUMMARY-2026-05-003",
            requested_by="ops",
            source_refs=[],
            correlation_id="corr-summary-hash-mismatch",
        )

    with pytest.raises(ValueError, match="PM_QUALITY_SUMMARY_WORKFLOW_PACK_UNSUPPORTED"):
        build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action,
            invocation_state="REQUESTED",
            summary_ref="PMQ-SUMMARY-2026-05-004",
            workflow_pack_name="unsupported.pack",
            requested_by="ops",
            source_refs=[],
            correlation_id="corr-summary-pack-unsupported",
        )

    with pytest.raises(ValueError, match="PM_QUALITY_SUMMARY_CONTENT_HASH_INVALID"):
        build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action,
            invocation_state="REQUESTED",
            summary_ref="PMQ-SUMMARY-2026-05-005",
            summary_content_hash="not-a-sha256-hash",
            requested_by="ops",
            source_refs=[],
            correlation_id="corr-summary-invalid-hash",
        )


def test_pm_quality_summary_invocation_source_ref_helpers_project_managed_and_ai_refs() -> None:
    score_run = _ready_score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )
    caller_ref = DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="PmOperatingQualityScoreRun",
        source_id=score_run.score_run_id,
        source_version="duplicate",
    )

    refs = summary_history._summary_invocation_source_refs(
        score_run=score_run,
        review_action=review_action,
        workflow_pack_version="v1",
        workflow_run_id=" pmq-summary-run-001 ",
        summary_artifact_ref=" pmq-summary-artifact-001 ",
        summary_content_hash="sha256:pmq-summary",
        source_refs=[caller_ref],
    )

    assert [ref.source_type for ref in refs] == [
        "PM_QUALITY_SUMMARY_ARTIFACT",
        "pm_quality_summary.pack",
        "PmOperatingQualityReviewAction",
        "PmOperatingQualityScoreRun",
    ]
    assert refs[0].source_id == "pmq-summary-artifact-001"
    assert refs[1].source_id == "pmq-summary-run-001"
    assert refs[3].source_version == "duplicate"


def test_pm_quality_summary_invocation_validation_helpers_classify_guardrails() -> None:
    score_run = _ready_score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )

    assert not summary_history._summary_review_action_target_mismatched(
        score_run=score_run,
        review_action=review_action,
    )
    assert summary_history._summary_review_action_target_mismatched(
        score_run=score_run,
        review_action=review_action.model_copy(update={"target_id": "other"}),
    )
    assert summary_history._summary_content_hash_invalid(None) is False
    assert summary_history._summary_content_hash_invalid("sha256:summary") is False
    assert summary_history._summary_content_hash_invalid("not-a-sha256-hash") is True


def test_pm_quality_summary_invocation_validation_checks_preserve_error_order() -> None:
    score_run = _ready_score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    ).model_copy(
        update={
            "target_id": "other",
            "target_content_hash": "sha256:other",
        }
    )

    checks = summary_history._summary_invocation_validation_checks(
        score_run=score_run,
        review_action=review_action,
        workflow_pack_name="unsupported.pack",
        summary_content_hash="not-a-sha256-hash",
    )

    assert [error_code for failed, error_code in checks if failed] == [
        "PM_QUALITY_SUMMARY_REVIEW_ACTION_TARGET_MISMATCH",
        "PM_QUALITY_SUMMARY_REVIEW_ACTION_HASH_MISMATCH",
        "PM_QUALITY_SUMMARY_WORKFLOW_PACK_UNSUPPORTED",
        "PM_QUALITY_SUMMARY_CONTENT_HASH_INVALID",
    ]


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


def test_pm_quality_outcome_review_signal_helpers_project_review_source_posture() -> None:
    review = _review()
    review_ref = scoring._outcome_review_ref(review)

    discipline = scoring._outcome_discipline_signal(review=review, review_ref=review_ref)
    source_quality = scoring._outcome_source_quality_signal(review=review, review_ref=review_ref)

    assert discipline is not None
    assert discipline.indicator == "OUTCOME_DISCIPLINE"
    assert discipline.state == review.state
    assert discipline.as_of_date == review.review_window.as_of_date
    assert discipline.source_refs == [review_ref]
    assert discipline.reason_codes == sorted(
        {result.reason_code for result in review.dimension_results}
    )

    assert source_quality.indicator == "SOURCE_QUALITY"
    assert source_quality.state == review.supportability.state
    assert source_quality.reason_codes == review.supportability.reason_codes
    assert source_quality.source_refs == [review_ref, *review.source_lineage]


def test_pm_quality_outcome_review_signal_helpers_handle_missing_handoff_evidence() -> None:
    review = _review().model_copy(
        update={
            "supportability": _review().supportability.model_copy(update={"reason_codes": []}),
            "report_input_ref": None,
            "ai_evidence_ref": None,
        }
    )
    review_ref = scoring._outcome_review_ref(review)

    assert scoring._outcome_handoff_refs(review) == []
    assert scoring._outcome_handoff_evidence_signal(review=review, review_ref=review_ref) is None
    assert scoring._outcome_source_quality_signal(
        review=review, review_ref=review_ref
    ).reason_codes == ["OUTCOME_REVIEW_SOURCE_POSTURE"]


def test_pm_quality_outcome_review_signal_helpers_project_handoff_evidence() -> None:
    report_ref = DpmOutcomeSourceRef(
        source_system="lotus-report",
        source_type="DPM_OUTCOME_REPORT_INPUT",
        source_id="report_001",
        content_hash="sha256:report",
    )
    ai_ref = DpmOutcomeSourceRef(
        source_system="lotus-ai",
        source_type="DPM_OUTCOME_AI_EVIDENCE_INPUT",
        source_id="ai_001",
        content_hash="sha256:ai",
    )
    review = _review().model_copy(
        update={
            "report_input_ref": report_ref,
            "ai_evidence_ref": ai_ref,
        }
    )
    review_ref = scoring._outcome_review_ref(review)

    handoff = scoring._outcome_handoff_evidence_signal(review=review, review_ref=review_ref)

    assert scoring._outcome_handoff_refs(review) == [report_ref, ai_ref]
    assert handoff is not None
    assert handoff.indicator == "EVIDENCE_COMPLETENESS"
    assert handoff.score == Decimal("100")
    assert handoff.state == "READY"
    assert handoff.reason_codes == ["OUTCOME_REVIEW_HANDOFF_EVIDENCE_AVAILABLE"]
    assert handoff.source_refs == [review_ref, report_ref, ai_ref]


def test_pm_quality_score_run_source_ref_helper_collects_scope_and_governance_refs() -> None:
    indicator_ref = DpmOutcomeSourceRef(
        source_system="lotus-risk",
        source_type="PM_SOURCE_QUALITY",
        source_id="risk-source-001",
    )
    book_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id="book-scope-001",
    )
    governance_ref = DpmOutcomeSourceRef(
        source_system="bank-governance",
        source_type="PM_QUALITY_POLICY_APPROVAL",
        source_id="PMQ-APPROVAL-2026-05",
    )
    indicator_result = DpmPmQualityIndicatorResult(
        indicator="SOURCE_QUALITY",
        score=Decimal("91"),
        weight=Decimal("100"),
        state="READY",
        evidence_count=1,
        reason_codes=["SOURCE_READY"],
        source_refs=[indicator_ref, book_ref],
    )
    book_scope = DpmPmQualityBookScopeEvidence(
        source_id="book-scope-001",
        product_version="v1",
        supportability_state="READY",
        returned_portfolio_count=1,
        source_refs=[book_ref],
    )
    scope_evidence = scoring._scope_evidence_from_policy(_scope_policy())
    governance_evidence = scoring._governance_evidence(
        policy=_enabled_policy(),
        as_of_date="2026-05-12",
        generated_by="ops",
    ).model_copy(update={"source_refs": [governance_ref]})

    refs = scoring._score_run_source_refs(
        indicator_results=[indicator_result],
        book_scope_evidence=book_scope,
        scope_evidence=scope_evidence,
        governance_evidence=governance_evidence,
    )

    assert [ref.source_type for ref in refs] == [
        "PM_QUALITY_LOOKBACK_WINDOW",
        "PM_QUALITY_POLICY_APPROVAL",
        "PM_QUALITY_PEER_GROUP_DEFINITION",
        "PortfolioManagerBookMembership",
        "PM_SOURCE_QUALITY",
    ]
    assert len([ref for ref in refs if ref.source_id == "book-scope-001"]) == 1


def test_pm_quality_score_run_hash_payload_serializes_optional_materialization() -> None:
    indicator_ref = DpmOutcomeSourceRef(
        source_system="lotus-risk",
        source_type="PM_SOURCE_QUALITY",
        source_id="risk-source-001",
    )
    indicator_result = DpmPmQualityIndicatorResult(
        indicator="SOURCE_QUALITY",
        score=Decimal("91"),
        weight=Decimal("100"),
        state="READY",
        evidence_count=1,
        reason_codes=["SOURCE_READY"],
        source_refs=[indicator_ref],
    )

    payload = scoring._score_run_hash_payload(
        pm_id="pm_001",
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=_enabled_policy(),
        state="READY",
        score=Decimal("91.00"),
        indicator_results=[indicator_result],
        book_scope_evidence=None,
        scope_evidence=None,
        governance_evidence=None,
        reason_codes=["PM_QUALITY_WITHIN_POLICY"],
        source_refs=[indicator_ref],
    )

    assert payload["score"] == "91.00"
    assert payload["book_scope_evidence"] is None
    assert payload["scope_evidence"] is None
    assert payload["governance_evidence"] is None
    assert payload["indicator_results"][0]["score"] == "91"
    assert payload["source_refs"] == [indicator_ref.model_dump(mode="json")]


def test_pm_operating_quality_materializes_peer_group_and_lookback_scope() -> None:
    score_run = build_pm_operating_quality_score_run(
        pm_id="pm_001",
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=_scope_policy(),
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="OUTCOME_DISCIPLINE",
                evidence_state="READY",
                score=Decimal("92"),
                source_system="lotus-performance",
                source_type="PM_OUTCOME_DISCIPLINE",
                source_id="pm_outcome_001",
                source_refs=[
                    DpmOutcomeSourceRef(
                        source_system="lotus-performance",
                        source_type="PM_OUTCOME_DISCIPLINE",
                        source_id="pm_outcome_001",
                        source_version="2026-05-10",
                    )
                ],
            ),
            DpmPmQualityEvidenceItem(
                indicator="SOURCE_QUALITY",
                evidence_state="READY",
                score=Decimal("88"),
                source_system="lotus-risk",
                source_type="PM_SOURCE_QUALITY",
                source_id="pm_source_001",
                source_refs=[
                    DpmOutcomeSourceRef(
                        source_system="lotus-risk",
                        source_type="PM_SOURCE_QUALITY",
                        source_id="pm_source_001",
                        source_version="2026-05-11",
                    )
                ],
            ),
            DpmPmQualityEvidenceItem(
                indicator="EVIDENCE_COMPLETENESS",
                evidence_state="READY",
                score=Decimal("90"),
                source_system="lotus-manage",
                source_type="PM_EVIDENCE_COMPLETENESS",
                source_id="pm_evidence_001",
                source_refs=[
                    DpmOutcomeSourceRef(
                        source_system="lotus-manage",
                        source_type="PM_EVIDENCE_COMPLETENESS",
                        source_id="pm_evidence_001",
                        source_version="2026-05-12",
                    )
                ],
            ),
        ],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id="corr-scope-001",
    )

    assert score_run.scope_evidence is not None
    assert score_run.scope_evidence.peer_group_id == "sg_dpm_balanced"
    assert score_run.scope_evidence.minimum_peer_count == 3
    assert score_run.scope_evidence.lookback_window_id == "pmq_30d_20260512"
    assert score_run.scope_evidence.reason_codes == [
        "PM_QUALITY_PEER_GROUP_MATERIALIZED",
        "PM_QUALITY_LOOKBACK_WINDOW_MATERIALIZED",
    ]
    assert any(
        ref.source_type == "PM_QUALITY_PEER_GROUP_DEFINITION" for ref in score_run.source_refs
    )
    assert any(ref.source_type == "PM_QUALITY_LOOKBACK_WINDOW" for ref in score_run.source_refs)


def test_pm_operating_quality_scope_projection_helpers_materialize_policy_scope() -> None:
    policy = _scope_policy()
    peer_group = policy.peer_group_policy
    lookback = policy.lookback_window_policy

    peer_group_fields = scoring._peer_group_scope_fields(peer_group)
    lookback_fields = scoring._lookback_scope_fields(lookback)

    assert peer_group_fields.peer_group_id == "sg_dpm_balanced"
    assert peer_group_fields.minimum_peer_count == 3
    assert lookback_fields.window_id == "pmq_30d_20260512"
    assert lookback_fields.timezone == "Asia/Singapore"
    assert scoring._scope_reason_codes(peer_group=peer_group, lookback=lookback) == [
        "PM_QUALITY_PEER_GROUP_MATERIALIZED",
        "PM_QUALITY_LOOKBACK_WINDOW_MATERIALIZED",
    ]
    assert [
        ref.source_type for ref in scoring._scope_source_refs(peer_group=peer_group, lookback=None)
    ] == ["PM_QUALITY_PEER_GROUP_DEFINITION"]


def test_pm_operating_quality_scope_projection_helpers_handle_empty_scope() -> None:
    peer_group_fields = scoring._peer_group_scope_fields(None)
    lookback_fields = scoring._lookback_scope_fields(None)

    assert peer_group_fields.peer_group_id is None
    assert peer_group_fields.minimum_peer_count is None
    assert lookback_fields.window_id is None
    assert lookback_fields.timezone is None
    assert scoring._scope_reason_codes(peer_group=None, lookback=None) == []
    assert scoring._scope_source_refs(peer_group=None, lookback=None) == []


def test_pm_operating_quality_lookback_window_fails_closed_for_stale_evidence() -> None:
    with pytest.raises(
        scoring.DpmPmQualityValidationError, match="PM_QUALITY_EVIDENCE_OUTSIDE_LOOKBACK_WINDOW"
    ):
        build_pm_operating_quality_score_run(
            pm_id="pm_001",
            book_id="sg_dpm_book",
            as_of_date="2026-05-12",
            policy=_scope_policy(),
            evidence_items=[
                DpmPmQualityEvidenceItem(
                    indicator="OUTCOME_DISCIPLINE",
                    evidence_state="READY",
                    score=Decimal("92"),
                    source_system="lotus-performance",
                    source_type="PM_OUTCOME_DISCIPLINE",
                    source_id="pm_outcome_stale",
                    source_refs=[
                        DpmOutcomeSourceRef(
                            source_system="lotus-performance",
                            source_type="PM_OUTCOME_DISCIPLINE",
                            source_id="pm_outcome_stale",
                            source_version="2026-04-01",
                        )
                    ],
                )
            ],
            outcome_reviews=[],
            generated_by="ops",
            correlation_id="corr-scope-stale",
        )


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
    with pytest.raises(ValueError, match="prohibited use"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_bad_normalized_use",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("100"))],
            governance_approval=_governance_approval(),
            allowed_uses=["portfolio_management_review", " HR "],
        )


def test_pm_quality_scope_policy_models_reject_unproven_or_invalid_scope() -> None:
    with pytest.raises(ValueError, match="PM_QUALITY_PEER_GROUP_ID_REQUIRED"):
        DpmPmQualityPeerGroupPolicy(
            peer_group_id=" ",
            display_name="Singapore DPM balanced mandates",
            segment_type="MANDATE_TYPE",
            source_refs=[_source_ref()],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_PEER_GROUP_DISPLAY_NAME_REQUIRED"):
        DpmPmQualityPeerGroupPolicy(
            peer_group_id="sg_dpm_balanced",
            display_name=" ",
            segment_type="MANDATE_TYPE",
            source_refs=[_source_ref()],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_PEER_GROUP_SOURCE_REFS_REQUIRED"):
        DpmPmQualityPeerGroupPolicy(
            peer_group_id="sg_dpm_balanced",
            display_name="Singapore DPM balanced mandates",
            segment_type="MANDATE_TYPE",
            source_refs=[],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_LOOKBACK_WINDOW_ID_REQUIRED"):
        DpmPmQualityLookbackWindowPolicy(
            window_id=" ",
            start_date="2026-04-13",
            end_date="2026-05-12",
            source_refs=[_source_ref()],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_LOOKBACK_WINDOW_DATE_INVALID"):
        DpmPmQualityLookbackWindowPolicy(
            window_id="pmq_30d_20260512",
            start_date="not-a-date",
            end_date="2026-05-12",
            source_refs=[_source_ref()],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_LOOKBACK_WINDOW_RANGE_INVALID"):
        DpmPmQualityLookbackWindowPolicy(
            window_id="pmq_30d_20260512",
            start_date="2026-05-13",
            end_date="2026-05-12",
            source_refs=[_source_ref()],
        )
    with pytest.raises(ValueError, match="PM_QUALITY_LOOKBACK_WINDOW_SOURCE_REFS_REQUIRED"):
        DpmPmQualityLookbackWindowPolicy(
            window_id="pmq_30d_20260512",
            start_date="2026-04-13",
            end_date="2026-05-12",
            source_refs=[],
        )


def test_pm_quality_policy_model_rejects_threshold_weight_and_indicator_edges() -> None:
    with pytest.raises(ValueError, match="ready_threshold"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_bad_threshold",
            policy_version="2026.05",
            enabled=False,
            as_of_date="2026-05-12",
            ready_threshold=Decimal("70"),
            watch_threshold=Decimal("80"),
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
        )
    with pytest.raises(ValueError, match="at least one configured weight"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_no_weights",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[],
            governance_approval=_governance_approval(),
        )
    with pytest.raises(ValueError, match="PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_missing_governance",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("100"))],
            governance_approval=None,
        )
    with pytest.raises(ValueError, match="indicators must be unique"):
        DpmPmOperatingQualityPolicy(
            policy_id="pmq_duplicate_weight",
            policy_version="2026.05",
            enabled=True,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
            weights=[
                DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("50")),
                DpmPmQualityWeight(indicator="OUTCOME_DISCIPLINE", weight=Decimal("50")),
            ],
            governance_approval=_governance_approval(),
        )


def test_pm_quality_lookback_window_requires_dated_valid_evidence() -> None:
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED",
    ):
        build_pm_operating_quality_score_run(
            pm_id="pm_001",
            book_id="sg_dpm_book",
            as_of_date="2026-05-12",
            policy=_scope_policy(),
            evidence_items=[
                DpmPmQualityEvidenceItem(
                    indicator="OUTCOME_DISCIPLINE",
                    evidence_state="READY",
                    score=Decimal("92"),
                    source_system="lotus-performance",
                    source_type="PM_OUTCOME_DISCIPLINE",
                    source_id="pm_outcome_undated",
                )
            ],
            outcome_reviews=[],
            generated_by="ops",
            correlation_id="corr-undated-lookback",
        )
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_EVIDENCE_AS_OF_DATE_INVALID",
    ):
        scoring._validate_lookback_window(
            policy=_scope_policy(),
            signals=[
                scoring._PmQualitySignal(
                    indicator="OUTCOME_DISCIPLINE",
                    score=Decimal("92"),
                    state="READY",
                    reason_codes=["PM_OUTCOME_DISCIPLINE_SOURCE_SIGNAL"],
                    source_refs=[_source_ref()],
                    as_of_date="not-a-date",
                )
            ],
        )
    invalid_policy = _enabled_policy().model_copy(
        update={
            "lookback_window_policy": DpmPmQualityLookbackWindowPolicy.model_construct(
                window_id="pmq_invalid",
                start_date="not-a-date",
                end_date="2026-05-12",
                timezone="UTC",
                source_refs=[_source_ref()],
            )
        }
    )
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_LOOKBACK_WINDOW_DATE_INVALID",
    ):
        scoring._validate_lookback_window(
            policy=invalid_policy,
            signals=[
                scoring._PmQualitySignal(
                    indicator="OUTCOME_DISCIPLINE",
                    score=Decimal("92"),
                    state="READY",
                    reason_codes=["PM_OUTCOME_DISCIPLINE_SOURCE_SIGNAL"],
                    source_refs=[_source_ref()],
                    as_of_date="2026-05-12",
                )
            ],
        )


def test_pm_quality_lookback_window_helpers_parse_source_dates_and_boundaries() -> None:
    lookback = DpmPmQualityLookbackWindowPolicy(
        window_id="pmq_30d_20260512",
        start_date="2026-04-13",
        end_date="2026-05-12",
        timezone="UTC",
        source_refs=[_source_ref()],
    )
    signal = scoring._PmQualitySignal(
        indicator="OUTCOME_DISCIPLINE",
        score=Decimal("92"),
        state="READY",
        reason_codes=["PM_OUTCOME_DISCIPLINE_SOURCE_SIGNAL"],
        source_refs=[_source_ref()],
        as_of_date="2026-05-12",
    )

    assert scoring._lookback_window_dates(lookback) == (
        date(2026, 4, 13),
        date(2026, 5, 12),
    )
    assert scoring._signal_as_of_business_date(signal) == date(2026, 5, 12)
    assert scoring._date_in_inclusive_window(
        date(2026, 4, 13),
        date(2026, 4, 13),
        date(2026, 5, 12),
    )
    assert not scoring._date_in_inclusive_window(
        date(2026, 5, 13),
        date(2026, 4, 13),
        date(2026, 5, 12),
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
    assert scoring._worst_state(["READY", "PENDING_REVIEW", "DISABLED"]) == "PENDING_REVIEW"
    assert scoring._worst_state(["READY", "NOT_SUPPORTED"]) == "READY"
    assert scoring._worst_state(["NOT_SUPPORTED"]) == "DEGRADED"
    assert scoring._worst_state(["UNKNOWN"]) == "DEGRADED"
    assert scoring._mean([]) == Decimal("0")


def test_pm_quality_fairness_analysis_rejects_invalid_inputs() -> None:
    segment = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_balanced",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM balanced mandates",
        score_runs=[_ready_score_run()],
        source_refs=[_source_ref()],
    )

    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_FAIRNESS_SEGMENTS_REQUIRED"):
        build_pm_operating_quality_fairness_analysis(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[segment],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("10"),
            generated_by="ops",
            correlation_id="corr-fairness-invalid-segments",
        )
    with pytest.raises(
        DpmPmQualityValidationError, match="PM_QUALITY_FAIRNESS_MINIMUM_COUNT_INVALID"
    ):
        build_pm_operating_quality_fairness_analysis(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[segment, segment],
            minimum_segment_score_run_count=0,
            maximum_average_score_spread=Decimal("10"),
            generated_by="ops",
            correlation_id="corr-fairness-invalid-count",
        )
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_FAIRNESS_SPREAD_THRESHOLD_INVALID",
    ):
        build_pm_operating_quality_fairness_analysis(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[segment, segment],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("101"),
            generated_by="ops",
            correlation_id="corr-fairness-invalid-spread",
        )


def _fairness_segment_result(
    *,
    segment_id: str,
    state: str,
    average_score: Decimal | None,
    reason_codes: list[str],
) -> DpmPmQualityFairnessSegmentResult:
    return DpmPmQualityFairnessSegmentResult(
        segment_id=segment_id,
        segment_type="MANDATE_TYPE",
        display_name=segment_id,
        state=state,
        score_run_count=1 if average_score is not None else 0,
        average_score=average_score,
        minimum_score=average_score,
        maximum_score=average_score,
        reason_codes=reason_codes,
        score_run_refs=[],
        source_refs=[_source_ref()],
    )


def test_fairness_analysis_input_helper_rejects_invalid_thresholds() -> None:
    segment = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_balanced",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM balanced mandates",
        score_runs=[_ready_score_run()],
        source_refs=[_source_ref()],
    )

    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_FAIRNESS_SEGMENTS_REQUIRED"):
        scoring._validate_fairness_analysis_inputs(
            segments=[segment],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("10"),
        )
    with pytest.raises(
        DpmPmQualityValidationError, match="PM_QUALITY_FAIRNESS_MINIMUM_COUNT_INVALID"
    ):
        scoring._validate_fairness_analysis_inputs(
            segments=[segment, segment],
            minimum_segment_score_run_count=0,
            maximum_average_score_spread=Decimal("10"),
        )


def test_fairness_analysis_posture_helper_classifies_blocked_pending_and_ready() -> None:
    blocked = scoring._fairness_analysis_posture(
        segment_results=[
            _fairness_segment_result(
                segment_id="blocked",
                state="BLOCKED",
                average_score=None,
                reason_codes=["PM_QUALITY_FAIRNESS_POLICY_MISMATCH"],
            ),
            _fairness_segment_result(
                segment_id="ready",
                state="READY",
                average_score=Decimal("90"),
                reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_READY"],
            ),
        ],
        maximum_average_score_spread=Decimal("10"),
    )
    pending = scoring._fairness_analysis_posture(
        segment_results=[
            _fairness_segment_result(
                segment_id="a",
                state="READY",
                average_score=Decimal("95"),
                reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_READY"],
            ),
            _fairness_segment_result(
                segment_id="b",
                state="READY",
                average_score=Decimal("80"),
                reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_READY"],
            ),
        ],
        maximum_average_score_spread=Decimal("10"),
    )
    ready = scoring._fairness_analysis_posture(
        segment_results=[
            _fairness_segment_result(
                segment_id="a",
                state="READY",
                average_score=Decimal("95"),
                reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_READY"],
            ),
            _fairness_segment_result(
                segment_id="b",
                state="READY",
                average_score=Decimal("80"),
                reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_READY"],
            ),
        ],
        maximum_average_score_spread=Decimal("20"),
    )

    assert blocked.state == "BLOCKED"
    assert "PM_QUALITY_FAIRNESS_SEGMENT_BLOCKED" in blocked.reason_codes
    assert pending.state == "PENDING_REVIEW"
    assert pending.observed_spread == Decimal("15.00")
    assert ready.state == "READY"
    assert ready.reason_codes == ["PM_QUALITY_FAIRNESS_WITHIN_GOVERNED_SPREAD"]


def test_pm_quality_fairness_analysis_classifies_blocked_pending_and_ready_postures() -> None:
    segment_a = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_balanced_a",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM balanced mandates A",
        score_runs=[_ready_score_run(pm_id="pm_a", score=Decimal("95"))],
        source_refs=[_source_ref()],
    )
    segment_b = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_balanced_b",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM balanced mandates B",
        score_runs=[_ready_score_run(pm_id="pm_b", score=Decimal("80"))],
        source_refs=[_source_ref()],
    )
    mismatch_segment = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_balanced_mismatch",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM balanced mismatched policy",
        score_runs=[
            _ready_score_run(
                pm_id="pm_mismatch",
                policy_id="pmq_other",
                as_of_date="2026-05-11",
                state="BLOCKED",
            )
        ],
        source_refs=[_source_ref()],
    )

    blocked = build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[segment_a, mismatch_segment],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("10"),
        generated_by="ops",
        correlation_id="corr-fairness-blocked",
    )
    pending = build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[segment_a, segment_b],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("10"),
        generated_by="ops",
        correlation_id="corr-fairness-pending",
    )
    ready = build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[segment_a, segment_b],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("20"),
        generated_by="ops",
        correlation_id="corr-fairness-ready",
    )

    assert blocked.state == "BLOCKED"
    assert "PM_QUALITY_FAIRNESS_POLICY_MISMATCH" in blocked.reason_codes
    assert "PM_QUALITY_FAIRNESS_AS_OF_DATE_MISMATCH" in blocked.reason_codes
    assert "PM_QUALITY_FAIRNESS_SCORE_RUN_NOT_SCORABLE" in blocked.reason_codes
    assert pending.state == "PENDING_REVIEW"
    assert pending.observed_average_score_spread == Decimal("15.00")
    assert pending.reason_codes == ["PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED"]
    assert ready.state == "READY"
    assert ready.reason_codes == ["PM_QUALITY_FAIRNESS_WITHIN_GOVERNED_SPREAD"]

    action = build_pm_quality_review_action(
        target=ready,
        target_type="FAIRNESS_ANALYSIS",
        action_type="ESCALATE_MODEL_RISK_REVIEW",
        review_action_ref="PMQ-FAIRNESS-REVIEW-2026-05-001",
        review_reason="Escalate fairness spread evidence for model-risk review.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-fairness-review",
    )
    assert action.target_id == ready.fairness_analysis_id

    with pytest.raises(ValueError, match="PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH"):
        build_pm_quality_review_action(
            target=ready,
            target_type="SCORE_RUN",
            action_type="ACKNOWLEDGE",
            review_action_ref="PMQ-FAIRNESS-REVIEW-2026-05-002",
            review_reason="Mismatched fairness target type.",
            actor_id="ops",
            source_refs=[],
            remediation_due_date=None,
            correlation_id="corr-fairness-review-mismatch",
        )


def test_pm_quality_score_run_scope_mismatch_helpers_classify_fairness_inputs() -> None:
    ready = _ready_score_run()
    policy_mismatch = _ready_score_run(policy_id="pmq_other")
    date_mismatch = _ready_score_run(as_of_date="2026-05-11")
    blocked = _ready_score_run(state="BLOCKED")

    assert not scoring._score_run_policy_mismatched(
        score_run=ready,
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
    )
    assert scoring._score_run_policy_mismatched(
        score_run=policy_mismatch,
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
    )
    assert scoring._score_run_as_of_date_mismatched(
        score_run=date_mismatch,
        as_of_date="2026-05-12",
    )
    assert scoring._score_run_not_scorable(blocked)
    assert not scoring._score_run_not_scorable(ready)


def test_pm_quality_score_run_scope_mismatch_reasons_deduplicate_failures() -> None:
    reasons = scoring._score_run_scope_mismatch_reasons(
        score_runs=[
            _ready_score_run(policy_id="pmq_other"),
            _ready_score_run(as_of_date="2026-05-11"),
            _ready_score_run(state="BLOCKED"),
            _ready_score_run(state="DISABLED"),
        ],
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
    )

    assert reasons == [
        "PM_QUALITY_FAIRNESS_AS_OF_DATE_MISMATCH",
        "PM_QUALITY_FAIRNESS_POLICY_MISMATCH",
        "PM_QUALITY_FAIRNESS_SCORE_RUN_NOT_SCORABLE",
    ]


def test_pm_quality_fairness_analysis_blocks_segments_below_minimum_count() -> None:
    empty_segment = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_empty",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM empty segment",
        score_runs=[],
        source_refs=[_source_ref()],
    )
    ready_segment = DpmPmQualityFairnessSegmentInput(
        segment_id="sg_dpm_ready",
        segment_type="MANDATE_TYPE",
        display_name="Singapore DPM ready segment",
        score_runs=[_ready_score_run(pm_id="pm_ready", score=Decimal("90"))],
        source_refs=[_source_ref()],
    )

    analysis = build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[empty_segment, ready_segment],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("10"),
        generated_by="ops",
        correlation_id="corr-fairness-minimum",
    )

    assert analysis.state == "BLOCKED"
    assert "PM_QUALITY_FAIRNESS_SEGMENT_MINIMUM_COUNT_NOT_MET" in analysis.reason_codes


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


def test_pm_quality_governance_expiry_helper_projects_active_posture() -> None:
    active = scoring._governance_expiry_evaluation(
        expires_on="2026-06-30",
        as_of_date="2026-05-12",
    )
    no_expiry = scoring._governance_expiry_evaluation(
        expires_on=None,
        as_of_date="2026-05-12",
    )

    assert active.expires_on == "2026-06-30"
    assert active.reason_codes == ["PM_QUALITY_GOVERNANCE_ACTIVE"]
    assert no_expiry.expires_on is None
    assert no_expiry.reason_codes == []


def test_pm_quality_governance_expiry_helper_rejects_invalid_or_expired_dates() -> None:
    with pytest.raises(
        DpmPmQualityValidationError,
        match="PM_QUALITY_GOVERNANCE_EXPIRY_DATE_INVALID",
    ):
        scoring._governance_expiry_evaluation(
            expires_on="not-a-date",
            as_of_date="2026-05-12",
        )

    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_GOVERNANCE_EXPIRED"):
        scoring._governance_expiry_evaluation(
            expires_on="2026-05-01",
            as_of_date="2026-05-12",
        )


def test_pm_quality_actor_entitlement_helper_projects_authorization_state() -> None:
    authorized = scoring._actor_entitlement_evaluation(
        entitled_actor_ids=[" ops ", ""],
        generated_by="ops",
    )
    not_supplied = scoring._actor_entitlement_evaluation(
        entitled_actor_ids=[],
        generated_by="ops",
    )

    assert authorized.state == "AUTHORIZED"
    assert authorized.reason_codes == ["PM_QUALITY_ACTOR_AUTHORIZED"]
    assert not_supplied.state == "NOT_SUPPLIED"
    assert not_supplied.reason_codes == []

    with pytest.raises(DpmPmQualityValidationError, match="PM_QUALITY_ACTOR_NOT_ENTITLED"):
        scoring._actor_entitlement_evaluation(
            entitled_actor_ids=["ops"],
            generated_by="unauthorized",
        )
