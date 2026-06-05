from collections.abc import Iterable
from typing import Literal

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GateDecision,
    GateDecisionSummary,
    GateReason,
    RuleResult,
    SuitabilityResult,
)

_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

_GateName = Literal[
    "BLOCKED",
    "RISK_REVIEW_REQUIRED",
    "COMPLIANCE_REVIEW_REQUIRED",
    "MANDATE_APPROVAL_REQUIRED",
    "EXECUTION_READY",
    "NONE",
]
_NextStep = Literal[
    "FIX_INPUT",
    "RISK_REVIEW",
    "COMPLIANCE_REVIEW",
    "REQUEST_MANDATE_APPROVAL",
    "EXECUTE",
    "NONE",
]


def _dq_reasons(diagnostics: DiagnosticsData | None) -> list[GateReason]:
    dq = (
        diagnostics.data_quality
        if diagnostics is not None
        else {"price_missing": [], "fx_missing": []}
    )
    reasons: list[GateReason] = []
    if dq.get("price_missing"):
        reasons.append(
            GateReason(
                reason_code="DATA_QUALITY_MISSING_PRICE",
                severity="HIGH",
                source="DATA_QUALITY",
                details={"count": str(len(dq["price_missing"]))},
            )
        )
    if dq.get("fx_missing"):
        reasons.append(
            GateReason(
                reason_code="DATA_QUALITY_MISSING_FX",
                severity="HIGH",
                source="DATA_QUALITY",
                details={"count": str(len(dq["fx_missing"]))},
            )
        )
    return reasons


def _rule_reasons(rule_results: Iterable[RuleResult]) -> tuple[list[GateReason], int, int]:
    reasons: list[GateReason] = []
    hard_fail_count = 0
    soft_fail_count = 0
    for rule in rule_results:
        if rule.status != "FAIL":
            continue
        if rule.severity == "HARD":
            hard_fail_count += 1
            reasons.append(
                GateReason(
                    reason_code=f"HARD_RULE_FAIL:{rule.rule_id}",
                    severity="HIGH",
                    source="RULE_ENGINE",
                    details={"reason_code": rule.reason_code},
                )
            )
        elif rule.severity == "SOFT":
            soft_fail_count += 1
            reasons.append(
                GateReason(
                    reason_code=f"SOFT_RULE_FAIL:{rule.rule_id}",
                    severity="MEDIUM",
                    source="RULE_ENGINE",
                    details={"reason_code": rule.reason_code},
                )
            )
    return reasons, hard_fail_count, soft_fail_count


def _suitability_reasons(
    suitability: SuitabilityResult | None,
) -> tuple[list[GateReason], int, int]:
    if suitability is None:
        return [], 0, 0
    reasons: list[GateReason] = []
    new_high = 0
    new_medium = 0
    for issue in suitability.issues:
        if issue.status_change != "NEW":
            continue
        if issue.severity == "HIGH":
            new_high += 1
            reasons.append(
                GateReason(
                    reason_code="NEW_HIGH_SUITABILITY_ISSUE",
                    severity="HIGH",
                    source="SUITABILITY",
                    details={"issue_id": issue.issue_id, "issue_key": issue.issue_key},
                )
            )
        elif issue.severity == "MEDIUM":
            new_medium += 1
            reasons.append(
                GateReason(
                    reason_code="NEW_MEDIUM_SUITABILITY_ISSUE",
                    severity="MEDIUM",
                    source="SUITABILITY",
                    details={"issue_id": issue.issue_id, "issue_key": issue.issue_key},
                )
            )
    return reasons, new_high, new_medium


def evaluate_gate_decision(
    *,
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    rule_results: Iterable[RuleResult],
    suitability: SuitabilityResult | None,
    diagnostics: DiagnosticsData | None,
    options: EngineOptions,
    default_requires_mandate_approval: bool,
) -> GateDecision:
    reasons, hard_fail_count, soft_fail_count = _rule_reasons(rule_results)
    dq_reasons = _dq_reasons(diagnostics)
    suitability_reasons, new_high, new_medium = _suitability_reasons(suitability)
    reasons.extend(suitability_reasons)
    reasons.extend(dq_reasons)

    requires_mandate_approval = (
        options.workflow_requires_mandate_approval or default_requires_mandate_approval
    )

    gate, next_step = _select_gate_route(
        status=status,
        hard_fail_count=hard_fail_count,
        soft_fail_count=soft_fail_count,
        new_high=new_high,
        new_medium=new_medium,
        options=options,
        requires_mandate_approval=requires_mandate_approval,
    )
    reasons = _sorted_gate_reasons(reasons)
    return GateDecision(
        gate=gate,
        recommended_next_step=next_step,
        reasons=reasons,
        summary=GateDecisionSummary(
            hard_fail_count=hard_fail_count,
            soft_fail_count=soft_fail_count,
            new_high_suitability_count=new_high,
            new_medium_suitability_count=new_medium,
        ),
    )


def _select_gate_route(
    *,
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    hard_fail_count: int,
    soft_fail_count: int,
    new_high: int,
    new_medium: int,
    options: EngineOptions,
    requires_mandate_approval: bool,
) -> tuple[_GateName, _NextStep]:
    if status == "BLOCKED" or hard_fail_count > 0:
        return "BLOCKED", "FIX_INPUT"
    if new_high > 0:
        return "COMPLIANCE_REVIEW_REQUIRED", "COMPLIANCE_REVIEW"
    if soft_fail_count > 0 or new_medium > 0:
        return "RISK_REVIEW_REQUIRED", "RISK_REVIEW"
    if options.mandate_approval_already_obtained:
        return "EXECUTION_READY", "EXECUTE"
    if requires_mandate_approval:
        return "MANDATE_APPROVAL_REQUIRED", "REQUEST_MANDATE_APPROVAL"
    return "EXECUTION_READY", "EXECUTE"


def _sorted_gate_reasons(reasons: list[GateReason]) -> list[GateReason]:
    return sorted(
        reasons,
        key=lambda reason: (
            _SEVERITY_ORDER[reason.severity],
            reason.source,
            reason.reason_code,
            reason.details.get("issue_key", reason.details.get("reason_code", "")),
        ),
    )
