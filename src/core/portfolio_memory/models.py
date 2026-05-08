"""Domain models for source-backed portfolio memory."""

from typing import Any, Literal

from pydantic import BaseModel, Field

PortfolioMemoryEventType = Literal[
    "PROOF_PACK_CREATED",
    "PROOF_PACK_TIMELINE_EVENT",
    "MANDATE_HEALTH_SNAPSHOT",
    "MANDATE_MONITORING_EXCEPTION",
    "WAVE_CREATED",
    "WAVE_EVENT",
    "WAVE_HANDOFF_READY",
    "OUTCOME_REVIEW_CREATED",
    "OUTCOME_REVIEW_EVENT",
]

PortfolioMemorySupportabilityState = Literal[
    "READY",
    "PENDING_REVIEW",
    "DEGRADED",
    "BLOCKED",
    "EMPTY",
]


class DpmPortfolioMemorySourceRef(BaseModel):
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


class DpmPortfolioMemoryEvent(BaseModel):
    event_id: str = Field(description="Stable portfolio-memory event identifier.")
    event_type: PortfolioMemoryEventType = Field(description="Portfolio-memory event type.")
    event_time: str = Field(description="UTC event timestamp.")
    actor: str = Field(description="Actor or service responsible for the event.")
    source_system: str = Field(description="System that owns the source event.")
    source_type: str = Field(description="Source artifact or event type.")
    source_id: str = Field(description="Source identifier.")
    status: str = Field(description="Source event status.")
    supportability_state: PortfolioMemorySupportabilityState = Field(
        description="Bounded supportability state represented by this event.",
    )
    summary: str = Field(description="Business-readable event summary.")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes carried from source evidence.",
    )
    source_refs: list[DpmPortfolioMemorySourceRef] = Field(
        default_factory=list,
        description="Source refs linked to the event.",
    )
    artifact_refs: list[DpmPortfolioMemorySourceRef] = Field(
        default_factory=list,
        description="Artifact refs linked to the event.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical source content hash when available.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded metadata without raw source payloads.",
    )


class DpmPortfolioMemory(BaseModel):
    portfolio_id: str = Field(description="Portfolio identifier.")
    event_count: int = Field(description="Returned event count.")
    supportability_state: PortfolioMemorySupportabilityState = Field(
        description="Worst supportability state represented by returned events.",
    )
    event_type_counts: dict[str, int] = Field(description="Returned event count by event type.")
    source_systems: list[str] = Field(description="Source systems represented by returned events.")
    reason_codes: list[str] = Field(description="Bounded aggregate reason codes.")
    events: list[DpmPortfolioMemoryEvent] = Field(
        description="Ordered source-backed portfolio-memory events."
    )
    content_hash: str = Field(description="Canonical hash of the returned memory view.")
    generated_at: str = Field(description="UTC timestamp when the read model was generated.")
