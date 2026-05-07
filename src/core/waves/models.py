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
    source_system: str = Field(
        description="System that owns this source evidence.",
        examples=["lotus-manage"],
    )
    source_type: str = Field(
        description="Source product, artifact, or event type.",
        examples=["AFFECTED_PORTFOLIO_MANIFEST"],
    )
    source_id: str = Field(description="Source identifier.", examples=["manifest_20260503_001"])
    source_version: str | None = Field(
        default=None,
        description="Source contract or product version when available.",
        examples=["1.0.0"],
    )
    supportability_state: str | None = Field(
        default=None,
        description="Source supportability posture when available.",
        examples=["READY"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical content hash when available.",
        examples=["sha256:manifest-example"],
    )


class DpmWaveTrigger(BaseModel):
    trigger_type: WaveTriggerType = Field(
        description="Bounded wave trigger type.",
        examples=["EXPLICIT_PORTFOLIO_LIST"],
    )
    trigger_id: str = Field(
        description="Business trigger identifier.",
        examples=["manual-wave-20260503-001"],
    )
    rationale: str = Field(
        description="Business rationale for the wave.",
        examples=["Review explicitly selected portfolios after model drift triage."],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs supporting this trigger.",
    )


class DpmRebalanceWaveItem(BaseModel):
    wave_item_id: str = Field(description="Stable wave item identifier.", examples=["dwi_001"])
    portfolio_id: str = Field(
        description="Affected portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    mandate_id: str | None = Field(
        default=None,
        description="Mandate id when known.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    model_portfolio_id: str | None = Field(
        default=None,
        description="Model portfolio id when sourced.",
        examples=["MODEL_SG_BALANCED"],
    )
    state: WaveItemState = Field(
        description="Current item readiness/workflow state.",
        examples=["CANDIDATE"],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining item state.",
        examples=[["AFFECTED_PORTFOLIO_SOURCE_READY"]],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for item readiness and lineage.",
    )
    alternative_set_id: str | None = Field(
        default=None,
        description="RFC-0039 construction alternative set id when generated.",
        examples=["cas_001"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected RFC-0039 alternative id when available.",
        examples=["alt_min_turnover"],
    )
    proof_pack_id: str | None = Field(
        default=None,
        description="RFC-0040 proof-pack id when linked.",
        examples=["dpp_wave_001"],
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded diagnostics; never raw upstream payloads.",
        examples=[{"source_posture": "candidate_only"}],
    )


class DpmWaveSourceAnalyticsSummary(BaseModel):
    source_family: Literal["RISK", "PERFORMANCE"] = Field(
        description="Owning analytics source family represented by this aggregate.",
        examples=["RISK"],
    )
    supportability_state: str = Field(
        description="Worst source-owned supportability posture represented by the aggregate.",
        examples=["READY"],
    )
    item_count: int = Field(
        description="Wave items with source-owned analytics evidence for this family.",
        examples=[2],
    )
    ready_item_count: int = Field(
        description="Items with READY source-owned analytics evidence.",
        examples=[1],
    )
    degraded_item_count: int = Field(
        description="Items with DEGRADED source-owned analytics evidence.",
        examples=[1],
    )
    blocked_item_count: int = Field(
        description="Items with BLOCKED source-owned analytics evidence.",
        examples=[0],
    )
    pending_review_item_count: int = Field(
        description="Items with PENDING_REVIEW source-owned analytics evidence.",
        examples=[0],
    )
    source_systems: list[str] = Field(
        default_factory=list,
        description="Owning source systems represented in this aggregate.",
        examples=[["lotus-risk"]],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for source-owned analytics evidence.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded source-owner reason codes represented by this aggregate.",
        examples=[["LOTUS_RISK_CONCENTRATION_READY"]],
    )
    source_measures: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Source-emitted scalar values grouped by measure name. Manage records values for "
            "lineage and cockpit display; it does not recalculate risk or performance."
        ),
        examples=[{"concentration_hhi_delta": ["125.50"]}],
    )


class DpmWaveAggregateMetrics(BaseModel):
    item_count: int = Field(description="Total item count in the wave.", examples=[2])
    state_counts: dict[str, int] = Field(
        description="Item count by state.",
        examples=[{"CANDIDATE": 1, "SOURCE_BLOCKED": 1}],
    )
    ready_item_count: int = Field(
        description="Items ready for simulation or later stages.",
        examples=[0],
    )
    blocked_item_count: int = Field(
        description="Items blocked by source or workflow state.",
        examples=[1],
    )
    review_required_item_count: int = Field(
        description="Items requiring human review.",
        examples=[0],
    )
    source_degraded_item_count: int = Field(
        description="Items with degraded source posture.",
        examples=[0],
    )
    source_analytics: list[DpmWaveSourceAnalyticsSummary] = Field(
        default_factory=list,
        description=(
            "Risk and performance source-owner aggregate evidence derived from item analytics "
            "lineage. Empty means no source-owned analytics evidence was supplied or resolved."
        ),
    )


class DpmRebalanceWaveEvent(BaseModel):
    event_id: str = Field(description="Stable event identifier.", examples=["dwe_001"])
    wave_id: str = Field(description="Wave aggregate identifier.", examples=["dwv_001"])
    from_state: WaveState | None = Field(
        default=None,
        description="Previous wave state, or null for creation events.",
        examples=["DRAFT"],
    )
    to_state: WaveState = Field(description="Resulting wave state.", examples=["PREVIEWED"])
    event_type: str = Field(description="Bounded event type.", examples=["STATE_TRANSITION"])
    actor_id: str = Field(
        description="Human or service actor that caused the event.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded reason code for the event.", examples=["PREVIEWED"]
    )
    correlation_id: str = Field(
        description="Correlation id for audit and supportability.",
        examples=["corr-wave-001"],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event was recorded.",
        examples=["2026-05-03T09:30:00Z"],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded event metadata; never raw upstream payloads.",
        examples=[{"item_count": 2}],
    )


class DpmWaveHandoffRef(BaseModel):
    handoff_ref_id: str = Field(
        description="Stable internal operations handoff evidence identifier.",
        examples=["dwh_001"],
    )
    wave_id: str = Field(description="Wave aggregate identifier.", examples=["dwv_001"])
    item_ids: list[str] = Field(
        description="Wave item ids included in this handoff package.",
        examples=[["dwi_001"]],
    )
    actor_id: str = Field(description="Actor that prepared the handoff.", examples=["pm_001"])
    reason_code: str = Field(
        description="Bounded reason code for the handoff.",
        examples=["READY_FOR_OPERATIONS_REVIEW"],
    )
    correlation_id: str = Field(
        description="Correlation id for audit and supportability.",
        examples=["corr-wave-handoff-001"],
    )
    external_execution_claimed: bool = Field(
        default=False,
        description="Always false: manage handoff evidence is not external execution.",
        examples=[False],
    )
    content_hash: str = Field(
        description="Canonical hash of the handoff evidence payload.",
        examples=["sha256:handoff-example"],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the handoff evidence was recorded.",
        examples=["2026-05-03T09:30:00Z"],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded handoff metadata; never raw upstream payloads.",
        examples=[{"staged_item_count": 1}],
    )


class DpmRebalanceWave(BaseModel):
    wave_id: str = Field(description="Stable rebalance wave identifier.", examples=["dwv_001"])
    wave_version: str = Field(
        default="1.0.0",
        description="Wave contract version.",
        examples=["1.0.0"],
    )
    state: WaveState = Field(description="Current wave state.", examples=["PREVIEWED"])
    trigger: DpmWaveTrigger = Field(description="Wave trigger context.")
    as_of_date: str = Field(
        description="Business as-of date for source checks.",
        examples=["2026-05-03"],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the wave was created.",
        examples=["2026-05-03T09:30:00Z"],
    )
    created_by: str = Field(
        description="Human or service actor that created the wave.",
        examples=["pm_001"],
    )
    correlation_id: str = Field(description="Creation correlation id.", examples=["corr-wave-001"])
    version: int = Field(
        default=1,
        description="Optimistic concurrency version.",
        examples=[1],
    )
    items: list[DpmRebalanceWaveItem] = Field(description="Wave item set.")
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate metrics reconciled from item evidence."
    )
    events: list[DpmRebalanceWaveEvent] = Field(
        default_factory=list,
        description="Append-only wave event timeline.",
    )
    handoff_refs: list[DpmWaveHandoffRef] = Field(
        default_factory=list,
        description="Append-only internal operations handoff evidence refs.",
    )
    retention_policy: str = Field(
        default="DPM_WAVE_STANDARD",
        description="Retention policy applied to the wave.",
        examples=["DPM_WAVE_STANDARD"],
    )
