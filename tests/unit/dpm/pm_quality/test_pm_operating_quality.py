from decimal import Decimal

import pytest

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessSegmentInput,
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
