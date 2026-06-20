"""Proof-pack section assembly and canonical hashing helpers."""

from typing import Any

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSection,
    DpmProofPackSourceRef,
    ProofPackSectionState,
    ProofPackSectionType,
)

SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]

SECTION_TITLES: dict[ProofPackSectionType, str] = {
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

SECTION_ORDER: list[ProofPackSectionType] = list(SECTION_TITLES)


def finalize_proof_pack_content_hash(pack: DpmPreTradeProofPack) -> DpmPreTradeProofPack:
    payload = pack.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmPreTradeProofPack.model_validate(payload)


def build_section(
    *,
    section_type: ProofPackSectionType,
    generated_at: str,
    payload: SectionPayload,
    run_id: str | None,
    run_artifact_hash: str | None,
    source_refs: list[DpmProofPackSourceRef],
    source_supportability: dict[str, Any],
) -> DpmProofPackSection:
    state, summary, facts, metrics, reason_codes = payload
    section_payload = DpmProofPackSection(
        section_id=f"{section_type}",
        section_type=section_type,
        state=state,
        title=SECTION_TITLES[section_type],
        summary=summary,
        facts=facts,
        metrics=metrics,
        reason_codes=reason_codes,
        evidence_refs=_section_evidence_refs(
            run_id=run_id,
            run_artifact_hash=run_artifact_hash,
        ),
        source_refs=source_refs,
        source_supportability=source_supportability,
        generated_at=generated_at,
        content_hash="",
    ).model_dump(mode="json")
    section_payload["content_hash"] = hash_canonical_payload(
        strip_keys(section_payload, exclude={"content_hash"})
    )
    return DpmProofPackSection.model_validate(section_payload)


def _section_evidence_refs(
    *,
    run_id: str | None,
    run_artifact_hash: str | None,
) -> list[DpmProofPackEvidenceRef]:
    if run_id is None or run_artifact_hash is None:
        return []
    return [
        DpmProofPackEvidenceRef(
            ref_type="DPM_RUN_ARTIFACT",
            ref_id=run_id,
            source_system="lotus-manage",
            content_hash=run_artifact_hash,
        )
    ]
