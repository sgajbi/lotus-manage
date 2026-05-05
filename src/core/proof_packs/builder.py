"""Pure RFC-0040 proof-pack builders."""

from datetime import datetime, timezone
from typing import Any, cast

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.models import (
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

_SECTION_ORDER: list[ProofPackSectionType] = list(_SECTION_TITLES)


class ProofPackSourceValidationError(ValueError):
    pass


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
) -> DpmPreTradeProofPack:
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
    if selection is not None and selection.alternative_id != selected_alternative_id:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_SELECTION_MISMATCH")
    if selection is not None and selection.alternative_set_id != alternative_set.alternative_set_id:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_SET_MISMATCH")

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
    )


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
) -> DpmPreTradeProofPack:
    resolved_created_at = created_at or datetime.now(timezone.utc)
    result = RebalanceResult.model_validate(run.result_json) if run is not None else None
    run_artifact = build_dpm_run_artifact(run=run) if run is not None else None
    source_hashes = _source_hashes(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )
    portfolio_id = _resolve_portfolio_id(run=run, alternative_set=alternative_set)
    resolved_correlation_id = (
        correlation_id
        or (
            selection.correlation_id if selection is not None and selection.correlation_id else None
        )
        or (run.correlation_id if run is not None else None)
        or f"proof-pack-{resolved_created_at.strftime('%Y%m%d%H%M%S')}"
    )
    proof_pack_id = _proof_pack_id(
        source_type=source_type,
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
    )
    generated_at = resolved_created_at.isoformat()
    source_refs = _source_refs(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        source_hashes=source_hashes,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )

    sections = [
        _build_section(
            section_type=section_type,
            generated_at=generated_at,
            result=result,
            run=run,
            run_artifact_hash=(
                run_artifact.evidence.hashes.artifact_hash if run_artifact is not None else None
            ),
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
            source_refs=source_refs,
            source_ref_count=len(source_refs),
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
    supportability = _supportability(sections)
    decision_summary = _decision_summary(
        source_type=source_type,
        result=result,
        selected_alternative=selected_alternative,
        reason=reason,
        supportability=supportability,
    )
    timeline = _decision_timeline(
        proof_pack_id=proof_pack_id,
        generated_at=generated_at,
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
        proof_pack_id=proof_pack_id,
        proof_pack_version=PROOF_PACK_VERSION,
        portfolio_id=portfolio_id,
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
        source_hashes=source_hashes,
        created_at=resolved_created_at,
        created_by=created_by,
        correlation_id=resolved_correlation_id,
    )
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
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]:
    if section_type == "decision_summary":
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
    if section_type == "mandate_context":
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
    if section_type == "source_readiness":
        source_state = result.lineage.source_supportability_state if result is not None else None
        if result is None:
            return ("BLOCKED", "No source run is available.", {}, {}, ["DPM_SOURCE_RUN_MISSING"])
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
    if section_type == "selected_alternative":
        if selected_alternative is None:
            return (
                "DEGRADED",
                "Direct-run proof pack has no selected construction alternative.",
                {},
                {},
                ["DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE"],
            )
        selected_state = (
            "READY"
            if selected_alternative.method_status == "READY"
            else cast(ProofPackSectionState, str(selected_alternative.method_status))
        )
        return (
            selected_state,
            "Selected construction alternative captured with method and trace evidence.",
            {
                "alternative_set_id": alternative_set.alternative_set_id
                if alternative_set
                else None,
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
            },
            selected_alternative.comparison_metrics.model_dump(mode="json"),
            []
            if selected_alternative.method_status == "READY"
            else ["DPM_SELECTED_METHOD_NOT_READY"],
        )
    if section_type == "risk_impact":
        return (
            "DEGRADED",
            "No risk-authoritative enrichment is attached to this first-wave proof pack.",
            {},
            {},
            ["DPM_RISK_AUTHORITY_CONTEXT_MISSING"],
        )
    if section_type == "performance_context":
        return (
            "DEGRADED",
            "No performance-authoritative benchmark context is attached.",
            {},
            {},
            ["DPM_PERFORMANCE_CONTEXT_MISSING"],
        )
    if section_type == "sustainability_controls":
        return (
            "DEGRADED",
            "Sustainability authority is not implemented for this proof pack.",
            {},
            {},
            ["DPM_SUSTAINABILITY_CONTEXT_MISSING"],
        )
    if section_type == "reporting_refs":
        return (
            "READY",
            "Report input adapter is available; generated refs are appended outside the immutable proof-pack body.",
            {"adapter_contract": "DpmProofPackReportInput"},
            {},
            [],
        )
    if section_type == "ai_refs":
        return (
            "READY",
            "AI evidence input adapter is available with forbidden-action and forbidden-field guardrails.",
            {"adapter_contract": "DpmProofPackAiEvidenceInput"},
            {},
            [],
        )
    if result is None:
        return ("BLOCKED", "Source rebalance run is missing.", {}, {}, ["DPM_SOURCE_RUN_MISSING"])
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
    if section_type == "after_state":
        return (
            "READY" if result.status != "BLOCKED" else "BLOCKED",
            "After-state simulation summary captured from source run.",
            {"after_summary": result.after_simulated.model_dump(mode="json")},
            {"position_count": len(result.after_simulated.positions)},
            [] if result.status != "BLOCKED" else ["DPM_AFTER_STATE_BLOCKED"],
        )
    if section_type == "drift_impact":
        if selected_alternative is not None:
            metrics = selected_alternative.comparison_metrics.model_dump(mode="json")
            return (
                "READY",
                "Drift impact captured from construction comparison metrics.",
                {},
                metrics,
                [],
            )
        return (
            "DEGRADED",
            "Direct-run proof has no construction comparison drift trace.",
            {},
            {},
            ["DPM_DRIFT_COMPARISON_UNAVAILABLE"],
        )
    if section_type == "tax_impact":
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
    if section_type == "turnover_and_cost":
        metrics = (
            selected_alternative.comparison_metrics.model_dump(mode="json")
            if selected_alternative
            else {}
        )
        turnover_state: ProofPackSectionState = "READY" if metrics else "DEGRADED"
        return (
            turnover_state,
            "Turnover and cost evidence captured when construction metrics are available.",
            {},
            metrics,
            [] if metrics else ["DPM_TURNOVER_COST_METRICS_MISSING"],
        )
    if section_type == "liquidity_and_cash":
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
    if section_type == "fx_funding_plan":
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
    if section_type == "currency_overlay_evidence":
        return (
            "DEGRADED",
            "Currency-overlay authority context is not attached.",
            {},
            {},
            ["DPM_CURRENCY_OVERLAY_CONTEXT_MISSING"],
        )
    if section_type == "scenario_and_regime_evidence":
        return (
            "DEGRADED",
            "Scenario/regime authority context is not attached.",
            {},
            {},
            ["DPM_SCENARIO_CONTEXT_MISSING"],
        )
    if section_type == "eligibility_and_restrictions":
        excluded = result.universe.excluded
        return (
            "READY" if not excluded else "PENDING_REVIEW",
            "Eligibility and restriction evidence captured from source run universe.",
            {"excluded": [item.model_dump(mode="json") for item in excluded]},
            {"excluded_count": len(excluded)},
            ["DPM_UNIVERSE_EXCLUSIONS_PRESENT"] if excluded else [],
        )
    if section_type == "rule_results":
        failed = [rule for rule in result.rule_results if rule.status == "FAIL"]
        return (
            "BLOCKED" if any(rule.severity == "HARD" for rule in failed) else "READY",
            "Rule results captured from manage policy engine.",
            {"rule_results": [rule.model_dump(mode="json") for rule in result.rule_results]},
            {"fail_count": len(failed)},
            [rule.reason_code for rule in failed],
        )
    if section_type == "approval_requirements":
        gate = result.gate_decision
        workflow_facts = [
            decision.model_dump(mode="json")
            for decision in sorted(workflow_decisions, key=lambda item: item.decided_at)
        ]
        approval_state: ProofPackSectionState = "READY"
        if result.status == "PENDING_REVIEW" or (gate and gate.gate.endswith("REQUIRED")):
            approval_state = "PENDING_REVIEW"
        if result.status == "BLOCKED" or (gate and gate.gate == "BLOCKED"):
            approval_state = "BLOCKED"
        return (
            approval_state,
            "Approval posture captured from run status and gate decision.",
            {
                "gate_decision": gate.model_dump(mode="json") if gate else None,
                "workflow_decisions": workflow_facts,
            },
            {"workflow_decision_count": len(workflow_facts)},
            [reason.reason_code for reason in gate.reasons] if gate else [],
        )
    if section_type == "operations_handoff":
        return (
            "READY" if result.status == "READY" else "PENDING_REVIEW",
            "Operations handoff reflects current pre-trade readiness.",
            {"run_status": result.status},
            {},
            [] if result.status == "READY" else ["DPM_OPERATIONS_REVIEW_REQUIRED"],
        )
    if section_type == "decision_timeline":
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
    if section_type == "lineage":
        return (
            "READY" if run is not None else "BLOCKED",
            "Lineage identifiers captured from source run and source artifacts.",
            result.lineage.model_dump(mode="json") if result else {},
            {"source_ref_count": source_ref_count},
            [] if run is not None else ["DPM_LINEAGE_RUN_MISSING"],
        )
    if section_type == "supportability":
        return ("READY", "Supportability summary is generated for every proof pack.", {}, {}, [])
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
    events: list[DpmProofPackDecisionTimelineEvent] = []
    if run is not None:
        events.append(
            DpmProofPackDecisionTimelineEvent(
                event_id=f"{run.rebalance_run_id}:run_created",
                event_type="REBALANCE_RUN_CREATED",
                event_time=run.created_at.isoformat(),
                actor="lotus-manage",
                source_system="lotus-manage",
                status=str(run.result_json.get("status", "UNKNOWN")),
                reason_codes=[],
            )
        )
    if alternative_set is not None:
        events.append(
            DpmProofPackDecisionTimelineEvent(
                event_id=f"{alternative_set.alternative_set_id}:generated",
                event_type="ALTERNATIVE_SET_GENERATED",
                event_time=alternative_set.generated_at.isoformat(),
                actor="lotus-manage",
                source_system="lotus-manage",
                status=str(alternative_set.status),
                reason_codes=[],
            )
        )
    if selected_alternative is not None:
        events.append(
            DpmProofPackDecisionTimelineEvent(
                event_id=f"{selected_alternative.alternative_id}:selected",
                event_type="SELECTED_ALTERNATIVE",
                event_time=selection.selected_at.isoformat() if selection else generated_at,
                actor=selection.actor_id if selection else created_by,
                source_system="lotus-manage",
                status=str(selected_alternative.method_status),
                reason_codes=[selection.reason_code] if selection else [],
            )
        )
    for decision in workflow_decisions:
        events.append(
            DpmProofPackDecisionTimelineEvent(
                event_id=f"{decision.decision_id}:workflow_decision",
                event_type="WORKFLOW_DECISION",
                event_time=decision.decided_at.isoformat(),
                actor=decision.actor_id,
                source_system="lotus-manage",
                status=str(decision.action),
                reason_codes=[decision.reason_code],
            )
        )
    events.append(
        DpmProofPackDecisionTimelineEvent(
            event_id=f"{proof_pack_id}:generated",
            event_type="PROOF_PACK_GENERATED",
            event_time=generated_at,
            actor=created_by,
            source_system="lotus-manage",
            status=source_type,
            reason_codes=[],
        )
    )
    event_rank = {
        "REBALANCE_RUN_CREATED": 0,
        "ALTERNATIVE_SET_GENERATED": 1,
        "SELECTED_ALTERNATIVE": 2,
        "WORKFLOW_DECISION": 3,
        "PROOF_PACK_GENERATED": 4,
    }
    return DpmProofPackDecisionTimeline(
        events=sorted(
            events,
            key=lambda event: (
                event.event_time,
                event_rank.get(event.event_type, 99),
                event.event_id,
            ),
        )
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
        result = RebalanceResult.model_validate(run.result_json)
        refs.append(
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="DPM_REBALANCE_RUN",
                source_id=run.rebalance_run_id,
                supportability_state=result.status,
                content_hash=source_hashes.get("rebalance_run"),
            )
        )
    if alternative_set is not None:
        refs.append(
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
                source_id=alternative_set.alternative_set_id,
                supportability_state=str(alternative_set.status),
                content_hash=source_hashes.get("alternative_set"),
            )
        )
    if selected_alternative is not None:
        refs.append(
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE",
                source_id=selected_alternative.alternative_id,
                supportability_state=str(selected_alternative.method_status),
                content_hash=source_hashes.get("selected_alternative"),
            )
        )
    if mandate_twin is not None:
        refs.append(
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="DPM_MANDATE_DIGITAL_TWIN",
                source_id=mandate_twin.mandate_id,
                supportability_state="READY" if not mandate_twin.field_gap_codes else "DEGRADED",
                content_hash=source_hashes.get("mandate_twin"),
            )
        )
    if mandate_health is not None:
        refs.append(
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
                source_id=mandate_health.health_snapshot_id,
                supportability_state=mandate_health.health_state.value,
                content_hash=source_hashes.get("mandate_health"),
            )
        )
    return refs


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
        return run.rebalance_run_id.replace("rr_", "dpp_", 1)
    if (
        source_type == "SELECTED_ALTERNATIVE"
        and alternative_set is not None
        and selected_alternative is not None
    ):
        return f"dpp_{alternative_set.alternative_set_id}_{selected_alternative.alternative_id}"
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")
