from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.api.services import wave_service
from src.core.waves import DpmRebalanceWave
from src.core.waves.models import (
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveExternalExecutionBoundaryEvidence,
    DpmWaveHandoffRef,
)


class DpmWaveSupportabilityIssue(BaseModel):
    support_ref: str = Field(
        description="Opaque support reference that avoids portfolio or client identifiers.",
        examples=["wave:dwv_001:item:1"],
    )
    item_state: str = Field(description="Wave item workflow state.", examples=["SOURCE_BLOCKED"])
    severity: Literal["INFO", "WARNING", "CRITICAL"] = Field(
        description="Operator severity for this issue.",
        examples=["CRITICAL"],
    )
    source_owner: str = Field(
        description="Owning product or route responsible for remediation.",
        examples=["lotus-manage"],
    )
    reason_codes: list[str] = Field(
        description="Bounded reason codes explaining supportability posture.",
        examples=[["MANDATE_DIGITAL_TWIN_MISSING"]],
    )
    remediation_route: str = Field(
        description="Product-safe remediation route or action.",
        examples=["REPAIR_SOURCE_DATA"],
    )


class DpmWaveSupportabilityResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["SOURCE_CHECKED"])
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Bounded supportability state for the wave.",
        examples=["blocked"],
    )
    reason: str = Field(
        description="Bounded supportability reason.",
        examples=["wave_blocked_items"],
    )
    item_count: int = Field(description="Number of wave items inspected.", examples=[2])
    issue_counts: dict[str, int] = Field(
        description="Issue count by severity.",
        examples=[{"critical": 1, "warning": 0, "info": 1}],
    )
    issues: list[DpmWaveSupportabilityIssue] = Field(
        description=(
            "Product-safe issues without portfolio ids, client ids, raw requests, raw responses, "
            "secrets, or trace values."
        )
    )
    operator_actions: list[str] = Field(
        description="Deduplicated product-safe remediation actions.",
        examples=[["REPAIR_SOURCE_DATA", "RUN_WAVE_SIMULATION"]],
    )


class DpmWaveResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Previewed or durable rebalance wave.")
    durable: bool = Field(
        description="Whether this response was durably persisted.", examples=[False]
    )
    supportability: DpmWaveSupportabilityResponse = Field(
        description=(
            "Product-safe wave supportability derived by lotus-manage from item states. "
            "Gateway and Workbench must preserve this authority-owned posture instead of "
            "reconstructing readiness."
        )
    )
    idempotent_replay: bool = Field(
        default=False,
        description="True when create returned an already persisted wave for the idempotency key.",
        examples=[False],
    )


class DpmWaveSearchItem(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    trigger_type: str = Field(
        description="Bounded trigger type used to create the wave.",
        examples=["EXPLICIT_PORTFOLIO_LIST"],
    )
    trigger_id: str = Field(description="Business trigger identifier.", examples=["manual-001"])
    as_of_date: str = Field(description="Business as-of date.", examples=["2026-05-03"])
    created_at: datetime = Field(
        description="UTC timestamp when the wave was created.",
        examples=["2026-05-03T09:30:00Z"],
    )
    created_by: str = Field(description="Actor that created the wave.", examples=["pm_001"])
    item_count: int = Field(description="Number of wave items.", examples=[2])
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Product-safe supportability posture for search and triage.",
        examples=["ready"],
    )
    supportability_reason: str = Field(
        description="Bounded reason for the supportability state.",
        examples=["wave_supportability_ready"],
    )
    latest_event_type: str | None = Field(
        default=None,
        description="Latest persisted event type for operator context.",
        examples=["STATE_TRANSITION"],
    )
    latest_event_reason_code: str | None = Field(
        default=None,
        description="Latest persisted event reason code for operator context.",
        examples=["WAVE_HANDOFF_READY"],
    )


class DpmWaveSearchResponse(BaseModel):
    items: list[DpmWaveSearchItem] = Field(
        description="Bounded page of persisted waves matching the search filters."
    )
    limit: int = Field(description="Requested page size.", examples=[50])
    offset: int = Field(description="Requested page offset.", examples=[0])
    returned_count: int = Field(description="Number of waves returned.", examples=[1])


class DpmWaveDetailResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Persisted wave detail.")
    supportability: DpmWaveSupportabilityResponse = Field(
        description="Latest product-safe supportability derived from persisted item states."
    )
    proof_pack_posture: "DpmWaveProofPackPostureResponse" = Field(
        description="Wave proof-pack and internal operations handoff posture."
    )


class DpmWaveItemsResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    items: list[DpmRebalanceWaveItem] = Field(
        description=(
            "Persisted item list with source readiness, selection, proof-pack, and handoff posture."
        )
    )
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )


class DpmWaveProofPackRef(BaseModel):
    wave_item_id: str = Field(description="Wave item identifier.", examples=["dwi_001"])
    proof_pack_id: str | None = Field(
        default=None,
        description="Linked RFC-0040 proof-pack id when generated.",
        examples=["dpp_001"],
    )
    item_state: str = Field(description="Current item state.", examples=["PROOF_PACK_READY"])
    proof_pack_state: str | None = Field(
        default=None,
        description="Proof-pack posture captured in item diagnostics.",
        examples=["READY"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected RFC-0039 construction alternative id.",
        examples=["alt_min_turnover"],
    )


class DpmWaveProofPackPostureResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    item_count: int = Field(description="Total item count.", examples=[2])
    linked_item_count: int = Field(description="Items with linked proof packs.", examples=[1])
    ready_proof_pack_count: int = Field(
        description="Linked proof packs that are not degraded.", examples=[1]
    )
    degraded_proof_pack_count: int = Field(
        description="Items with degraded proof-pack posture.", examples=[0]
    )
    proof_pack_refs: list[DpmWaveProofPackRef] = Field(
        description="Item-level proof-pack references and posture."
    )
    handoff_refs: list[DpmWaveHandoffRef] = Field(
        description="Append-only internal operations handoff evidence refs."
    )
    external_execution_claimed: bool = Field(
        description=(
            "Always false for valid manage-owned handoff evidence. If persisted evidence ever "
            "contains an external execution claim, downstream report input is blocked until an "
            "external OMS/execution owner contract exists."
        ),
        examples=[False],
    )
    external_execution_boundary: DpmWaveExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-OMS boundary evidence for downstream reports, audit, and "
            "operator diagnosis."
        )
    )


def wave_response(
    *,
    wave: DpmRebalanceWave,
    durable: bool,
    idempotent_replay: bool = False,
) -> DpmWaveResponse:
    return DpmWaveResponse(
        wave=wave,
        durable=durable,
        supportability=DpmWaveSupportabilityResponse.model_validate(
            wave_service.wave_supportability_payload(wave)
        ),
        idempotent_replay=idempotent_replay,
    )
