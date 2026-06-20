"""Proof-pack section payload routing."""

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.models import RebalanceResult
from src.core.proof_packs.alternative_sections import (
    eligibility_and_restrictions_section_payload,
    selected_alternative_section_payload,
    turnover_and_cost_section_payload,
)
from src.core.proof_packs.governance_sections import proof_pack_governance_section_payload
from src.core.proof_packs.mandate_context import mandate_context_section_payload
from src.core.proof_packs.models import ProofPackSectionType
from src.core.proof_packs.run_sections import (
    run_diagnostics_section_payload,
    run_policy_section_payload,
    run_state_section_payload,
)
from src.core.proof_packs.section_assembly import SectionPayload
from src.core.proof_packs.section_payloads import (
    adapter_section_payload,
    decision_summary_section_payload,
    source_analytics_section_payload,
    source_readiness_section_payload,
)
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
)
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord

PreRunSourceAnalyticsConfig = tuple[ProofPackAnalyticsFamily, str, str]

PRE_RUN_SOURCE_ANALYTICS_SECTIONS: dict[ProofPackSectionType, PreRunSourceAnalyticsConfig] = {
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

PRE_RUN_ADAPTER_SECTIONS: dict[ProofPackSectionType, tuple[str, str]] = {
    "reporting_refs": (
        "Report input adapter is available; generated refs are appended outside the immutable proof-pack body.",
        "DpmProofPackReportInput",
    ),
    "ai_refs": (
        "AI evidence input adapter is available with forbidden-action and forbidden-field guardrails.",
        "DpmProofPackAiEvidenceInput",
    ),
}


def pre_run_source_analytics_payload(
    *,
    section_type: ProofPackSectionType,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> SectionPayload | None:
    config = PRE_RUN_SOURCE_ANALYTICS_SECTIONS.get(section_type)
    if config is None:
        return None

    family, missing_summary, missing_reason_code = config
    return source_analytics_section_payload(
        source_analytics=source_analytics,
        family=family,
        missing_summary=missing_summary,
        missing_reason_code=missing_reason_code,
    )


def pre_run_adapter_payload(
    *,
    section_type: ProofPackSectionType,
) -> SectionPayload | None:
    config = PRE_RUN_ADAPTER_SECTIONS.get(section_type)
    if config is None:
        return None

    summary, adapter_contract = config
    return adapter_section_payload(
        summary=summary,
        adapter_contract=adapter_contract,
    )


def pre_run_core_section_payload(
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
) -> SectionPayload | None:
    if section_type == "decision_summary":
        return decision_summary_section_payload(
            result=result,
            selected_alternative=selected_alternative,
            reason=reason,
            created_by=created_by,
        )
    if section_type == "mandate_context":
        return mandate_context_section_payload(
            mandate_id=mandate_id,
            mandate_twin=mandate_twin,
            mandate_health=mandate_health,
            mandate_evidence_gap_codes=mandate_evidence_gap_codes,
        )
    if section_type == "source_readiness":
        return source_readiness_section_payload(
            result=result,
        )
    if section_type == "selected_alternative":
        return selected_alternative_section_payload(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
        )
    return None


def pre_run_section_payload(
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
) -> SectionPayload | None:
    core_payload = pre_run_core_section_payload(
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

    source_analytics_payload = pre_run_source_analytics_payload(
        section_type=section_type,
        source_analytics=source_analytics,
    )
    if source_analytics_payload is not None:
        return source_analytics_payload

    adapter_payload = pre_run_adapter_payload(section_type=section_type)
    if adapter_payload is not None:
        return adapter_payload

    return None


def run_bound_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    selected_alternative: ConstructionAlternative | None,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> SectionPayload | None:
    run_state_payload = run_state_section_payload(section_type=section_type, result=result)
    if run_state_payload is not None:
        return run_state_payload

    run_policy_payload = run_policy_section_payload(
        section_type=section_type,
        result=result,
        selected_alternative=selected_alternative,
    )
    if run_policy_payload is not None:
        return run_policy_payload

    if section_type == "turnover_and_cost":
        return turnover_and_cost_section_payload(
            selected_alternative=selected_alternative,
            source_analytics=source_analytics,
        )

    run_diagnostics_payload = run_diagnostics_section_payload(
        section_type=section_type,
        result=result,
    )
    if run_diagnostics_payload is not None:
        return run_diagnostics_payload

    return None


def run_source_context_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> SectionPayload | None:
    if section_type == "scenario_and_regime_evidence":
        return source_analytics_section_payload(
            source_analytics=source_analytics,
            family="regime_stress",
            missing_summary="Scenario/regime authority context is not attached.",
            missing_reason_code="DPM_SCENARIO_CONTEXT_MISSING",
            sort_reason_codes=True,
        )
    if section_type == "eligibility_and_restrictions":
        return eligibility_and_restrictions_section_payload(
            result=result,
            source_analytics=source_analytics,
        )
    return None


def section_payload(
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
) -> SectionPayload:
    _ = run_artifact_hash
    pre_run_payload = pre_run_section_payload(
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

    return run_present_section_payload(
        section_type=section_type,
        result=result,
        run=run,
        selected_alternative=selected_alternative,
        selection=selection,
        source_ref_count=source_ref_count,
        source_analytics=source_analytics,
        workflow_decisions=workflow_decisions,
    )


def run_present_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    source_ref_count: int,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> SectionPayload:
    run_bound_payload = run_bound_section_payload(
        section_type=section_type,
        result=result,
        selected_alternative=selected_alternative,
        source_analytics=source_analytics,
    )
    if run_bound_payload is not None:
        return run_bound_payload

    run_source_context_payload = run_source_context_section_payload(
        section_type=section_type,
        result=result,
        source_analytics=source_analytics,
    )
    if run_source_context_payload is not None:
        return run_source_context_payload

    governance_payload = proof_pack_governance_section_payload(
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
