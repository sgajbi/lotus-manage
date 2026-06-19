"""Pure RFC-0040 proof-pack builders."""

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.models import (
    AuthoritativeRegimeStressContext,
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.proof_packs import alternative_sections as _alternative_sections
from src.core.proof_packs import decision_artifacts as _decision_artifacts
from src.core.proof_packs import identity as _identity
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSection,
    DpmProofPackSourceRef,
    DpmProofPackSupportability,
    ProofPackSectionState,
    ProofPackSectionType,
    ProofPackSourceType,
    ProofPackStatus,
)
from src.core.proof_packs.mandate_context import (
    mandate_context_section_payload as _mandate_context_section_payload,
)
from src.core.proof_packs import governance_sections as _governance_sections
from src.core.proof_packs import run_sections as _run_sections
from src.core.proof_packs import section_payloads as _section_payloads
from src.core.proof_packs import source_identity as _source_identity
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.rebalance_runs.artifact import build_dpm_run_artifact
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from src.core.models import RebalanceResult

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


proof_pack_id_for_rebalance_run = _identity.proof_pack_id_for_rebalance_run
proof_pack_id_for_selected_alternative = _identity.proof_pack_id_for_selected_alternative


_SECTION_ORDER: list[ProofPackSectionType] = list(_SECTION_TITLES)


ProofPackSourceValidationError = _identity.ProofPackSourceValidationError


_SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]

_PreRunSourceAnalyticsConfig = tuple[ProofPackAnalyticsFamily, str, str]

_ProofPackSourceContext = _source_identity.ProofPackSourceContext
_SourceHashCandidate = _source_identity.SourceHashCandidate
_approval_gate_fact = _governance_sections.approval_gate_fact
_approval_reason_codes = _governance_sections.approval_reason_codes
_approval_requirements_section_payload = _governance_sections.approval_requirements_section_payload
_approval_section_state = _governance_sections.approval_section_state
_approval_workflow_decision_facts = _governance_sections.approval_workflow_decision_facts
_decision_timeline_section_payload = _governance_sections.decision_timeline_section_payload
_gate_blocks_approval = _governance_sections.gate_blocks_approval
_gate_requires_approval_review = _governance_sections.gate_requires_approval_review
_lineage_section_payload = _governance_sections.lineage_section_payload
_optional_source_hash = _source_identity.optional_source_hash
_operations_handoff_section_payload = _governance_sections.operations_handoff_section_payload
_present_source_refs = _source_identity.present_source_refs
_proof_pack_governance_section_payload = _governance_sections.proof_pack_governance_section_payload
_proof_pack_source_context = _source_identity.proof_pack_source_context
_run_blocks_approval = _governance_sections.run_blocks_approval
_run_requires_approval_review = _governance_sections.run_requires_approval_review
_source_analytics = _source_identity.source_analytics_for_proof_pack
_source_hash_candidates = _source_identity.source_hash_candidates
_source_hashes = _source_identity.source_hashes_for_proof_pack
_source_refs = _source_identity.source_refs_for_proof_pack
_supportability_section_payload = _governance_sections.supportability_section_payload
_eligibility_and_restrictions_section_payload = (
    _alternative_sections.eligibility_and_restrictions_section_payload
)
_eligibility_payload_from_universe_exclusions = (
    _alternative_sections.eligibility_payload_from_universe_exclusions
)
_eligibility_payload_with_restriction_context = (
    _alternative_sections.eligibility_payload_with_restriction_context
)
_eligibility_reason_codes = _alternative_sections.eligibility_reason_codes
_eligibility_state_from_universe_exclusions = (
    _alternative_sections.eligibility_state_from_universe_exclusions
)
_excluded_instrument_facts = _alternative_sections.excluded_instrument_facts
_selected_alternative_facts = _alternative_sections.selected_alternative_facts
_selected_alternative_method_state = _alternative_sections.selected_alternative_method_state
_selected_alternative_reason_codes = _alternative_sections.selected_alternative_reason_codes
_selected_alternative_section_payload = _alternative_sections.selected_alternative_section_payload
_turnover_and_cost_section_payload = _alternative_sections.turnover_and_cost_section_payload
_turnover_base_posture = _alternative_sections.turnover_base_posture
_turnover_comparison_metrics = _alternative_sections.turnover_comparison_metrics
_turnover_comparison_metrics_payload = _alternative_sections.turnover_comparison_metrics_payload
_turnover_payload_with_transaction_cost_context = (
    _alternative_sections.turnover_payload_with_transaction_cost_context
)
_turnover_payload_without_transaction_cost_context = (
    _alternative_sections.turnover_payload_without_transaction_cost_context
)
_alternative_set_generated_timeline_event = (
    _decision_artifacts.alternative_set_generated_timeline_event
)
_approval_state = _decision_artifacts.approval_state
_decision_summary = _decision_artifacts.decision_summary
_decision_timeline = _decision_artifacts.decision_timeline
_decision_timeline_event_sort_key = _decision_artifacts.decision_timeline_event_sort_key
_expected_benefit = _decision_artifacts.expected_benefit
_main_tradeoffs = _decision_artifacts.main_tradeoffs
_proof_pack_generated_timeline_event = _decision_artifacts.proof_pack_generated_timeline_event
_recommended_action = _decision_artifacts.recommended_action
_run_created_timeline_event = _decision_artifacts.run_created_timeline_event
_selected_alternative_timeline_event = _decision_artifacts.selected_alternative_timeline_event
_selected_alternative_type = _decision_artifacts.selected_alternative_type
_source_decision_timeline_events = _decision_artifacts.source_decision_timeline_events
_workflow_decision_timeline_events = _decision_artifacts.workflow_decision_timeline_events
_after_state_section_payload = _run_sections.after_state_section_payload
_currency_overlay_evidence_section_payload = _run_sections.currency_overlay_evidence_section_payload
_drift_impact_section_payload = _run_sections.drift_impact_section_payload
_failed_rule_results = _run_sections.failed_rule_results
_fx_funding_plan_section_payload = _run_sections.fx_funding_plan_section_payload
_liquidity_and_cash_section_payload = _run_sections.liquidity_and_cash_section_payload
_rule_results_metrics = _run_sections.rule_results_metrics
_rule_results_reason_codes = _run_sections.rule_results_reason_codes
_rule_results_section_payload = _run_sections.rule_results_section_payload
_rule_results_section_state = _run_sections.rule_results_section_state
_run_diagnostics_section_payload = _run_sections.run_diagnostics_section_payload
_run_policy_section_payload = _run_sections.run_policy_section_payload
_run_state_section_payload = _run_sections.run_state_section_payload
_tax_impact_section_payload = _run_sections.tax_impact_section_payload
_trade_intents_section_payload = _run_sections.trade_intents_section_payload
_alternative_set_status = _identity.alternative_set_status
_as_of_date = _identity.as_of_date
_candidate_proof_pack_id = _identity.candidate_proof_pack_id
_generated_proof_pack_correlation_id = _identity.generated_proof_pack_correlation_id
_proof_pack_id = _identity.proof_pack_id
_resolve_portfolio_id = _identity.resolve_portfolio_id
_resolve_proof_pack_correlation_id = _identity.resolve_proof_pack_correlation_id
_run_correlation_id = _identity.run_correlation_id
_run_source_proof_pack_id = _identity.run_source_proof_pack_id
_run_source_supportability = _identity.run_source_supportability
_selected_alternative_source_proof_pack_id = _identity.selected_alternative_source_proof_pack_id
_selection_correlation_id = _identity.selection_correlation_id
_source_supportability = _identity.source_supportability
_adapter_section_payload = _section_payloads.adapter_section_payload
_decision_summary_section_payload = _section_payloads.decision_summary_section_payload
_source_analytics_section_payload = _section_payloads.source_analytics_section_payload
_source_readiness_section_payload = _section_payloads.source_readiness_section_payload

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
    source_context = _proof_pack_source_context(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        direct_regime_stress_context=direct_regime_stress_context,
    )
    result = _rebalance_result_from_run(run)
    return _ProofPackBuildContext(
        created_at=resolved_created_at,
        generated_at=resolved_created_at.isoformat(),
        result=result,
        run_artifact_hash=_run_artifact_hash(run),
        source_hashes=source_context.source_hashes,
        source_analytics=source_context.source_analytics,
        source_refs=source_context.source_refs,
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


def _rebalance_result_from_run(run: DpmRunRecord | None) -> RebalanceResult | None:
    return RebalanceResult.model_validate(run.result_json) if run is not None else None


def _run_artifact_hash(run: DpmRunRecord | None) -> str | None:
    if run is None:
        return None
    return build_dpm_run_artifact(run=run).evidence.hashes.artifact_hash


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

    return _run_present_section_payload(
        section_type=section_type,
        result=result,
        run=run,
        selected_alternative=selected_alternative,
        selection=selection,
        source_ref_count=source_ref_count,
        source_analytics=source_analytics,
        workflow_decisions=workflow_decisions,
    )


def _run_present_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    source_ref_count: int,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> _SectionPayload:
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
