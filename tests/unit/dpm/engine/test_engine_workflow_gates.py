from decimal import Decimal
from typing import Literal

from src.core.common.workflow_gates import (
    _select_gate_route,
    _sorted_gate_reasons,
    _suitability_issue_reason,
    _suitability_reasons,
    evaluate_gate_decision,
)
from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GateReason,
    RuleResult,
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SuitabilityIssue,
    SuitabilityResult,
    SuitabilitySummary,
)


def _rule(
    rule_id: str,
    severity: Literal["HARD", "SOFT", "INFO"],
    status: Literal["PASS", "FAIL"] = "FAIL",
    reason_code: str = "X",
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        severity=severity,
        status=status,
        measured=Decimal("1"),
        threshold={"max": Decimal("0")},
        reason_code=reason_code,
    )


def _diagnostics(
    *,
    price_missing: list[str] | None = None,
    fx_missing: list[str] | None = None,
) -> DiagnosticsData:
    return DiagnosticsData(
        data_quality={
            "price_missing": price_missing or [],
            "fx_missing": fx_missing or [],
        }
    )


def _high_suitability_result() -> SuitabilityResult:
    issue = _suitability_issue(
        issue_id="SUIT_ISSUER_MAX",
        issue_key="ISSUER_MAX|X",
        dimension="ISSUER",
        severity="HIGH",
        status_change="NEW",
    )
    return SuitabilityResult(
        summary=SuitabilitySummary(
            new_count=1,
            resolved_count=0,
            persistent_count=0,
            highest_severity_new="HIGH",
        ),
        issues=[issue],
        recommended_gate="COMPLIANCE_REVIEW",
    )


def _suitability_issue(
    *,
    issue_id: str,
    issue_key: str,
    dimension: Literal[
        "CONCENTRATION",
        "ISSUER",
        "LIQUIDITY",
        "GOVERNANCE",
        "CASH",
        "DATA_QUALITY",
    ],
    severity: Literal["LOW", "MEDIUM", "HIGH"],
    status_change: Literal["NEW", "PERSISTENT", "RESOLVED"],
) -> SuitabilityIssue:
    return SuitabilityIssue(
        issue_id=issue_id,
        issue_key=issue_key,
        dimension=dimension,
        severity=severity,
        status_change=status_change,
        summary=f"{dimension} suitability issue",
        details={},
        evidence=SuitabilityEvidence(
            as_of="md_1",
            snapshot_ids=SuitabilityEvidenceSnapshotIds(
                portfolio_snapshot_id="pf_1",
                market_data_snapshot_id="md_1",
            ),
        ),
    )


def test_suitability_issue_reason_maps_new_high_and_medium_issues() -> None:
    high_reason = _suitability_issue_reason(
        _suitability_issue(
            issue_id="SUIT_HIGH",
            issue_key="ISSUER_MAX|X",
            dimension="ISSUER",
            severity="HIGH",
            status_change="NEW",
        )
    )
    medium_reason = _suitability_issue_reason(
        _suitability_issue(
            issue_id="SUIT_MEDIUM",
            issue_key="CONCENTRATION_MAX|Y",
            dimension="CONCENTRATION",
            severity="MEDIUM",
            status_change="NEW",
        )
    )

    assert high_reason is not None
    assert high_reason.reason.reason_code == "NEW_HIGH_SUITABILITY_ISSUE"
    assert high_reason.high_count == 1
    assert high_reason.medium_count == 0
    assert medium_reason is not None
    assert medium_reason.reason.reason_code == "NEW_MEDIUM_SUITABILITY_ISSUE"
    assert medium_reason.high_count == 0
    assert medium_reason.medium_count == 1


def test_suitability_issue_reason_ignores_non_new_or_low_issues() -> None:
    assert (
        _suitability_issue_reason(
            _suitability_issue(
                issue_id="SUIT_PERSISTENT",
                issue_key="ISSUER_MAX|X",
                dimension="ISSUER",
                severity="HIGH",
                status_change="PERSISTENT",
            )
        )
        is None
    )
    assert (
        _suitability_issue_reason(
            _suitability_issue(
                issue_id="SUIT_LOW",
                issue_key="MIN_TRADE|Z",
                dimension="LIQUIDITY",
                severity="LOW",
                status_change="NEW",
            )
        )
        is None
    )


def test_suitability_reasons_aggregates_new_issue_counts() -> None:
    reasons, new_high, new_medium = _suitability_reasons(
        SuitabilityResult(
            summary=SuitabilitySummary(
                new_count=3,
                resolved_count=0,
                persistent_count=1,
                highest_severity_new="HIGH",
            ),
            issues=[
                _suitability_issue(
                    issue_id="SUIT_HIGH",
                    issue_key="ISSUER_MAX|X",
                    dimension="ISSUER",
                    severity="HIGH",
                    status_change="NEW",
                ),
                _suitability_issue(
                    issue_id="SUIT_MEDIUM",
                    issue_key="CONCENTRATION_MAX|Y",
                    dimension="CONCENTRATION",
                    severity="MEDIUM",
                    status_change="NEW",
                ),
                _suitability_issue(
                    issue_id="SUIT_PERSISTENT",
                    issue_key="ISSUER_MAX|X",
                    dimension="ISSUER",
                    severity="HIGH",
                    status_change="PERSISTENT",
                ),
            ],
            recommended_gate="COMPLIANCE_REVIEW",
        )
    )

    assert [reason.reason_code for reason in reasons] == [
        "NEW_HIGH_SUITABILITY_ISSUE",
        "NEW_MEDIUM_SUITABILITY_ISSUE",
    ]
    assert new_high == 1
    assert new_medium == 1


def test_workflow_gate_blocked_dominates() -> None:
    gate = evaluate_gate_decision(
        status="BLOCKED",
        rule_results=[_rule("INSUFFICIENT_CASH", "HARD")],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )
    assert gate.gate == "BLOCKED"
    assert gate.recommended_next_step == "FIX_INPUT"


def test_workflow_gate_compliance_for_new_high_suitability() -> None:
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=_high_suitability_result(),
        diagnostics=_diagnostics(),
        options=EngineOptions(),
        default_requires_mandate_approval=True,
    )
    assert gate.gate == "COMPLIANCE_REVIEW_REQUIRED"
    assert gate.recommended_next_step == "COMPLIANCE_REVIEW"


def test_workflow_gate_risk_for_soft_fail() -> None:
    gate = evaluate_gate_decision(
        status="PENDING_REVIEW",
        rule_results=[_rule("CASH_BAND", "SOFT")],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )
    assert gate.gate == "RISK_REVIEW_REQUIRED"
    assert gate.recommended_next_step == "RISK_REVIEW"


def test_workflow_gate_execution_ready_for_clean_dpm() -> None:
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )
    assert gate.gate == "EXECUTION_READY"
    assert gate.recommended_next_step == "EXECUTE"


def test_workflow_gate_execution_ready_when_mandate_approval_already_obtained() -> None:
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(mandate_approval_already_obtained=True),
        default_requires_mandate_approval=True,
    )
    assert gate.gate == "EXECUTION_READY"
    assert gate.recommended_next_step == "EXECUTE"


def test_workflow_gate_prioritizes_data_quality_in_reason_sorting() -> None:
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[_rule("CASH_BAND", "SOFT", reason_code="SOFT_CASH_BAND")],
        suitability=_high_suitability_result(),
        diagnostics=_diagnostics(price_missing=["A"], fx_missing=["USD/SGD"]),
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )
    assert gate.gate == "COMPLIANCE_REVIEW_REQUIRED"
    assert gate.summary.hard_fail_count == 0
    assert gate.summary.soft_fail_count == 1
    assert gate.summary.new_high_suitability_count == 1
    assert gate.summary.new_medium_suitability_count == 0
    assert [reason.reason_code for reason in gate.reasons[:2]] == [
        "DATA_QUALITY_MISSING_FX",
        "DATA_QUALITY_MISSING_PRICE",
    ]


def test_select_gate_route_preserves_decision_precedence() -> None:
    assert _select_gate_route(
        status="BLOCKED",
        hard_fail_count=0,
        soft_fail_count=0,
        new_high=1,
        new_medium=1,
        options=EngineOptions(),
        requires_mandate_approval=True,
    ) == ("BLOCKED", "FIX_INPUT")
    assert _select_gate_route(
        status="READY",
        hard_fail_count=0,
        soft_fail_count=0,
        new_high=1,
        new_medium=1,
        options=EngineOptions(),
        requires_mandate_approval=True,
    ) == ("COMPLIANCE_REVIEW_REQUIRED", "COMPLIANCE_REVIEW")
    assert _select_gate_route(
        status="READY",
        hard_fail_count=0,
        soft_fail_count=1,
        new_high=0,
        new_medium=1,
        options=EngineOptions(),
        requires_mandate_approval=True,
    ) == ("RISK_REVIEW_REQUIRED", "RISK_REVIEW")
    assert _select_gate_route(
        status="READY",
        hard_fail_count=0,
        soft_fail_count=0,
        new_high=0,
        new_medium=0,
        options=EngineOptions(mandate_approval_already_obtained=True),
        requires_mandate_approval=True,
    ) == ("EXECUTION_READY", "EXECUTE")
    assert _select_gate_route(
        status="READY",
        hard_fail_count=0,
        soft_fail_count=0,
        new_high=0,
        new_medium=0,
        options=EngineOptions(),
        requires_mandate_approval=True,
    ) == ("MANDATE_APPROVAL_REQUIRED", "REQUEST_MANDATE_APPROVAL")
    assert _select_gate_route(
        status="READY",
        hard_fail_count=0,
        soft_fail_count=0,
        new_high=0,
        new_medium=0,
        options=EngineOptions(),
        requires_mandate_approval=False,
    ) == ("EXECUTION_READY", "EXECUTE")


def test_sorted_gate_reasons_orders_by_severity_source_code_and_detail() -> None:
    reasons = [
        GateReason(
            reason_code="SOFT_RULE_FAIL:CASH",
            severity="MEDIUM",
            source="RULE_ENGINE",
            details={"reason_code": "CASH"},
        ),
        GateReason(
            reason_code="NEW_HIGH_SUITABILITY_ISSUE",
            severity="HIGH",
            source="SUITABILITY",
            details={"issue_key": "B"},
        ),
        GateReason(
            reason_code="DATA_QUALITY_MISSING_PRICE",
            severity="HIGH",
            source="DATA_QUALITY",
            details={"count": "1"},
        ),
    ]

    assert [reason.reason_code for reason in _sorted_gate_reasons(reasons)] == [
        "DATA_QUALITY_MISSING_PRICE",
        "NEW_HIGH_SUITABILITY_ISSUE",
        "SOFT_RULE_FAIL:CASH",
    ]
