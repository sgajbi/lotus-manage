"""Report handoff adapters for RFC-0041 rebalance waves."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
)

WAVE_REPORT_INPUT_CONTRACT_VERSION = "1.0"
WAVE_REPORT_INPUT_REF_TYPE = "DPM_WAVE_REPORT_INPUT"


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
    redaction_policy: str = Field(description="Redaction policy applied to report input.")
    external_execution_claimed: bool = Field(
        description="Always false until an external OMS/execution owner is implemented."
    )
    evidence_ref: DpmWaveReportEvidenceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical report-input hash.")


def build_wave_report_input(
    *,
    wave: DpmRebalanceWave,
    supportability: dict[str, Any],
    proof_pack_posture: dict[str, Any],
) -> DpmWaveReportInput:
    wave_payload = wave.model_dump(mode="json")
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
        redaction_policy="NO_RAW_PAYLOADS",
        external_execution_claimed=bool(proof_pack_posture.get("external_execution_claimed")),
        evidence_ref=DpmWaveReportEvidenceRef(
            ref_type=WAVE_REPORT_INPUT_REF_TYPE,
            ref_id=f"{wave.wave_id}:{WAVE_REPORT_INPUT_REF_TYPE.lower()}",
            source_system="lotus-manage",
            content_hash=None,
        ),
        content_hash="",
    ).model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmWaveReportInput.model_validate(payload)


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
