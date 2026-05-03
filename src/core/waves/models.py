"""Domain models for RFC-0041 rebalance waves."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

WaveTriggerType = Literal[
    "EXPLICIT_PORTFOLIO_LIST",
    "PM_BOOK_REVIEW",
    "CIO_MODEL_CHANGE",
    "TACTICAL_HOUSE_VIEW",
    "RISK_EVENT",
    "BULK_REVIEW_CAMPAIGN",
]

WaveState = Literal[
    "DRAFT",
    "PREVIEWED",
    "CREATED",
    "SOURCE_CHECKED",
    "SIMULATING",
    "SIMULATED",
    "PARTIALLY_SIMULATED",
    "SIMULATION_FAILED",
    "REVIEW_REQUIRED",
    "APPROVED",
    "APPROVED_WITH_EXCEPTIONS",
    "STAGED",
    "HANDOFF_READY",
    "HANDOFF_BLOCKED",
    "HANDOFF_ACKNOWLEDGED",
    "BLOCKED",
    "REJECTED",
    "CANCELLED",
    "CLOSED",
]

WaveItemState = Literal[
    "CANDIDATE",
    "SOURCE_READY",
    "SOURCE_DEGRADED",
    "REVIEW_REQUIRED",
    "SOURCE_BLOCKED",
    "SIMULATED",
    "SIMULATION_BLOCKED",
    "SELECTED",
    "PROOF_PACK_READY",
    "APPROVED",
    "STAGED",
    "HANDOFF_READY",
    "EXCLUDED",
]


class DpmWaveSourceRef(BaseModel):
    source_system: str = Field(description="System that owns this source evidence.")
    source_type: str = Field(description="Source product, artifact, or event type.")
    source_id: str = Field(description="Source identifier.")
    source_version: str | None = Field(
        default=None,
        description="Source contract or product version when available.",
    )
    supportability_state: str | None = Field(
        default=None,
        description="Source supportability posture when available.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
    )


class DpmWaveTrigger(BaseModel):
    trigger_type: WaveTriggerType = Field(description="Bounded wave trigger type.")
    trigger_id: str = Field(description="Business trigger identifier.")
    rationale: str = Field(description="Business rationale for the wave.")
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs supporting this trigger.",
    )


class DpmRebalanceWaveItem(BaseModel):
    wave_item_id: str = Field(description="Stable wave item identifier.")
    portfolio_id: str = Field(description="Affected portfolio identifier.")
    mandate_id: str | None = Field(default=None, description="Mandate id when known.")
    model_portfolio_id: str | None = Field(
        default=None,
        description="Model portfolio id when sourced.",
    )
    state: WaveItemState = Field(description="Current item readiness/workflow state.")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining item state.",
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for item readiness and lineage.",
    )
    alternative_set_id: str | None = Field(
        default=None,
        description="RFC-0039 construction alternative set id when generated.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected RFC-0039 alternative id when available.",
    )
    proof_pack_id: str | None = Field(
        default=None,
        description="RFC-0040 proof-pack id when linked.",
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded diagnostics; never raw upstream payloads.",
    )


class DpmWaveAggregateMetrics(BaseModel):
    item_count: int = Field(description="Total item count in the wave.")
    state_counts: dict[str, int] = Field(description="Item count by state.")
    ready_item_count: int = Field(description="Items ready for simulation or later stages.")
    blocked_item_count: int = Field(description="Items blocked by source or workflow state.")
    review_required_item_count: int = Field(description="Items requiring human review.")
    source_degraded_item_count: int = Field(description="Items with degraded source posture.")


class DpmRebalanceWaveEvent(BaseModel):
    event_id: str = Field(description="Stable event identifier.")
    wave_id: str = Field(description="Wave aggregate identifier.")
    from_state: WaveState | None = Field(
        default=None,
        description="Previous wave state, or null for creation events.",
    )
    to_state: WaveState = Field(description="Resulting wave state.")
    event_type: str = Field(description="Bounded event type.")
    actor_id: str = Field(description="Human or service actor that caused the event.")
    reason_code: str = Field(description="Bounded reason code for the event.")
    correlation_id: str = Field(description="Correlation id for audit and supportability.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event was recorded.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded event metadata; never raw upstream payloads.",
    )


class DpmRebalanceWave(BaseModel):
    wave_id: str = Field(description="Stable rebalance wave identifier.")
    wave_version: str = Field(default="1.0.0", description="Wave contract version.")
    state: WaveState = Field(description="Current wave state.")
    trigger: DpmWaveTrigger = Field(description="Wave trigger context.")
    as_of_date: str = Field(description="Business as-of date for source checks.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the wave was created.",
    )
    created_by: str = Field(description="Human or service actor that created the wave.")
    correlation_id: str = Field(description="Creation correlation id.")
    version: int = Field(default=1, description="Optimistic concurrency version.")
    items: list[DpmRebalanceWaveItem] = Field(description="Wave item set.")
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate metrics reconciled from item evidence."
    )
    events: list[DpmRebalanceWaveEvent] = Field(
        default_factory=list,
        description="Append-only wave event timeline.",
    )
    retention_policy: str = Field(
        default="DPM_WAVE_STANDARD",
        description="Retention policy applied to the wave.",
    )
