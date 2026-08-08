"""Report handoff adapters for RFC-0041 rebalance waves."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.waves.campaign_discovery import (
    GLOBAL_CAMPAIGN_UNIVERSE_BLOCKED_CAPABILITIES,
    GLOBAL_CAMPAIGN_UNIVERSE_PROMOTION_REQUIREMENTS,
    GLOBAL_CAMPAIGN_UNIVERSE_REQUIRED_SOURCE_PRODUCT,
)
from src.core.waves.models import (
    DpmWaveClientCommunicationBoundaryEvidence,
    DpmWaveExternalExecutionBoundaryEvidence,
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
    normalize_dpm_wave_source_ref_collections_for_hash,
)

WAVE_REPORT_INPUT_CONTRACT_VERSION = "1.0"
WAVE_REPORT_INPUT_REF_TYPE = "DPM_WAVE_REPORT_INPUT"


class DpmWaveReportInputBoundaryError(ValueError):
    """Raised when report-input evidence would cross an unsupported ownership boundary."""


class DpmWaveReportEvidenceRef(BaseModel):
    ref_type: str = Field(description="Evidence reference type.")
    ref_id: str = Field(description="Evidence reference identifier.")
    source_system: str = Field(description="System that owns this evidence reference.")
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
    )


class DpmWaveReportItem(BaseModel):
    wave_item_id: str = Field(description="Stable wave item identifier.")
    portfolio_id: str = Field(description="Affected portfolio identifier.")
    mandate_id: str | None = Field(description="Mandate identifier when available.")
    model_portfolio_id: str | None = Field(description="Model portfolio identifier when available.")
    state: str = Field(description="Current wave item state.")
    reason_codes: list[str] = Field(description="Bounded item reason codes.")
    selected_alternative_id: str | None = Field(
        description="Selected RFC-0039 construction alternative when available."
    )
    proof_pack_id: str | None = Field(description="Linked RFC-0040 proof-pack when available.")
    proof_pack_state: str | None = Field(description="Linked proof-pack posture when available.")
    source_refs: list[DpmWaveSourceRef] = Field(description="Source refs for this wave item.")
    diagnostics: dict[str, Any] = Field(description="Bounded report-safe diagnostics.")


class DpmWaveReportEvent(BaseModel):
    event_id: str = Field(description="Wave event identifier.")
    event_type: str = Field(description="Wave event type.")
    from_state: str | None = Field(description="Previous wave state when available.")
    to_state: str = Field(description="Resulting wave state.")
    actor_id: str = Field(description="Actor that caused the event.")
    reason_code: str = Field(description="Bounded event reason code.")
    correlation_id: str = Field(description="Event correlation id.")
    created_at: str = Field(description="UTC event timestamp.")
    metadata: dict[str, Any] = Field(description="Bounded report-safe event metadata.")


class DpmWaveReportInput(BaseModel):
    contract_version: str = Field(description="Report-input contract version.")
    wave_id: str = Field(description="Source rebalance wave identifier.")
    wave_content_hash: str = Field(description="Canonical source wave hash.")
    wave_state: str = Field(description="Current source wave state.")
    trigger_type: str = Field(description="Wave trigger type.")
    trigger_id: str = Field(description="Wave trigger identifier.")
    trigger_rationale: str = Field(description="Business rationale for the wave.")
    as_of_date: str = Field(description="Business as-of date.")
    generated_at: str = Field(description="Deterministic handoff generation timestamp.")
    report_title: str = Field(description="Suggested report title.")
    report_audience: list[str] = Field(description="Intended report audiences.")
    aggregate_metrics: dict[str, Any] = Field(description="Wave aggregate metrics.")
    supportability: dict[str, Any] = Field(description="Wave supportability payload.")
    proof_pack_posture: dict[str, Any] = Field(description="Wave proof-pack posture payload.")
    items: list[DpmWaveReportItem] = Field(description="Report-safe wave item payloads.")
    events: list[DpmWaveReportEvent] = Field(description="Report-safe event timeline.")
    handoff_refs: list[DpmWaveHandoffRef] = Field(description="Internal operations handoff refs.")
    source_refs: list[DpmWaveSourceRef] = Field(description="Deduplicated source refs.")
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = Field(
        default=None,
        description=(
            "Optional Manage-owned portfolio-memory lineage context for downstream reports. "
            "This context carries its own content hash and is excluded from the wave report-input "
            "evidence hash to avoid recursive report-input lineage."
        ),
    )
    redaction_policy: str = Field(description="Redaction policy applied to report input.")
    external_execution_boundary: DpmWaveExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed evidence proving this report input stops at internal "
            "operations handoff and does not cross into OMS execution."
        )
    )
    client_communication_boundary: DpmWaveClientCommunicationBoundaryEvidence = Field(
        description=(
            "Structured fail-closed evidence proving this report input stops at internal "
            "operations handoff and does not cross into client communication, client approval, "
            "or delivery confirmation."
        )
    )
    campaign_universe_boundary: "DpmWaveCampaignUniverseBoundaryEvidence | None" = Field(
        default=None,
        description=(
            "Structured fail-closed evidence for BULK_REVIEW_CAMPAIGN waves proving Manage uses "
            "persisted source-backed campaign-definition candidates only and does not discover "
            "the global portfolio universe, recalculate source facts, or recompute membership."
        ),
    )
    external_execution_claimed: bool = Field(
        description="Always false until an external OMS/execution owner is implemented."
    )
    evidence_ref: DpmWaveReportEvidenceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical report-input hash.")


class DpmWaveCampaignUniverseBoundaryEvidence(BaseModel):
    boundary_id: Literal["DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY"] = Field(
        default="DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY",
        description="Stable unsupported global portfolio-universe campaign boundary identifier.",
    )
    supportability_state: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Fail-closed supportability state for global campaign universe discovery.",
    )
    source_system: Literal["lotus-manage"] = Field(
        default="lotus-manage",
        description="System preserving the unsupported boundary evidence.",
    )
    source_product_name: Literal["DpmWaveReportInput"] = Field(
        default="DpmWaveReportInput",
        description="Manage-owned report-input product that consumes persisted wave truth only.",
    )
    source_product_version: Literal["v1"] = Field(
        default="v1",
        description="Boundary evidence product version.",
    )
    discovery_mode: Literal["PERSISTED_DEFINITION_ONLY"] = Field(
        default="PERSISTED_DEFINITION_ONLY",
        description=(
            "Manage report-input handoff mode for campaign waves. It only preserves the already "
            "persisted campaign candidate set represented by the wave."
        ),
    )
    source_scope: Literal["PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES"] = Field(
        default="PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES",
        description="Supported candidate source scope for this handoff.",
    )
    global_portfolio_universe_discovery: Literal["UNSUPPORTED"] = Field(
        default="UNSUPPORTED",
        description="Manage report inputs do not scan or discover the bank-wide portfolio universe.",
    )
    global_portfolio_universe_owner_posture: Literal["DEFERRED_SOURCE_OWNER"] = Field(
        default="DEFERRED_SOURCE_OWNER",
        description="Future bank-wide campaign discovery requires an explicit source owner.",
    )
    required_source_product: Literal["GlobalPortfolioUniverseCampaignCandidateSet:v1"] = Field(
        default="GlobalPortfolioUniverseCampaignCandidateSet:v1",
        description="Source product required before global campaign universe discovery can promote.",
    )
    candidate_source_ref_posture: Literal["SOURCE_BACKED", "NO_CANDIDATES"] = Field(
        description="Whether the persisted campaign wave has candidate source references."
    )
    source_systems: list[str] = Field(
        description="Sorted source systems represented by trigger and item source references.",
        examples=[["lotus-core", "lotus-manage"]],
    )
    blocked_capabilities: list[str] = Field(
        description="Global campaign discovery capabilities blocked by this boundary evidence.",
        examples=[["bank_wide_portfolio_universe_scan", "membership_recomputation"]],
    )
    promotion_requirements: list[str] = Field(
        description="Requirements before global portfolio-universe campaign discovery can promote.",
        examples=[
            [
                "certified_source_owner",
                "GlobalPortfolioUniverseCampaignCandidateSet:v1",
            ]
        ],
    )
    operating_boundaries: list[str] = Field(
        description="Machine-readable no-claim boundaries for downstream report consumers.",
        examples=[["NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY", "NO_MEMBERSHIP_RECOMPUTATION"]],
    )
    summary: str = Field(description="Operator-facing no-global-campaign-universe summary.")
    content_hash: str = Field(description="Canonical hash of the boundary evidence payload.")


def build_wave_report_input(
    *,
    wave: DpmRebalanceWave,
    supportability: dict[str, Any],
    proof_pack_posture: dict[str, Any],
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = None,
) -> DpmWaveReportInput:
    if bool(proof_pack_posture.get("external_execution_claimed")):
        raise DpmWaveReportInputBoundaryError(
            "Wave report input cannot propagate external execution claims; "
            "lotus-manage only owns internal operations handoff evidence."
        )
    wave_payload = wave.model_dump(mode="json")
    normalize_dpm_wave_source_ref_collections_for_hash(wave_payload)
    wave_content_hash = hash_canonical_payload(wave_payload)
    payload = DpmWaveReportInput(
        contract_version=WAVE_REPORT_INPUT_CONTRACT_VERSION,
        wave_id=wave.wave_id,
        wave_content_hash=wave_content_hash,
        wave_state=wave.state,
        trigger_type=wave.trigger.trigger_type,
        trigger_id=wave.trigger.trigger_id,
        trigger_rationale=wave.trigger.rationale,
        as_of_date=wave.as_of_date,
        generated_at=wave.created_at.isoformat(),
        report_title=f"Rebalance Wave Evidence - {wave.wave_id}",
        report_audience=[
            "portfolio_manager",
            "chief_investment_office",
            "investment_control",
            "operations",
            "audit",
        ],
        aggregate_metrics=wave.aggregate_metrics.model_dump(mode="json"),
        supportability=supportability,
        proof_pack_posture=proof_pack_posture,
        items=[_report_item(item) for item in wave.items],
        events=[_report_event(event) for event in wave.events],
        handoff_refs=wave.handoff_refs,
        source_refs=_dedupe_source_refs(wave),
        portfolio_memory_context=portfolio_memory_context,
        redaction_policy="NO_RAW_PAYLOADS",
        external_execution_boundary=DpmWaveExternalExecutionBoundaryEvidence.model_validate(
            proof_pack_posture["external_execution_boundary"]
        ),
        client_communication_boundary=DpmWaveClientCommunicationBoundaryEvidence.model_validate(
            proof_pack_posture["client_communication_boundary"]
        ),
        campaign_universe_boundary=_campaign_universe_boundary(wave),
        external_execution_claimed=False,
        evidence_ref=DpmWaveReportEvidenceRef(
            ref_type=WAVE_REPORT_INPUT_REF_TYPE,
            ref_id=f"{wave.wave_id}:{WAVE_REPORT_INPUT_REF_TYPE.lower()}",
            source_system="lotus-manage",
            content_hash=None,
        ),
        content_hash="",
    ).model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(
        strip_keys(payload, exclude={"content_hash", "portfolio_memory_context"})
    )
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmWaveReportInput.model_validate(payload)


def _campaign_universe_boundary(
    wave: DpmRebalanceWave,
) -> DpmWaveCampaignUniverseBoundaryEvidence | None:
    if wave.trigger.trigger_type != "BULK_REVIEW_CAMPAIGN":
        return None
    source_refs = _dedupe_source_refs(wave)
    source_systems = sorted(
        {source_ref.source_system for source_ref in source_refs if source_ref.source_system.strip()}
    )
    payload: dict[str, Any] = {
        "boundary_id": "DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmWaveReportInput",
        "source_product_version": "v1",
        "discovery_mode": "PERSISTED_DEFINITION_ONLY",
        "source_scope": "PERSISTED_CAMPAIGN_DEFINITION_CANDIDATES",
        "global_portfolio_universe_discovery": "UNSUPPORTED",
        "global_portfolio_universe_owner_posture": "DEFERRED_SOURCE_OWNER",
        "required_source_product": GLOBAL_CAMPAIGN_UNIVERSE_REQUIRED_SOURCE_PRODUCT,
        "candidate_source_ref_posture": "SOURCE_BACKED" if source_refs else "NO_CANDIDATES",
        "source_systems": source_systems,
        "blocked_capabilities": list(GLOBAL_CAMPAIGN_UNIVERSE_BLOCKED_CAPABILITIES),
        "promotion_requirements": list(GLOBAL_CAMPAIGN_UNIVERSE_PROMOTION_REQUIREMENTS),
        "operating_boundaries": [
            "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
            "NO_SOURCE_FACT_RECALCULATION",
            "NO_MEMBERSHIP_RECOMPUTATION",
            "NO_ORDER_GENERATION",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        "summary": (
            "Bulk-review campaign wave report inputs preserve persisted campaign-definition "
            "candidate evidence only. They do not discover the global portfolio universe, "
            "recalculate source facts, recompute membership, generate orders, or claim OMS "
            "execution."
        ),
    }
    payload["content_hash"] = hash_canonical_payload(payload)
    return DpmWaveCampaignUniverseBoundaryEvidence.model_validate(payload)


def _report_item(item: DpmRebalanceWaveItem) -> DpmWaveReportItem:
    return DpmWaveReportItem(
        wave_item_id=item.wave_item_id,
        portfolio_id=item.portfolio_id,
        mandate_id=item.mandate_id,
        model_portfolio_id=item.model_portfolio_id,
        state=item.state,
        reason_codes=item.reason_codes,
        selected_alternative_id=item.selected_alternative_id,
        proof_pack_id=item.proof_pack_id,
        proof_pack_state=_optional_str(item.diagnostics.get("proof_pack_state")),
        source_refs=item.source_refs,
        diagnostics=item.diagnostics,
    )


def _report_event(event: DpmRebalanceWaveEvent) -> DpmWaveReportEvent:
    return DpmWaveReportEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        from_state=event.from_state,
        to_state=event.to_state,
        actor_id=event.actor_id,
        reason_code=event.reason_code,
        correlation_id=event.correlation_id,
        created_at=event.created_at.isoformat(),
        metadata=event.metadata,
    )


def _dedupe_source_refs(wave: DpmRebalanceWave) -> list[DpmWaveSourceRef]:
    refs_by_key: dict[tuple[str, str, str], DpmWaveSourceRef] = {}
    for ref in wave.trigger.source_refs:
        refs_by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    for item in wave.items:
        for ref in item.source_refs:
            refs_by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return list(refs_by_key.values())


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
