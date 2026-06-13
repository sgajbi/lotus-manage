"""Pure RFC-0040 proof-pack builders."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.models import (
    AuthoritativeRegimeStressContext,
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackDecisionSummary,
    DpmProofPackDecisionTimeline,
    DpmProofPackDecisionTimelineEvent,
    DpmProofPackEvidenceRef,
    DpmProofPackSection,
    DpmProofPackSourceRef,
    DpmProofPackSupportability,
    ProofPackSectionState,
    ProofPackSectionType,
    ProofPackSourceType,
    ProofPackStatus,
)
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
    source_analytics_for_alternative,
    source_analytics_for_context,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.rebalance_runs.artifact import build_dpm_run_artifact
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from src.core.models import GateDecision, RebalanceResult

PROOF_PACK_VERSION = "1.0"

_SECTION_TITLES: dict[ProofPackSectionType, str] = {
    "decision_summary": "Decision Summary",
    "mandate_context": "Mandate Context",
    "source_readiness": "Source Readiness",
    "before_state": "Before State",
    "target_state": "Target State",
    "selected_alternative": "Selected Alternative",
    "trade_intents": "Trade Intents",
    "after_state": "After State",
    "drift_impact": "Drift Impact",
    "risk_impact": "Risk Impact",
    "performance_context": "Performance Context",
    "tax_impact": "Tax Impact",
    "turnover_and_cost": "Turnover and Cost",
    "liquidity_and_cash": "Liquidity and Cash",
    "fx_funding_plan": "FX Funding Plan",
    "currency_overlay_evidence": "Currency Overlay Evidence",
    "scenario_and_regime_evidence": "Scenario and Regime Evidence",
    "eligibility_and_restrictions": "Eligibility and Restrictions",
    "sustainability_controls": "Sustainability Controls",
    "rule_results": "Rule Results",
    "approval_requirements": "Approval Requirements",
    "operations_handoff": "Operations Handoff",
    "decision_timeline": "Decision Timeline",
    "lineage": "Lineage",
    "supportability": "Supportability",
    "reporting_refs": "Reporting References",
    "ai_refs": "AI Evidence References",
}


def proof_pack_id_for_rebalance_run(*, rebalance_run_id: str) -> str:
    return rebalance_run_id.replace("rr_", "dpp_", 1)


def proof_pack_id_for_selected_alternative(
    *, alternative_set_id: str, selected_alternative_id: str
) -> str:
    return f"dpp_{alternative_set_id}_{selected_alternative_id}"


_SECTION_ORDER: list[ProofPackSectionType] = list(_SECTION_TITLES)


class ProofPackSourceValidationError(ValueError):
    pass


_SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]

_PreRunSourceAnalyticsConfig = tuple[ProofPackAnalyticsFamily, str, str]

_PRE_RUN_SOURCE_ANALYTICS_SECTIONS: dict[ProofPackSectionType, _PreRunSourceAnalyticsConfig] = {
    "risk_impact": (
        "risk",
        "No risk-authoritative enrichment is attached to this first-wave proof pack.",
        "DPM_RISK_AUTHORITY_CONTEXT_MISSING",
    ),
    "performance_context": (
        "performance",
        "No performance-authoritative benchmark context is attached.",
        "DPM_PERFORMANCE_CONTEXT_MISSING",
    ),
    "sustainability_controls": (
        "sustainability_preference",
        "Sustainability preference authority context is not attached.",
        "DPM_SUSTAINABILITY_PREFERENCE_CONTEXT_MISSING",
    ),
}

_PRE_RUN_ADAPTER_SECTIONS: dict[ProofPackSectionType, tuple[str, str]] = {
    "reporting_refs": (
        "Report input adapter is available; generated refs are appended outside the immutable proof-pack body.",
        "DpmProofPackReportInput",
    ),
    "ai_refs": (
        "AI evidence input adapter is available with forbidden-action and forbidden-field guardrails.",
        "DpmProofPackAiEvidenceInput",
    ),
}


@dataclass(frozen=True)
class _ProofPackBuildContext:
    created_at: datetime
    generated_at: str
    result: RebalanceResult | None
    run_artifact_hash: str | None
    source_hashes: dict[str, str]
    source_analytics: dict[str, ProofPackSourceAnalytics]
    source_refs: list[DpmProofPackSourceRef]
    proof_pack_id: str
    portfolio_id: str
    correlation_id: str


def build_proof_pack_from_run(
    *,
    run: DpmRunRecord,
    created_by: str,
    reason: str | None,
    created_at: datetime | None = None,
    correlation_id: str | None = None,
    mandate_id: str | None = None,
    mandate_twin: DpmMandateDigitalTwin | None = None,
    mandate_health: DpmMandateHealthSnapshot | None = None,
    mandate_evidence_gap_codes: list[str] | None = None,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord] | None = None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None = None,
) -> DpmPreTradeProofPack:
    return _build_proof_pack(
        source_type="REBALANCE_RUN",
        run=run,
        alternative_set=None,
        selected_alternative=None,
        selection=None,
        created_by=created_by,
        reason=reason,
        created_at=created_at,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes or [],
        workflow_decisions=workflow_decisions or [],
        direct_regime_stress_context=direct_regime_stress_context,
    )


def build_proof_pack_from_selected_alternative(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative_id: str,
    run: DpmRunRecord | None,
    created_by: str,
    reason: str | None,
    selection: ConstructionAlternativeSelection | None = None,
    created_at: datetime | None = None,
    correlation_id: str | None = None,
    mandate_id: str | None = None,
    mandate_twin: DpmMandateDigitalTwin | None = None,
    mandate_health: DpmMandateHealthSnapshot | None = None,
    mandate_evidence_gap_codes: list[str] | None = None,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord] | None = None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None = None,
) -> DpmPreTradeProofPack:
    selected = _selected_alternative_for_proof_pack(
        alternative_set=alternative_set,
        selected_alternative_id=selected_alternative_id,
        selection=selection,
    )
    return _build_proof_pack(
        source_type="SELECTED_ALTERNATIVE",
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected,
        selection=selection,
        created_by=created_by,
        reason=reason,
        created_at=created_at,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes or [],
        workflow_decisions=workflow_decisions or [],
        direct_regime_stress_context=direct_regime_stress_context,
    )


def _selected_alternative_for_proof_pack(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative_id: str,
    selection: ConstructionAlternativeSelection | None,
) -> ConstructionAlternative:
    selected = next(
        (
            alternative
            for alternative in alternative_set.alternatives
            if alternative.alternative_id == selected_alternative_id
        ),
        None,
    )
    if selected is None:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_NOT_FOUND")
    if selection is not None:
        _validate_selected_alternative_selection(
            alternative_set_id=alternative_set.alternative_set_id,
            selected_alternative_id=selected_alternative_id,
            selection=selection,
        )
    return selected


def _validate_selected_alternative_selection(
    *,
    alternative_set_id: str,
    selected_alternative_id: str,
    selection: ConstructionAlternativeSelection,
) -> None:
    if selection.alternative_id != selected_alternative_id:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_SELECTION_MISMATCH")
    if selection.alternative_set_id != alternative_set_id:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_SET_MISMATCH")


def _build_proof_pack(
    *,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    created_by: str,
    reason: str | None,
    created_at: datetime | None,
    correlation_id: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> DpmPreTradeProofPack:
    context = _proof_pack_build_context(
        source_type=source_type,
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        correlation_id=correlation_id,
        created_at=created_at,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        direct_regime_stress_context=direct_regime_stress_context,
    )

    sections = _proof_pack_sections(
        context=context,
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        reason=reason,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        created_by=created_by,
        workflow_decisions=workflow_decisions,
    )
    supportability = _supportability(sections)
    decision_summary = _decision_summary(
        source_type=source_type,
        result=context.result,
        selected_alternative=selected_alternative,
        reason=reason,
        supportability=supportability,
    )
    timeline = _decision_timeline(
        proof_pack_id=context.proof_pack_id,
        generated_at=context.generated_at,
        source_type=source_type,
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        workflow_decisions=workflow_decisions,
        created_by=created_by,
    )
    section_by_type = {section.section_type: section for section in sections}
    pack = DpmPreTradeProofPack(
        proof_pack_id=context.proof_pack_id,
        proof_pack_version=PROOF_PACK_VERSION,
        portfolio_id=context.portfolio_id,
        mandate_id=mandate_id,
        source_type=source_type,
        rebalance_run_id=run.rebalance_run_id if run is not None else None,
        alternative_set_id=(
            alternative_set.alternative_set_id if alternative_set is not None else None
        ),
        selected_alternative_id=(
            selected_alternative.alternative_id if selected_alternative is not None else None
        ),
        as_of_date=_as_of_date(run=run, alternative_set=alternative_set),
        status=supportability.status,
        decision_summary=decision_summary,
        sections=sections,
        approval_requirements=section_by_type["approval_requirements"],
        operations_handoff=section_by_type["operations_handoff"],
        decision_timeline=timeline,
        lineage=section_by_type["lineage"],
        supportability=supportability,
        content_hash="",
        source_hashes=context.source_hashes,
        created_at=context.created_at,
        created_by=created_by,
        correlation_id=context.correlation_id,
    )
    return _finalize_proof_pack_content_hash(pack)


def _proof_pack_build_context(
    *,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    correlation_id: str | None,
    created_at: datetime | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> _ProofPackBuildContext:
    resolved_created_at = created_at or datetime.now(timezone.utc)
    source_hashes = _source_hashes(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )
    source_analytics = _source_analytics(
        selected_alternative=selected_alternative,
        direct_regime_stress_context=direct_regime_stress_context,
    )
    for analytics in source_analytics.values():
        source_hashes[analytics.source_hash_key] = analytics.content_hash
    source_refs = _source_refs(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        source_hashes=source_hashes,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )
    source_refs.extend(analytics.source_ref for analytics in source_analytics.values())
    run_artifact = build_dpm_run_artifact(run=run) if run is not None else None
    return _ProofPackBuildContext(
        created_at=resolved_created_at,
        generated_at=resolved_created_at.isoformat(),
        result=RebalanceResult.model_validate(run.result_json) if run is not None else None,
        run_artifact_hash=(
            run_artifact.evidence.hashes.artifact_hash if run_artifact is not None else None
        ),
        source_hashes=source_hashes,
        source_analytics=source_analytics,
        source_refs=source_refs,
        proof_pack_id=_proof_pack_id(
            source_type=source_type,
            run=run,
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
        ),
        portfolio_id=_resolve_portfolio_id(run=run, alternative_set=alternative_set),
        correlation_id=_resolve_proof_pack_correlation_id(
            correlation_id=correlation_id,
            selection=selection,
            run=run,
            created_at=resolved_created_at,
        ),
    )


def _resolve_proof_pack_correlation_id(
    *,
    correlation_id: str | None,
    selection: ConstructionAlternativeSelection | None,
    run: DpmRunRecord | None,
    created_at: datetime,
) -> str:
    return next(
        candidate
        for candidate in [
            correlation_id,
            _selection_correlation_id(selection),
            _run_correlation_id(run),
            _generated_proof_pack_correlation_id(created_at),
        ]
        if candidate
    )


def _selection_correlation_id(selection: ConstructionAlternativeSelection | None) -> str | None:
    if selection is None or not selection.correlation_id:
        return None
    return selection.correlation_id


def _run_correlation_id(run: DpmRunRecord | None) -> str | None:
    return run.correlation_id if run is not None else None


def _generated_proof_pack_correlation_id(created_at: datetime) -> str:
    return f"proof-pack-{created_at.strftime('%Y%m%d%H%M%S')}"


def _proof_pack_sections(
    *,
    context: _ProofPackBuildContext,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    reason: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    created_by: str,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[DpmProofPackSection]:
    return [
        _build_section(
            section_type=section_type,
            generated_at=context.generated_at,
            result=context.result,
            run=run,
            run_artifact_hash=context.run_artifact_hash,
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
            source_refs=context.source_refs,
            source_ref_count=len(context.source_refs),
            source_analytics=context.source_analytics,
            reason=reason,
            mandate_id=mandate_id,
            mandate_twin=mandate_twin,
            mandate_health=mandate_health,
            mandate_evidence_gap_codes=mandate_evidence_gap_codes,
            created_by=created_by,
            workflow_decisions=workflow_decisions,
        )
        for section_type in _SECTION_ORDER
    ]


def _finalize_proof_pack_content_hash(pack: DpmPreTradeProofPack) -> DpmPreTradeProofPack:
    payload = pack.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmPreTradeProofPack.model_validate(payload)


def _build_section(
    *,
    section_type: ProofPackSectionType,
    generated_at: str,
    result: RebalanceResult | None,
    run: DpmRunRecord | None,
    run_artifact_hash: str | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    source_refs: list[DpmProofPackSourceRef],
    source_ref_count: int,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    reason: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    created_by: str,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> DpmProofPackSection:
    state, summary, facts, metrics, reason_codes = _section_payload(
        section_type=section_type,
        result=result,
        run=run,
        run_artifact_hash=run_artifact_hash,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        reason=reason,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        created_by=created_by,
        source_ref_count=source_ref_count,
        source_analytics=source_analytics,
        workflow_decisions=workflow_decisions,
    )
    evidence_refs = []
    if run is not None and run_artifact_hash is not None:
        evidence_refs.append(
            DpmProofPackEvidenceRef(
                ref_type="DPM_RUN_ARTIFACT",
                ref_id=run.rebalance_run_id,
                source_system="lotus-manage",
                content_hash=run_artifact_hash,
            )
        )
    payload = DpmProofPackSection(
        section_id=f"{section_type}",
        section_type=section_type,
        state=state,
        title=_SECTION_TITLES[section_type],
        summary=summary,
        facts=facts,
        metrics=metrics,
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
        source_refs=source_refs,
        source_supportability=_source_supportability(
            result=result, alternative_set=alternative_set
        ),
        generated_at=generated_at,
        content_hash="",
    ).model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmProofPackSection.model_validate(payload)


def _source_analytics_section_payload(
    *,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    family: ProofPackAnalyticsFamily,
    missing_summary: str,
    missing_reason_code: str,
    sort_reason_codes: bool = False,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    analytics = source_analytics.get(family)
    if analytics is None:
        return ("DEGRADED", missing_summary, {}, {}, [missing_reason_code])
    reason_codes = list(analytics.reason_codes)
    if sort_reason_codes:
        reason_codes = sorted(set(reason_codes))
    return (
        analytics.state,
        analytics.summary,
        analytics.facts,
        analytics.metrics,
        reason_codes,
    )


def _adapter_section_payload(
    *,
    summary: str,
    adapter_contract: str,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    return (
        "READY",
        summary,
        {"adapter_contract": adapter_contract},
        {},
        [],
    )


def _run_state_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]] | None:
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
        return _trade_intents_section_payload(result)
    if section_type == "after_state":
        return _after_state_section_payload(result)
    return None


def _trade_intents_section_payload(
    result: RebalanceResult,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
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


def _after_state_section_payload(
    result: RebalanceResult,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    blocked = result.status == "BLOCKED"
    return (
        "BLOCKED" if blocked else "READY",
        "After-state simulation summary captured from source run.",
        {"after_summary": result.after_simulated.model_dump(mode="json")},
        {"position_count": len(result.after_simulated.positions)},
        ["DPM_AFTER_STATE_BLOCKED"] if blocked else [],
    )


def _run_diagnostics_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]] | None:
    if section_type == "liquidity_and_cash":
        return _liquidity_and_cash_section_payload(result)
    if section_type == "fx_funding_plan":
        return _fx_funding_plan_section_payload(result)
    if section_type == "currency_overlay_evidence":
        return _currency_overlay_evidence_section_payload()
    return None


def _liquidity_and_cash_section_payload(result: RebalanceResult) -> _SectionPayload:
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


def _fx_funding_plan_section_payload(result: RebalanceResult) -> _SectionPayload:
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


def _currency_overlay_evidence_section_payload() -> _SectionPayload:
    return (
        "DEGRADED",
        "Currency-overlay authority context is not attached.",
        {},
        {},
        ["DPM_CURRENCY_OVERLAY_CONTEXT_MISSING"],
    )


def _run_policy_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    selected_alternative: ConstructionAlternative | None,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]] | None:
    if section_type == "drift_impact":
        return _drift_impact_section_payload(selected_alternative=selected_alternative)
    if section_type == "tax_impact":
        return _tax_impact_section_payload(result=result)
    if section_type == "rule_results":
        return _rule_results_section_payload(result=result)
    return None


def _drift_impact_section_payload(
    *, selected_alternative: ConstructionAlternative | None
) -> _SectionPayload:
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


def _tax_impact_section_payload(*, result: RebalanceResult) -> _SectionPayload:
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


def _rule_results_section_payload(*, result: RebalanceResult) -> _SectionPayload:
    failed = [rule for rule in result.rule_results if rule.status == "FAIL"]
    return (
        "BLOCKED" if any(rule.severity == "HARD" for rule in failed) else "READY",
        "Rule results captured from manage policy engine.",
        {"rule_results": [rule.model_dump(mode="json") for rule in result.rule_results]},
        {"fail_count": len(failed)},
        [rule.reason_code for rule in failed],
    )


def _proof_pack_governance_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    selection: ConstructionAlternativeSelection | None,
    source_ref_count: int,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]] | None:
    if section_type == "approval_requirements":
        return _approval_requirements_section_payload(
            result=result,
            workflow_decisions=workflow_decisions,
        )
    if section_type == "operations_handoff":
        return _operations_handoff_section_payload(result=result)
    if section_type == "decision_timeline":
        return _decision_timeline_section_payload(run=run, selection=selection)
    if section_type == "lineage":
        return _lineage_section_payload(
            result=result,
            run=run,
            source_ref_count=source_ref_count,
        )
    if section_type == "supportability":
        return _supportability_section_payload()
    return None


def _operations_handoff_section_payload(*, result: RebalanceResult) -> _SectionPayload:
    return (
        "READY" if result.status == "READY" else "PENDING_REVIEW",
        "Operations handoff reflects current pre-trade readiness.",
        {"run_status": result.status},
        {},
        [] if result.status == "READY" else ["DPM_OPERATIONS_REVIEW_REQUIRED"],
    )


def _decision_timeline_section_payload(
    *,
    run: DpmRunRecord | None,
    selection: ConstructionAlternativeSelection | None,
) -> _SectionPayload:
    return (
        "READY",
        "Timeline generated from source run, selection, and proof-pack generation events.",
        {
            "run_created_at": run.created_at.isoformat() if run else None,
            "selection_id": selection.selection_id if selection else None,
        },
        {},
        [],
    )


def _lineage_section_payload(
    *,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    source_ref_count: int,
) -> _SectionPayload:
    return (
        "READY" if run is not None else "BLOCKED",
        "Lineage identifiers captured from source run and source artifacts.",
        result.lineage.model_dump(mode="json") if result else {},
        {"source_ref_count": source_ref_count},
        [] if run is not None else ["DPM_LINEAGE_RUN_MISSING"],
    )


def _supportability_section_payload() -> _SectionPayload:
    return ("READY", "Supportability summary is generated for every proof pack.", {}, {}, [])


def _approval_requirements_section_payload(
    *,
    result: RebalanceResult,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> _SectionPayload:
    gate = result.gate_decision
    workflow_facts = _approval_workflow_decision_facts(workflow_decisions)
    return (
        _approval_section_state(result=result, gate=gate),
        "Approval posture captured from run status and gate decision.",
        {
            "gate_decision": _approval_gate_fact(gate),
            "workflow_decisions": workflow_facts,
        },
        {"workflow_decision_count": len(workflow_facts)},
        _approval_reason_codes(gate),
    )


def _approval_workflow_decision_facts(
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[dict[str, Any]]:
    return [
        decision.model_dump(mode="json")
        for decision in sorted(workflow_decisions, key=lambda item: item.decided_at)
    ]


def _approval_section_state(
    *, result: RebalanceResult, gate: GateDecision | None
) -> ProofPackSectionState:
    if _run_blocks_approval(result) or _gate_blocks_approval(gate):
        return "BLOCKED"
    if _run_requires_approval_review(result) or _gate_requires_approval_review(gate):
        return "PENDING_REVIEW"
    return "READY"


def _run_blocks_approval(result: RebalanceResult) -> bool:
    return result.status == "BLOCKED"


def _gate_blocks_approval(gate: GateDecision | None) -> bool:
    return gate is not None and gate.gate == "BLOCKED"


def _run_requires_approval_review(result: RebalanceResult) -> bool:
    return result.status == "PENDING_REVIEW"


def _gate_requires_approval_review(gate: GateDecision | None) -> bool:
    return gate is not None and gate.gate.endswith("REQUIRED")


def _approval_gate_fact(gate: GateDecision | None) -> dict[str, Any] | None:
    return gate.model_dump(mode="json") if gate is not None else None


def _approval_reason_codes(gate: GateDecision | None) -> list[str]:
    if gate is None:
        return []
    return [reason.reason_code for reason in gate.reasons]


def _mandate_context_section_payload(
    *,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    if not mandate_id:
        return (
            "BLOCKED",
            "Mandate identity is required before proof-pack promotion.",
            {"mandate_id": None},
            {},
            ["DPM_PROOF_PACK_MANDATE_ID_MISSING"],
        )
    if mandate_twin is None:
        reason_codes = mandate_evidence_gap_codes or ["DPM_MANDATE_TWIN_EVIDENCE_MISSING"]
        return (
            "DEGRADED",
            "Mandate identity is present, but no persisted mandate digital-twin evidence is attached.",
            {"mandate_id": mandate_id},
            {},
            reason_codes,
        )
    if mandate_health is None:
        return (
            "DEGRADED",
            "Mandate digital-twin evidence is attached, but latest mandate-health evidence is missing.",
            {
                "mandate_id": mandate_twin.mandate_id,
                "mandate_version": mandate_twin.mandate_version,
                "portfolio_id": mandate_twin.portfolio_id,
                "as_of_date": mandate_twin.as_of_date.isoformat(),
                "risk_profile": mandate_twin.risk_profile,
                "model_portfolio_id": mandate_twin.model_portfolio_id,
                "field_gap_codes": mandate_twin.field_gap_codes,
            },
            {},
            ["DPM_MANDATE_HEALTH_EVIDENCE_MISSING", *mandate_twin.field_gap_codes],
        )
    mandate_state = _mandate_health_state(mandate_health)
    reason_codes = [reason.reason_code for reason in mandate_health.top_reasons]
    return (
        mandate_state,
        "Mandate digital-twin and health evidence are attached from persisted RFC-0038 truth.",
        {
            "mandate_id": mandate_twin.mandate_id,
            "mandate_version": mandate_twin.mandate_version,
            "portfolio_id": mandate_twin.portfolio_id,
            "as_of_date": mandate_twin.as_of_date.isoformat(),
            "risk_profile": mandate_twin.risk_profile,
            "investment_objective": mandate_twin.investment_objective,
            "model_portfolio_id": mandate_twin.model_portfolio_id,
            "model_portfolio_version": mandate_twin.model_portfolio_version,
            "health_snapshot_id": mandate_health.health_snapshot_id,
            "health_state": mandate_health.health_state.value,
            "source_readiness_state": mandate_health.source_readiness_state,
            "field_gap_codes": mandate_twin.field_gap_codes,
        },
        {
            "health_score": mandate_health.health_score,
            "dimension_count": len(mandate_health.dimension_scores),
            "top_reason_count": len(mandate_health.top_reasons),
            "source_lineage_count": len(mandate_twin.source_lineage),
        },
        [*reason_codes, *mandate_twin.field_gap_codes],
    )


def _selected_alternative_section_payload(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    if selected_alternative is None:
        return (
            "DEGRADED",
            "Direct-run proof pack has no selected construction alternative.",
            {},
            {},
            ["DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE"],
        )
    return (
        _selected_alternative_method_state(selected_alternative),
        "Selected construction alternative captured with method and trace evidence.",
        _selected_alternative_facts(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
        ),
        selected_alternative.comparison_metrics.model_dump(mode="json"),
        _selected_alternative_reason_codes(selected_alternative),
    )


def _selected_alternative_method_state(
    selected_alternative: ConstructionAlternative,
) -> ProofPackSectionState:
    if selected_alternative.method_status == "READY":
        return "READY"
    return cast(ProofPackSectionState, str(selected_alternative.method_status))


def _selected_alternative_reason_codes(
    selected_alternative: ConstructionAlternative,
) -> list[str]:
    if selected_alternative.method_status == "READY":
        return []
    return ["DPM_SELECTED_METHOD_NOT_READY"]


def _selected_alternative_facts(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative,
    selection: ConstructionAlternativeSelection | None,
) -> dict[str, Any]:
    return {
        "alternative_set_id": alternative_set.alternative_set_id if alternative_set else None,
        "selected_alternative_id": selected_alternative.alternative_id,
        "selection_id": selection.selection_id if selection else None,
        "method": selected_alternative.method,
        "method_status": selected_alternative.method_status,
        "summary": selected_alternative.summary,
        "objective_trace": [
            item.model_dump(mode="json") for item in selected_alternative.objective_trace
        ],
        "constraint_trace": [
            item.model_dump(mode="json") for item in selected_alternative.constraint_trace
        ],
    }


def _source_readiness_section_payload(
    *,
    result: RebalanceResult | None,
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    if result is None:
        return ("BLOCKED", "No source run is available.", {}, {}, ["DPM_SOURCE_RUN_MISSING"])

    source_state = result.lineage.source_supportability_state
    reason_codes = (
        [] if source_state in {None, "READY", "ready"} else ["DPM_SOURCE_READINESS_DEGRADED"]
    )
    return (
        "READY" if not reason_codes else "DEGRADED",
        "Source readiness captured from run lineage.",
        {
            "input_mode": result.lineage.input_mode,
            "source_system": result.lineage.source_system,
            "source_supportability_state": source_state,
        },
        {},
        reason_codes,
    )


def _turnover_and_cost_section_payload(
    *,
    selected_alternative: ConstructionAlternative | None,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    transaction_cost_context = source_analytics.get("transaction_cost")
    metrics = (
        selected_alternative.comparison_metrics.model_dump(mode="json")
        if selected_alternative
        else {}
    )
    facts: dict[str, Any] = {}
    reason_codes = [] if metrics else ["DPM_TURNOVER_COST_METRICS_MISSING"]
    state: ProofPackSectionState = "READY" if metrics else "DEGRADED"
    summary = "Turnover and cost evidence captured when construction metrics are available."

    if transaction_cost_context is not None:
        facts = transaction_cost_context.facts
        metrics = {**metrics, **transaction_cost_context.metrics}
        reason_codes.extend(transaction_cost_context.reason_codes)
        state = _lowest_section_state([state, transaction_cost_context.state])
        summary = (
            "Turnover metrics and source-owned observed transaction-cost evidence are attached."
        )
    elif metrics:
        reason_codes.append("DPM_TRANSACTION_COST_AUTHORITY_CONTEXT_MISSING")
        state = "DEGRADED"

    return (
        state,
        summary,
        facts,
        metrics,
        sorted(set(reason_codes)),
    )


def _eligibility_and_restrictions_section_payload(
    *,
    result: RebalanceResult,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    restriction_context = source_analytics.get("client_restriction")
    excluded = result.universe.excluded
    if restriction_context is not None:
        reason_codes = list(restriction_context.reason_codes)
        if excluded:
            reason_codes.append("DPM_UNIVERSE_EXCLUSIONS_PRESENT")
        return (
            _lowest_section_state(
                [
                    restriction_context.state,
                    "PENDING_REVIEW" if excluded else "READY",
                ]
            ),
            "Eligibility evidence and source-owned client restriction profile are attached.",
            {
                **restriction_context.facts,
                "excluded": [item.model_dump(mode="json") for item in excluded],
            },
            {**restriction_context.metrics, "excluded_count": len(excluded)},
            sorted(set(reason_codes)),
        )

    return (
        "READY" if not excluded else "PENDING_REVIEW",
        "Eligibility and restriction evidence captured from source run universe.",
        {"excluded": [item.model_dump(mode="json") for item in excluded]},
        {"excluded_count": len(excluded)},
        ["DPM_UNIVERSE_EXCLUSIONS_PRESENT"] if excluded else [],
    )


def _decision_summary_section_payload(
    *,
    result: RebalanceResult | None,
    selected_alternative: ConstructionAlternative | None,
    reason: str | None,
    created_by: str,
) -> _SectionPayload:
    reason_codes = [] if reason else ["DPM_PROOF_PACK_REASON_MISSING"]
    return (
        "READY" if reason else "DEGRADED",
        "Decision evidence assembled from manage run and actor rationale.",
        {
            "actor": created_by,
            "reason": reason,
            "source_run_status": result.status if result is not None else None,
            "selected_alternative_id": (
                selected_alternative.alternative_id if selected_alternative else None
            ),
        },
        {},
        reason_codes,
    )


def _pre_run_source_analytics_payload(
    *,
    section_type: ProofPackSectionType,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> _SectionPayload | None:
    config = _PRE_RUN_SOURCE_ANALYTICS_SECTIONS.get(section_type)
    if config is None:
        return None

    family, missing_summary, missing_reason_code = config
    return _source_analytics_section_payload(
        source_analytics=source_analytics,
        family=family,
        missing_summary=missing_summary,
        missing_reason_code=missing_reason_code,
    )


def _pre_run_adapter_payload(
    *,
    section_type: ProofPackSectionType,
) -> _SectionPayload | None:
    config = _PRE_RUN_ADAPTER_SECTIONS.get(section_type)
    if config is None:
        return None

    summary, adapter_contract = config
    return _adapter_section_payload(
        summary=summary,
        adapter_contract=adapter_contract,
    )


def _pre_run_core_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    reason: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    created_by: str,
) -> _SectionPayload | None:
    if section_type == "decision_summary":
        return _decision_summary_section_payload(
            result=result,
            selected_alternative=selected_alternative,
            reason=reason,
            created_by=created_by,
        )
    if section_type == "mandate_context":
        return _mandate_context_section_payload(
            mandate_id=mandate_id,
            mandate_twin=mandate_twin,
            mandate_health=mandate_health,
            mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        )
    if section_type == "source_readiness":
        return _source_readiness_section_payload(
            result=result,
        )
    if section_type == "selected_alternative":
        return _selected_alternative_section_payload(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
        )
    return None


def _pre_run_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    reason: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    created_by: str,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> _SectionPayload | None:
    core_payload = _pre_run_core_section_payload(
        section_type=section_type,
        result=result,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        reason=reason,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        created_by=created_by,
    )
    if core_payload is not None:
        return core_payload

    source_analytics_payload = _pre_run_source_analytics_payload(
        section_type=section_type,
        source_analytics=source_analytics,
    )
    if source_analytics_payload is not None:
        return source_analytics_payload

    adapter_payload = _pre_run_adapter_payload(section_type=section_type)
    if adapter_payload is not None:
        return adapter_payload

    return None


def _run_bound_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    selected_alternative: ConstructionAlternative | None,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> _SectionPayload | None:
    run_state_payload = _run_state_section_payload(section_type=section_type, result=result)
    if run_state_payload is not None:
        return run_state_payload

    run_policy_payload = _run_policy_section_payload(
        section_type=section_type,
        result=result,
        selected_alternative=selected_alternative,
    )
    if run_policy_payload is not None:
        return run_policy_payload

    if section_type == "turnover_and_cost":
        return _turnover_and_cost_section_payload(
            selected_alternative=selected_alternative,
            source_analytics=source_analytics,
        )

    run_diagnostics_payload = _run_diagnostics_section_payload(
        section_type=section_type,
        result=result,
    )
    if run_diagnostics_payload is not None:
        return run_diagnostics_payload

    return None


def _run_source_context_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> _SectionPayload | None:
    if section_type == "scenario_and_regime_evidence":
        return _source_analytics_section_payload(
            source_analytics=source_analytics,
            family="regime_stress",
            missing_summary="Scenario/regime authority context is not attached.",
            missing_reason_code="DPM_SCENARIO_CONTEXT_MISSING",
            sort_reason_codes=True,
        )
    if section_type == "eligibility_and_restrictions":
        return _eligibility_and_restrictions_section_payload(
            result=result,
            source_analytics=source_analytics,
        )
    return None


def _section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult | None,
    run: DpmRunRecord | None,
    run_artifact_hash: str | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    reason: str | None,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
    created_by: str,
    source_ref_count: int,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    pre_run_payload = _pre_run_section_payload(
        section_type=section_type,
        result=result,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        reason=reason,
        mandate_id=mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        created_by=created_by,
        source_analytics=source_analytics,
    )
    if pre_run_payload is not None:
        return pre_run_payload
    if result is None:
        return ("BLOCKED", "Source rebalance run is missing.", {}, {}, ["DPM_SOURCE_RUN_MISSING"])
    run_bound_payload = _run_bound_section_payload(
        section_type=section_type,
        result=result,
        selected_alternative=selected_alternative,
        source_analytics=source_analytics,
    )
    if run_bound_payload is not None:
        return run_bound_payload

    run_source_context_payload = _run_source_context_section_payload(
        section_type=section_type,
        result=result,
        source_analytics=source_analytics,
    )
    if run_source_context_payload is not None:
        return run_source_context_payload

    governance_payload = _proof_pack_governance_section_payload(
        section_type=section_type,
        result=result,
        run=run,
        selection=selection,
        source_ref_count=source_ref_count,
        workflow_decisions=workflow_decisions,
    )
    if governance_payload is not None:
        return governance_payload
    raise AssertionError(f"Unhandled proof-pack section type: {section_type}")


def _decision_summary(
    *,
    source_type: ProofPackSourceType,
    result: RebalanceResult | None,
    selected_alternative: ConstructionAlternative | None,
    reason: str | None,
    supportability: DpmProofPackSupportability,
) -> DpmProofPackDecisionSummary:
    return DpmProofPackDecisionSummary(
        decision_type="PRE_TRADE_REBALANCE",
        recommended_action="REVIEW_REBALANCE"
        if supportability.status != "READY"
        else "APPROVE_REBALANCE",
        selected_alternative_type=(
            str(selected_alternative.method) if selected_alternative is not None else None
        ),
        business_rationale=reason or "No actor rationale supplied.",
        expected_benefit=(
            selected_alternative.summary
            if selected_alternative is not None
            else "Direct source run proof pack."
        ),
        main_tradeoffs=_main_tradeoffs(selected_alternative=selected_alternative),
        top_risks=supportability.reason_codes[:5],
        approval_state=result.status if result is not None else "BLOCKED",
        operations_state=supportability.status,
    )


def _main_tradeoffs(*, selected_alternative: ConstructionAlternative | None) -> list[str]:
    if selected_alternative is None:
        return ["No construction alternative comparison was selected."]
    metrics = selected_alternative.comparison_metrics
    return [
        f"turnover_weight={metrics.turnover_weight}",
        f"drift_reduction={metrics.drift_reduction}",
        f"trade_count={metrics.trade_count}",
    ]


def _decision_timeline(
    *,
    proof_pack_id: str,
    generated_at: str,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
    created_by: str,
) -> DpmProofPackDecisionTimeline:
    events = _source_decision_timeline_events(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        generated_at=generated_at,
        created_by=created_by,
    )
    events.extend(_workflow_decision_timeline_events(workflow_decisions))
    events.append(
        _proof_pack_generated_timeline_event(
            proof_pack_id=proof_pack_id,
            generated_at=generated_at,
            source_type=source_type,
            created_by=created_by,
        )
    )
    return DpmProofPackDecisionTimeline(
        events=sorted(events, key=_decision_timeline_event_sort_key)
    )


def _source_decision_timeline_events(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    generated_at: str,
    created_by: str,
) -> list[DpmProofPackDecisionTimelineEvent]:
    events: list[DpmProofPackDecisionTimelineEvent] = []
    if run is not None:
        events.append(_run_created_timeline_event(run))
    if alternative_set is not None:
        events.append(_alternative_set_generated_timeline_event(alternative_set))
    if selected_alternative is not None:
        events.append(
            _selected_alternative_timeline_event(
                selected_alternative=selected_alternative,
                selection=selection,
                generated_at=generated_at,
                created_by=created_by,
            )
        )
    return events


def _run_created_timeline_event(
    run: DpmRunRecord,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{run.rebalance_run_id}:run_created",
        event_type="REBALANCE_RUN_CREATED",
        event_time=run.created_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        status=str(run.result_json.get("status", "UNKNOWN")),
        reason_codes=[],
    )


def _alternative_set_generated_timeline_event(
    alternative_set: ConstructionAlternativeSet,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{alternative_set.alternative_set_id}:generated",
        event_type="ALTERNATIVE_SET_GENERATED",
        event_time=alternative_set.generated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        status=str(alternative_set.status),
        reason_codes=[],
    )


def _selected_alternative_timeline_event(
    *,
    selected_alternative: ConstructionAlternative,
    selection: ConstructionAlternativeSelection | None,
    generated_at: str,
    created_by: str,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{selected_alternative.alternative_id}:selected",
        event_type="SELECTED_ALTERNATIVE",
        event_time=selection.selected_at.isoformat() if selection else generated_at,
        actor=selection.actor_id if selection else created_by,
        source_system="lotus-manage",
        status=str(selected_alternative.method_status),
        reason_codes=[selection.reason_code] if selection else [],
    )


def _workflow_decision_timeline_events(
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[DpmProofPackDecisionTimelineEvent]:
    return [
        DpmProofPackDecisionTimelineEvent(
            event_id=f"{decision.decision_id}:workflow_decision",
            event_type="WORKFLOW_DECISION",
            event_time=decision.decided_at.isoformat(),
            actor=decision.actor_id,
            source_system="lotus-manage",
            status=str(decision.action),
            reason_codes=[decision.reason_code],
        )
        for decision in workflow_decisions
    ]


def _proof_pack_generated_timeline_event(
    *,
    proof_pack_id: str,
    generated_at: str,
    source_type: ProofPackSourceType,
    created_by: str,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{proof_pack_id}:generated",
        event_type="PROOF_PACK_GENERATED",
        event_time=generated_at,
        actor=created_by,
        source_system="lotus-manage",
        status=source_type,
        reason_codes=[],
    )


_DECISION_TIMELINE_EVENT_RANK = {
    "REBALANCE_RUN_CREATED": 0,
    "ALTERNATIVE_SET_GENERATED": 1,
    "SELECTED_ALTERNATIVE": 2,
    "WORKFLOW_DECISION": 3,
    "PROOF_PACK_GENERATED": 4,
}


def _decision_timeline_event_sort_key(
    event: DpmProofPackDecisionTimelineEvent,
) -> tuple[str, int, str]:
    return (
        event.event_time,
        _DECISION_TIMELINE_EVENT_RANK.get(event.event_type, 99),
        event.event_id,
    )


def _supportability(sections: list[DpmProofPackSection]) -> DpmProofPackSupportability:
    counts: dict[str, int] = {}
    reason_codes: list[str] = []
    section_hashes: dict[str, str] = {}
    for section in sections:
        counts[section.state] = counts.get(section.state, 0) + 1
        reason_codes.extend(section.reason_codes)
        section_hashes[section.section_id] = section.content_hash
    status = _aggregate_status(counts)
    return DpmProofPackSupportability(
        status=status,
        section_state_counts=counts,
        ready_section_count=counts.get("READY", 0),
        degraded_section_count=counts.get("DEGRADED", 0),
        blocked_section_count=counts.get("BLOCKED", 0),
        pending_review_section_count=counts.get("PENDING_REVIEW", 0),
        reason_codes=sorted(set(reason_codes)),
        section_hashes=section_hashes,
    )


def _aggregate_status(counts: dict[str, int]) -> ProofPackStatus:
    if counts.get("BLOCKED", 0) > 0:
        return "BLOCKED"
    if counts.get("PENDING_REVIEW", 0) > 0:
        return "PENDING_REVIEW"
    if counts.get("DEGRADED", 0) > 0:
        return "DEGRADED"
    return "READY"


def _lowest_section_state(states: list[ProofPackSectionState]) -> ProofPackSectionState:
    state_order = {
        "BLOCKED": 0,
        "DEGRADED": 1,
        "PENDING_REVIEW": 2,
        "READY": 3,
        "NOT_APPLICABLE": 4,
    }
    return min(states, key=lambda item: state_order[item])


def _source_hashes(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if run is not None:
        hashes["rebalance_run"] = hash_canonical_payload(run.model_dump(mode="json"))
    if alternative_set is not None:
        hashes["alternative_set"] = hash_canonical_payload(alternative_set.model_dump(mode="json"))
    if selected_alternative is not None:
        hashes["selected_alternative"] = hash_canonical_payload(
            selected_alternative.model_dump(mode="json")
        )
    if mandate_twin is not None:
        hashes["mandate_twin"] = hash_canonical_payload(mandate_twin.model_dump(mode="json"))
    if mandate_health is not None:
        hashes["mandate_health"] = hash_canonical_payload(mandate_health.model_dump(mode="json"))
    return hashes


def _source_analytics(
    *,
    selected_alternative: ConstructionAlternative | None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> dict[str, ProofPackSourceAnalytics]:
    families: tuple[ProofPackAnalyticsFamily, ...] = (
        "risk",
        "performance",
        "transaction_cost",
        "client_restriction",
        "sustainability_preference",
        "regime_stress",
    )
    analytics_by_family: dict[str, ProofPackSourceAnalytics] = {
        family: analytics
        for family in families
        if (
            analytics := source_analytics_for_alternative(
                alternative=selected_alternative,
                family=family,
            )
        )
        is not None
    }
    if direct_regime_stress_context is not None and "regime_stress" not in analytics_by_family:
        direct_analytics = source_analytics_for_context(
            source_context=direct_regime_stress_context.model_dump(mode="json"),
            family="regime_stress",
        )
        if direct_analytics is not None:
            analytics_by_family["regime_stress"] = direct_analytics
    return analytics_by_family


def _source_refs(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    source_hashes: dict[str, str],
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> list[DpmProofPackSourceRef]:
    refs = []
    if run is not None:
        refs.append(_run_source_ref(run=run, source_hashes=source_hashes))
    if alternative_set is not None:
        refs.append(_alternative_set_source_ref(alternative_set, source_hashes=source_hashes))
    if selected_alternative is not None:
        refs.append(
            _selected_alternative_source_ref(selected_alternative, source_hashes=source_hashes)
        )
    if mandate_twin is not None:
        refs.append(_mandate_twin_source_ref(mandate_twin, source_hashes=source_hashes))
    if mandate_health is not None:
        refs.append(_mandate_health_source_ref(mandate_health, source_hashes=source_hashes))
    return refs


def _run_source_ref(*, run: DpmRunRecord, source_hashes: dict[str, str]) -> DpmProofPackSourceRef:
    result = RebalanceResult.model_validate(run.result_json)
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_REBALANCE_RUN",
        source_id=run.rebalance_run_id,
        supportability_state=result.status,
        content_hash=source_hashes.get("rebalance_run"),
    )


def _alternative_set_source_ref(
    alternative_set: ConstructionAlternativeSet, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
        source_id=alternative_set.alternative_set_id,
        supportability_state=str(alternative_set.status),
        content_hash=source_hashes.get("alternative_set"),
    )


def _selected_alternative_source_ref(
    selected_alternative: ConstructionAlternative, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE",
        source_id=selected_alternative.alternative_id,
        supportability_state=str(selected_alternative.method_status),
        content_hash=source_hashes.get("selected_alternative"),
    )


def _mandate_twin_source_ref(
    mandate_twin: DpmMandateDigitalTwin, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_MANDATE_DIGITAL_TWIN",
        source_id=mandate_twin.mandate_id,
        supportability_state="READY" if not mandate_twin.field_gap_codes else "DEGRADED",
        content_hash=source_hashes.get("mandate_twin"),
    )


def _mandate_health_source_ref(
    mandate_health: DpmMandateHealthSnapshot, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
        source_id=mandate_health.health_snapshot_id,
        supportability_state=mandate_health.health_state.value,
        content_hash=source_hashes.get("mandate_health"),
    )


def _mandate_health_state(snapshot: DpmMandateHealthSnapshot) -> ProofPackSectionState:
    if snapshot.health_state.value == "BLOCKED":
        return "BLOCKED"
    if snapshot.health_state.value == "PENDING_REVIEW":
        return "PENDING_REVIEW"
    if snapshot.source_readiness_state not in {"READY", "ready"}:
        return "DEGRADED"
    return "READY"


def _source_supportability(
    *,
    result: RebalanceResult | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> dict[str, Any]:
    return {
        "run_status": result.status if result is not None else None,
        "input_mode": result.lineage.input_mode if result is not None else None,
        "source_system": result.lineage.source_system if result is not None else None,
        "source_supportability_state": (
            result.lineage.source_supportability_state if result is not None else None
        ),
        "alternative_set_status": str(alternative_set.status) if alternative_set else None,
    }


def _resolve_portfolio_id(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> str:
    if alternative_set is not None:
        return alternative_set.portfolio_id
    if run is not None:
        return run.portfolio_id
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")


def _as_of_date(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> str:
    if alternative_set is not None:
        return alternative_set.as_of
    if run is not None:
        return run.created_at.date().isoformat()
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")


def _proof_pack_id(
    *,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
) -> str:
    if source_type == "REBALANCE_RUN" and run is not None:
        return proof_pack_id_for_rebalance_run(rebalance_run_id=run.rebalance_run_id)
    if (
        source_type == "SELECTED_ALTERNATIVE"
        and alternative_set is not None
        and selected_alternative is not None
    ):
        return proof_pack_id_for_selected_alternative(
            alternative_set_id=alternative_set.alternative_set_id,
            selected_alternative_id=selected_alternative.alternative_id,
        )
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")
