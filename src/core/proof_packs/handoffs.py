"""Report and AI handoff adapters for RFC-0040 proof packs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs.markdown import render_proof_pack_markdown
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSourceRef,
    ProofPackSectionState,
    ProofPackSectionType,
    ProofPackStatus,
)

HANDOFF_CONTRACT_VERSION = "1.0"
REPORT_INPUT_REF_TYPE = "DPM_PROOF_PACK_REPORT_INPUT"
AI_EVIDENCE_REF_TYPE = "DPM_PROOF_PACK_AI_EVIDENCE_INPUT"
AI_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "account_number",
        "client_name",
        "client_id",
        "email",
        "phone",
        "raw_payload",
        "raw_request",
        "raw_response",
        "secret",
        "ssn",
        "token",
    }
)


class DpmProofPackReportSection(BaseModel):
    section_id: str = Field(description="Proof-pack section identifier.")
    section_type: ProofPackSectionType = Field(description="Proof-pack section type.")
    state: ProofPackSectionState = Field(description="Section supportability state.")
    title: str = Field(description="Business title.")
    summary: str = Field(description="Business-readable section summary.")
    reason_codes: list[str] = Field(description="Reason codes for degraded or blocked state.")
    facts: dict[str, Any] = Field(description="Report-safe section facts.")
    metrics: dict[str, Any] = Field(description="Report-safe section metrics.")
    evidence_refs: list[DpmProofPackEvidenceRef] = Field(description="Section evidence refs.")
    source_refs: list[DpmProofPackSourceRef] = Field(description="Section source refs.")
    content_hash: str = Field(description="Canonical section hash.")


class DpmProofPackReportInput(BaseModel):
    contract_version: str = Field(description="Report-input contract version.")
    proof_pack_id: str = Field(description="Source proof-pack identifier.")
    proof_pack_content_hash: str = Field(description="Canonical source proof-pack hash.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(description="Mandate identifier when available.")
    as_of_date: str = Field(description="Business as-of date.")
    generated_at: str = Field(description="Deterministic handoff generation timestamp.")
    report_title: str = Field(description="Suggested report title.")
    report_audience: list[str] = Field(description="Intended report audiences.")
    decision_summary: dict[str, Any] = Field(description="Decision summary payload.")
    supportability: dict[str, Any] = Field(description="Proof-pack supportability payload.")
    sections: list[DpmProofPackReportSection] = Field(description="Report section payloads.")
    markdown_summary: str = Field(description="Deterministic Markdown summary.")
    source_hashes: dict[str, str] = Field(description="Proof-pack source hashes.")
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = Field(
        default=None,
        description=(
            "Optional Manage-owned portfolio-memory lineage context for downstream reports. "
            "This context carries its own content hash and is excluded from the proof-pack "
            "report-input evidence hash to avoid recursive report-input lineage."
        ),
    )
    redaction_policy: str = Field(description="Redaction policy applied to report input.")
    evidence_ref: DpmProofPackEvidenceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical report-input hash.")


class DpmProofPackAiEvidenceSection(BaseModel):
    section_id: str = Field(description="Proof-pack section identifier.")
    section_type: ProofPackSectionType = Field(description="Proof-pack section type.")
    state: ProofPackSectionState = Field(description="Section supportability state.")
    summary: str = Field(description="Business-readable section summary.")
    reason_codes: list[str] = Field(description="Reason codes for this section.")
    bounded_facts: dict[str, Any] = Field(description="AI-safe bounded facts.")
    bounded_metrics: dict[str, Any] = Field(description="AI-safe bounded metrics.")
    content_hash: str = Field(description="Canonical section hash.")


class DpmProofPackAiEvidenceInput(BaseModel):
    contract_version: str = Field(description="AI-evidence input contract version.")
    proof_pack_id: str = Field(description="Source proof-pack identifier.")
    proof_pack_content_hash: str = Field(description="Canonical source proof-pack hash.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(description="Mandate identifier when available.")
    as_of_date: str = Field(description="Business as-of date.")
    generated_at: str = Field(description="Deterministic handoff generation timestamp.")
    permitted_use: str = Field(description="Permitted AI use for this evidence.")
    forbidden_actions: list[str] = Field(description="Actions the AI layer must not perform.")
    forbidden_fields_removed: list[str] = Field(description="Forbidden field names removed.")
    decision_summary: dict[str, Any] = Field(description="AI-safe decision summary.")
    supportability_status: ProofPackStatus = Field(description="Proof-pack supportability status.")
    reason_codes: list[str] = Field(description="Aggregate proof-pack reason codes.")
    sections: list[DpmProofPackAiEvidenceSection] = Field(description="AI-safe evidence sections.")
    source_refs: list[DpmProofPackSourceRef] = Field(description="AI-safe source references.")
    evidence_ref: DpmProofPackEvidenceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical AI-evidence input hash.")


def build_report_input(
    proof_pack: DpmPreTradeProofPack,
    *,
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = None,
) -> DpmProofPackReportInput:
    payload = DpmProofPackReportInput(
        contract_version=HANDOFF_CONTRACT_VERSION,
        proof_pack_id=proof_pack.proof_pack_id,
        proof_pack_content_hash=proof_pack.content_hash,
        portfolio_id=proof_pack.portfolio_id,
        mandate_id=proof_pack.mandate_id,
        as_of_date=proof_pack.as_of_date,
        generated_at=proof_pack.created_at.isoformat(),
        report_title=f"Pre-Trade Proof Pack - {proof_pack.portfolio_id}",
        report_audience=[
            "portfolio_manager",
            "investment_control",
            "compliance",
            "operations",
            "audit",
        ],
        decision_summary=proof_pack.decision_summary.model_dump(mode="json"),
        supportability=proof_pack.supportability.model_dump(mode="json"),
        sections=[
            DpmProofPackReportSection(
                section_id=section.section_id,
                section_type=section.section_type,
                state=section.state,
                title=section.title,
                summary=section.summary,
                reason_codes=section.reason_codes,
                facts=section.facts,
                metrics=section.metrics,
                evidence_refs=section.evidence_refs,
                source_refs=section.source_refs,
                content_hash=section.content_hash,
            )
            for section in proof_pack.sections
        ],
        markdown_summary=render_proof_pack_markdown(proof_pack),
        source_hashes=proof_pack.source_hashes,
        portfolio_memory_context=portfolio_memory_context,
        redaction_policy="NO_RAW_PAYLOADS",
        evidence_ref=_placeholder_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            proof_pack_id=proof_pack.proof_pack_id,
        ),
        content_hash="",
    ).model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(
        strip_keys(payload, exclude={"content_hash", "portfolio_memory_context"})
    )
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmProofPackReportInput.model_validate(payload)


def build_ai_evidence_input(proof_pack: DpmPreTradeProofPack) -> DpmProofPackAiEvidenceInput:
    removed: set[str] = set()
    sections = [
        DpmProofPackAiEvidenceSection(
            section_id=section.section_id,
            section_type=section.section_type,
            state=section.state,
            summary=section.summary,
            reason_codes=section.reason_codes,
            bounded_facts=_sanitize_for_ai(section.facts, removed),
            bounded_metrics=_sanitize_for_ai(section.metrics, removed),
            content_hash=section.content_hash,
        )
        for section in proof_pack.sections
    ]
    decision_summary = _sanitize_for_ai(
        proof_pack.decision_summary.model_dump(mode="json"), removed
    )
    payload = DpmProofPackAiEvidenceInput(
        contract_version=HANDOFF_CONTRACT_VERSION,
        proof_pack_id=proof_pack.proof_pack_id,
        proof_pack_content_hash=proof_pack.content_hash,
        portfolio_id=proof_pack.portfolio_id,
        mandate_id=proof_pack.mandate_id,
        as_of_date=proof_pack.as_of_date,
        generated_at=proof_pack.created_at.isoformat(),
        permitted_use="Draft support-only PM, compliance, and operations narratives from evidence.",
        forbidden_actions=[
            "place_orders",
            "approve_rebalance",
            "override_controls",
            "invent_missing_evidence",
            "score_portfolio_manager",
            "contact_client",
            "generate_client_message",
        ],
        forbidden_fields_removed=sorted(removed),
        decision_summary=decision_summary,
        supportability_status=proof_pack.supportability.status,
        reason_codes=proof_pack.supportability.reason_codes,
        sections=sections,
        source_refs=_dedupe_source_refs(proof_pack),
        evidence_ref=_placeholder_ref(
            ref_type=AI_EVIDENCE_REF_TYPE,
            proof_pack_id=proof_pack.proof_pack_id,
        ),
        content_hash="",
    ).model_dump(mode="json")
    assert_no_ai_forbidden_fields(payload)
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmProofPackAiEvidenceInput.model_validate(payload)


def assert_no_ai_forbidden_fields(payload: Any) -> None:
    found = sorted(_find_forbidden_field_names(payload))
    if found:
        raise ValueError(f"DPM_PROOF_PACK_AI_FORBIDDEN_FIELDS:{','.join(found)}")


def _sanitize_for_ai(value: Any, removed: set[str]) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in AI_FORBIDDEN_FIELD_NAMES:
                removed.add(key.lower())
                continue
            sanitized[key] = _sanitize_for_ai(item, removed)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_ai(item, removed) for item in value]
    return value


def _find_forbidden_field_names(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in AI_FORBIDDEN_FIELD_NAMES:
                found.add(key.lower())
            found.update(_find_forbidden_field_names(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_forbidden_field_names(item))
    return found


def _dedupe_source_refs(proof_pack: DpmPreTradeProofPack) -> list[DpmProofPackSourceRef]:
    refs_by_key: dict[tuple[str, str, str], DpmProofPackSourceRef] = {}
    for section in proof_pack.sections:
        for ref in section.source_refs:
            refs_by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return list(refs_by_key.values())


def _placeholder_ref(*, ref_type: str, proof_pack_id: str) -> DpmProofPackEvidenceRef:
    return DpmProofPackEvidenceRef(
        ref_type=ref_type,
        ref_id=f"{proof_pack_id}:{ref_type.lower()}",
        source_system="lotus-manage",
        content_hash=None,
    )
