"""Run-state, diagnostics, and policy proof-pack section builders."""

from typing import Any

from src.core.construction.models import ConstructionAlternative
from src.core.models import RebalanceResult, RuleResult
from src.core.proof_packs.models import ProofPackSectionState, ProofPackSectionType

SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]


def run_state_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
) -> SectionPayload | None:
    if section_type == "before_state":
        return (
            "READY",
            "Before-state summary captured from source run artifact.",
            {"before_summary": result.before.model_dump(mode="json")},
            {"position_count": len(result.before.positions)},
            [],
        )
    if section_type == "target_state":
        return (
            "READY",
            "Target state captured from source run target trace.",
            {"target_id": result.target.target_id},
            {"target_count": len(result.target.targets)},
            [],
        )
    if section_type == "trade_intents":
        return trade_intents_section_payload(result)
    if section_type == "after_state":
        return after_state_section_payload(result)
    return None


def trade_intents_section_payload(
    result: RebalanceResult,
) -> SectionPayload:
    if not result.intents:
        return (
            "BLOCKED",
            "No trade intents are available for pre-trade proof.",
            {"intent_ids": []},
            {"trade_count": 0},
            ["DPM_TRADE_INTENTS_MISSING"],
        )
    return (
        "READY",
        "Trade intents captured from source run.",
        {"intent_ids": [intent.intent_id for intent in result.intents]},
        {"trade_count": len(result.intents)},
        [],
    )


def after_state_section_payload(
    result: RebalanceResult,
) -> SectionPayload:
    blocked = result.status == "BLOCKED"
    return (
        "BLOCKED" if blocked else "READY",
        "After-state simulation summary captured from source run.",
        {"after_summary": result.after_simulated.model_dump(mode="json")},
        {"position_count": len(result.after_simulated.positions)},
        ["DPM_AFTER_STATE_BLOCKED"] if blocked else [],
    )


def run_diagnostics_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
) -> SectionPayload | None:
    if section_type == "liquidity_and_cash":
        return liquidity_and_cash_section_payload(result)
    if section_type == "fx_funding_plan":
        return fx_funding_plan_section_payload(result)
    if section_type == "currency_overlay_evidence":
        return currency_overlay_evidence_section_payload()
    return None


def liquidity_and_cash_section_payload(result: RebalanceResult) -> SectionPayload:
    breaches = result.diagnostics.cash_ladder_breaches
    return (
        "BLOCKED" if breaches else "READY",
        "Liquidity and cash posture captured from run diagnostics.",
        {
            "cash_ladder": [
                item.model_dump(mode="json") for item in result.diagnostics.cash_ladder
            ],
            "cash_ladder_breaches": [item.model_dump(mode="json") for item in breaches],
        },
        {"breach_count": len(breaches)},
        ["DPM_CASH_LADDER_BREACH"] if breaches else [],
    )


def fx_funding_plan_section_payload(result: RebalanceResult) -> SectionPayload:
    missing_pairs = result.diagnostics.missing_fx_pairs
    return (
        "BLOCKED" if missing_pairs else "READY",
        "FX funding posture captured from run diagnostics.",
        {
            "funding_plan": [
                item.model_dump(mode="json") for item in result.diagnostics.funding_plan
            ],
            "missing_fx_pairs": missing_pairs,
        },
        {"missing_fx_pair_count": len(missing_pairs)},
        ["DPM_REQUIRED_FX_PAIR_MISSING"] if missing_pairs else [],
    )


def currency_overlay_evidence_section_payload() -> SectionPayload:
    return (
        "DEGRADED",
        "Currency-overlay authority context is not attached.",
        {},
        {},
        ["DPM_CURRENCY_OVERLAY_CONTEXT_MISSING"],
    )


def run_policy_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    selected_alternative: ConstructionAlternative | None,
) -> SectionPayload | None:
    if section_type == "drift_impact":
        return drift_impact_section_payload(selected_alternative=selected_alternative)
    if section_type == "tax_impact":
        return tax_impact_section_payload(result=result)
    if section_type == "rule_results":
        return rule_results_section_payload(result=result)
    return None


def drift_impact_section_payload(
    *, selected_alternative: ConstructionAlternative | None
) -> SectionPayload:
    if selected_alternative is None:
        return (
            "DEGRADED",
            "Direct-run proof has no construction comparison drift trace.",
            {},
            {},
            ["DPM_DRIFT_COMPARISON_UNAVAILABLE"],
        )
    return (
        "READY",
        "Drift impact captured from construction comparison metrics.",
        {},
        selected_alternative.comparison_metrics.model_dump(mode="json"),
        [],
    )


def tax_impact_section_payload(*, result: RebalanceResult) -> SectionPayload:
    if result.tax_impact is None:
        return (
            "DEGRADED",
            "Tax impact is not available for this run.",
            {},
            {},
            ["DPM_TAX_IMPACT_MISSING"],
        )
    return (
        "READY",
        "Tax impact captured from manage tax-aware simulation.",
        result.tax_impact.model_dump(mode="json"),
        {},
        [],
    )


def rule_results_section_payload(*, result: RebalanceResult) -> SectionPayload:
    failed = failed_rule_results(result)
    return (
        rule_results_section_state(failed),
        "Rule results captured from manage policy engine.",
        {"rule_results": [rule.model_dump(mode="json") for rule in result.rule_results]},
        rule_results_metrics(failed),
        rule_results_reason_codes(failed),
    )


def failed_rule_results(result: RebalanceResult) -> list[RuleResult]:
    return [rule for rule in result.rule_results if rule.status == "FAIL"]


def rule_results_section_state(failed_rules: list[RuleResult]) -> ProofPackSectionState:
    return "BLOCKED" if any(rule.severity == "HARD" for rule in failed_rules) else "READY"


def rule_results_metrics(failed_rules: list[RuleResult]) -> dict[str, int]:
    return {"fail_count": len(failed_rules)}


def rule_results_reason_codes(failed_rules: list[RuleResult]) -> list[str]:
    return [rule.reason_code for rule in failed_rules]
