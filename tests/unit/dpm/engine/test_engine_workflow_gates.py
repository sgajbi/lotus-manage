from types import SimpleNamespace

from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.models import EngineOptions, RuleResult


def _rule(rule_id: str, severity: str, status: str = "FAIL", reason_code: str = "X"):
    return RuleResult(
        rule_id=rule_id,
        severity=severity,
        status=status,
        measured="1",
        threshold={"max": "0"},
        reason_code=reason_code,
    )


def test_workflow_gate_blocked_dominates():
    gate = evaluate_gate_decision(
        status="BLOCKED",
        rule_results=[_rule("INSUFFICIENT_CASH", "HARD")],
        suitability=None,
        diagnostics=SimpleNamespace(data_quality={"price_missing": [], "fx_missing": []}),
        options=EngineOptions(),
        default_requires_client_consent=False,
    )
    assert gate.gate == "BLOCKED"
    assert gate.recommended_next_step == "FIX_INPUT"


def test_workflow_gate_compliance_for_new_high_suitability():
    high_issue = SimpleNamespace(
        status_change="NEW",
        severity="HIGH",
        issue_id="SUIT_ISSUER_MAX",
        issue_key="ISSUER_MAX|X",
    )
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=SimpleNamespace(issues=[high_issue]),
        diagnostics=SimpleNamespace(data_quality={"price_missing": [], "fx_missing": []}),
        options=EngineOptions(),
        default_requires_client_consent=True,
    )
    assert gate.gate == "COMPLIANCE_REVIEW_REQUIRED"
    assert gate.recommended_next_step == "COMPLIANCE_REVIEW"


def test_workflow_gate_risk_for_soft_fail():
    gate = evaluate_gate_decision(
        status="PENDING_REVIEW",
        rule_results=[_rule("CASH_BAND", "SOFT")],
        suitability=None,
        diagnostics=SimpleNamespace(data_quality={"price_missing": [], "fx_missing": []}),
        options=EngineOptions(),
        default_requires_client_consent=False,
    )
    assert gate.gate == "RISK_REVIEW_REQUIRED"
    assert gate.recommended_next_step == "RISK_REVIEW"


def test_workflow_gate_execution_ready_for_clean_dpm():
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=SimpleNamespace(data_quality={"price_missing": [], "fx_missing": []}),
        options=EngineOptions(),
        default_requires_client_consent=False,
    )
    assert gate.gate == "EXECUTION_READY"
    assert gate.recommended_next_step == "EXECUTE"


def test_workflow_gate_execution_ready_when_client_consent_already_obtained():
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=SimpleNamespace(data_quality={"price_missing": [], "fx_missing": []}),
        options=EngineOptions(client_consent_already_obtained=True),
        default_requires_client_consent=True,
    )
    assert gate.gate == "EXECUTION_READY"
    assert gate.recommended_next_step == "EXECUTE"


def test_workflow_gate_prioritizes_data_quality_in_reason_sorting():
    high_issue = SimpleNamespace(
        status_change="NEW",
        severity="HIGH",
        issue_id="SUIT_ISSUER_MAX",
        issue_key="ISSUER_MAX|X",
    )
    gate = evaluate_gate_decision(
        status="READY",
        rule_results=[_rule("CASH_BAND", "SOFT", reason_code="SOFT_CASH_BAND")],
        suitability=SimpleNamespace(issues=[high_issue]),
        diagnostics=SimpleNamespace(data_quality={"price_missing": ["A"], "fx_missing": ["USD/SGD"]}),
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
