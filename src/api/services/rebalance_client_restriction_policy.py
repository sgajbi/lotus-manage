"""Qualify mechanical simulations against source-owned hard client policy."""

from __future__ import annotations

from typing import Literal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
)
from src.api.services.construction_client_restriction_supportability import (
    active_applicable_restrictions,
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_matches_intent,
    shelf_entries_by_instrument,
    violated_client_restrictions,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.construction.models import AuthoritativeClientRestrictionRule
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import (
    ClientRestrictionPolicyEvidence,
    GateDecision,
    GateDecisionSummary,
    GateReason,
    RebalanceResult,
    SecurityTradeIntent,
)


def _rule_ref(rule: AuthoritativeClientRestrictionRule, *, side: str, instrument_id: str) -> str:
    return ":".join(
        (
            rule.restriction_code,
            str(rule.restriction_version),
            rule.source_record_id or "no-record-id",
            side,
            instrument_id,
        )
    )


def _policy_gate(result: RebalanceResult, *, reason_code: str, blocked: bool) -> GateDecision:
    existing = result.gate_decision
    summary = (
        existing.summary
        if existing is not None
        else GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        )
    )
    reasons = list(existing.reasons) if existing is not None else []
    reasons.append(
        GateReason(
            reason_code=reason_code,
            severity="HIGH",
            source="CLIENT_POLICY",
        )
    )
    if blocked or (existing is not None and existing.gate == "BLOCKED"):
        gate: Literal["BLOCKED", "COMPLIANCE_REVIEW_REQUIRED"] = "BLOCKED"
        next_step: Literal["FIX_INPUT", "COMPLIANCE_REVIEW"] = "FIX_INPUT"
    else:
        gate, next_step = "COMPLIANCE_REVIEW_REQUIRED", "COMPLIANCE_REVIEW"
    return GateDecision(
        gate=gate,
        recommended_next_step=next_step,
        reasons=reasons,
        summary=summary.model_copy(
            update={"hard_fail_count": summary.hard_fail_count + (1 if blocked else 0)}
        ),
    )


def apply_client_restriction_policy(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    source_context: DpmResolvedSourceContext | None,
) -> RebalanceResult:
    if source_context is None:
        evidence = ClientRestrictionPolicyEvidence(
            decision="NOT_ASSESSED",
            reason_codes=["CLIENT_RESTRICTION_RAW_COUNTERFACTUAL"],
        )
        return result.model_copy(
            update={
                "client_restriction_policy": evidence,
                "gate_decision": _policy_gate(
                    result, reason_code="CLIENT_RESTRICTION_RAW_COUNTERFACTUAL", blocked=False
                ),
            }
        )

    profile = source_context.context.client_restriction_profile
    if profile is None:
        evidence = ClientRestrictionPolicyEvidence(
            decision="PENDING_REVIEW",
            reason_codes=["CLIENT_RESTRICTION_PROFILE_UNAVAILABLE"],
            stateful_context_hash=source_context.stateful_context_hash,
        )
        return result.model_copy(
            update={
                "status": "BLOCKED" if result.status == "BLOCKED" else "PENDING_REVIEW",
                "client_restriction_policy": evidence,
                "gate_decision": _policy_gate(
                    result, reason_code="CLIENT_RESTRICTION_PROFILE_UNAVAILABLE", blocked=False
                ),
            }
        )

    context = client_restriction_profile_context(profile)
    violations = violated_client_restrictions(request=request, result=result, context=context)
    shelf_by_instrument = shelf_entries_by_instrument(request=request)
    active_refs = sorted(
        {
            _rule_ref(rule, side=intent.side, instrument_id=intent.instrument_id)
            for intent in result.intents
            if isinstance(intent, SecurityTradeIntent)
            for rule in active_applicable_restrictions(
                restrictions=context.restrictions,
                trade_side=intent.side,
                as_of_date=context.as_of_date,
            )
            if restriction_matches_intent(
                intent=intent,
                shelf=shelf_by_instrument.get(intent.instrument_id),
                restriction=rule,
            )
        }
    )
    status = client_restriction_status(request=request, result=result, context=context)
    decision: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = (
        "BLOCKED"
        if status == ConstructionMethodStatus.BLOCKED
        else "READY"
        if status == ConstructionMethodStatus.READY
        else "PENDING_REVIEW"
    )
    reason_codes = client_restriction_reason_codes(request=request, result=result, context=context)
    evidence = ClientRestrictionPolicyEvidence(
        decision=decision,
        reason_codes=reason_codes,
        source_system=context.source_system,
        source_product_name=context.source_product_name,
        source_product_version=context.source_product_version,
        source_id=context.source_id,
        content_hash=context.content_hash,
        stateful_context_hash=source_context.stateful_context_hash,
        portfolio_id=context.portfolio_id,
        client_id=context.client_id,
        mandate_id=context.mandate_id,
        as_of_date=context.as_of_date,
        applicable_rule_refs=active_refs,
        violated_rule_refs=sorted(
            {
                _rule_ref(rule, side=intent.side, instrument_id=intent.instrument_id)
                for intent, rule in violations
            }
        ),
    )
    if decision == "READY":
        return result.model_copy(update={"client_restriction_policy": evidence})
    blocked = decision == "BLOCKED"
    gate_reason = next(
        (code for code in reason_codes if code.startswith("CLIENT_RESTRICTION_VIOLATION_")),
        next((code for code in reason_codes if code.startswith("MISSING_")), None),
    ) or next(
        (code for code in reason_codes if code.startswith("CLIENT_RESTRICTION_PROFILE_")),
        "CLIENT_RESTRICTION_PROFILE_UNASSESSED",
    )
    return result.model_copy(
        update={
            "status": "BLOCKED" if blocked or result.status == "BLOCKED" else "PENDING_REVIEW",
            "client_restriction_policy": evidence,
            "gate_decision": _policy_gate(
                result,
                reason_code=gate_reason,
                blocked=blocked,
            ),
        }
    )


__all__ = ["apply_client_restriction_policy"]
