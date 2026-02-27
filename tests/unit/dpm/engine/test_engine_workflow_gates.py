from decimal import Decimal
from typing import Literal

from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.models import (
    DiagnosticsData,
    EngineOptions,
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
    issue = SuitabilityIssue(
        issue_id="SUIT_ISSUER_MAX",
        issue_key="ISSUER_MAX|X",
        dimension="ISSUER",
        severity="HIGH",
        status_change="NEW",
        summary="Issuer concentration exceeded",
        details={},
        evidence=SuitabilityEvidence(
            as_of="md_1",
            snapshot_ids=SuitabilityEvidenceSnapshotIds(
                portfolio_snapshot_id="pf_1",
                market_data_snapshot_id="md_1",
            ),
        ),
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


def test_workflow_gate_blocked_dominates() -> None:
    gate = evaluate_gate_decision(
        status="BLOCKED",
        rule_results=[_rule("INSUFFICIENT_CASH", "HARD")],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(),
        default_requires_client_consent=False,
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
        default_requires_client_consent=True,
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
        default_requires_client_consent=False,
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
        default_requires_client_consent=False,
    )
    assert gate.gate == "EXECUTION_READY"
    assert gate.recommended_next_step == "EXECUTE"


def test_workflow_gate_execution_ready_when_client_consent_already_obtained() -> None:
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=_diagnostics(),
        options=EngineOptions(client_consent_already_obtained=True),
        default_requires_client_consent=True,
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
        default_requires_client_consent=False,
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
