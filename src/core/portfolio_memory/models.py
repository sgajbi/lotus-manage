"""Domain models for source-backed portfolio memory."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

PortfolioMemoryEventType = Literal[
    "PROOF_PACK_CREATED",
    "PROOF_PACK_TIMELINE_EVENT",
    "MANDATE_HEALTH_SNAPSHOT",
    "MANDATE_MONITORING_EXCEPTION",
    "CONSTRUCTION_ALTERNATIVE_SET",
    "CONSTRUCTION_ALTERNATIVE_SELECTED",
    "WAVE_CREATED",
    "WAVE_EVENT",
    "WAVE_HANDOFF_READY",
    "BULK_REVIEW_CAMPAIGN_DEFINITION",
    "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
    "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
    "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
    "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
    "OUTCOME_REVIEW_CREATED",
    "OUTCOME_REVIEW_EVENT",
    "PM_QUALITY_SCORE_RUN",
]

PortfolioMemorySupportabilityState = Literal[
    "READY",
    "PENDING_REVIEW",
    "DEGRADED",
    "BLOCKED",
    "EMPTY",
]
PortfolioMemorySourceEventFamilyStatus = Literal[
    "SUPPORTED",
    "DEFERRED_SOURCE_OWNER",
]

PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME = (
    "source_system:source_type:source_id:content_hash_or_content_hash_unavailable"
)
PORTFOLIO_MEMORY_RETENTION_POLICY = "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y"
PORTFOLIO_MEMORY_REDACTION_POLICY = "NO_RAW_PAYLOADS"
PORTFOLIO_MEMORY_AUDIT_POLICY = "AUDIT_READ_AND_EXPORT"
PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION = "CLIENT_CONFIDENTIAL_INTERNAL"
PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY = (
    "portfolio memory projects source-owned facts; consumers must not reconstruct risk, "
    "performance, mandate-health, execution, tax, cash, FX, report, or AI truth"
)


class DpmPortfolioMemoryExternalExecutionBoundaryEvidence(BaseModel):
    boundary_id: Literal["DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY"] = Field(
        default="DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY",
        description="Stable unsupported external execution boundary identifier.",
    )
    supportability_state: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Fail-closed supportability state for portfolio-memory execution events.",
    )
    source_system: Literal["lotus-manage"] = Field(
        default="lotus-manage",
        description="System preserving the unsupported portfolio-memory boundary evidence.",
    )
    source_product_name: Literal["DpmPortfolioMemory"] = Field(
        default="DpmPortfolioMemory",
        description="Manage-owned read model that stops at source-backed memory projection.",
    )
    source_product_version: Literal["v1"] = Field(
        default="v1",
        description="Boundary evidence product version.",
    )
    external_execution_events_projected: Literal[False] = Field(
        default=False,
        description="Portfolio memory does not project external execution, fill, or OMS events.",
    )
    external_acknowledgement_events_projected: Literal[False] = Field(
        default=False,
        description="Portfolio memory does not project bank-owned OMS acknowledgement events.",
    )
    reason_code: str = Field(
        description="Bounded reason code for the external execution memory boundary.",
        examples=["PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_EVENTS_NOT_SUPPORTED"],
    )
    blocked_capabilities: list[str] = Field(
        description="External execution capabilities blocked from portfolio-memory projection.",
        examples=[["order_generation", "venue_routing", "oms_acknowledgement"]],
    )
    required_owner: str = Field(
        description="Future owner required before external execution memory can be promoted.",
        examples=["future execution/OMS owner"],
    )
    required_source_product: str = Field(
        description="Source product required before Manage can consume execution acknowledgement truth.",
        examples=["ExternalOrderExecutionAcknowledgement:v1"],
    )
    summary: str = Field(description="Operator-facing no-claim memory boundary summary.")
    content_hash: str = Field(description="Canonical hash of the boundary evidence payload.")


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


class DpmPortfolioMemorySourceEventFamilyPosture(BaseModel):
    family_key: str = Field(description="Stable key for the source-event family.")
    source_system: str = Field(description="Owning source system or future source-owner boundary.")
    owner: str = Field(description="Current accountable owner for the source-event family posture.")
    support_status: PortfolioMemorySourceEventFamilyStatus = Field(
        description="Support posture for this source-event family in portfolio memory.",
    )
    event_types: list[str] = Field(
        default_factory=list,
        description="Supported event types for this family when implementation-backed.",
    )
    route: str | None = Field(
        default=None,
        description="Owning API route when the source-event family is implementation-backed.",
    )
    reason_code: str = Field(description="Bounded reason code for this source-event posture.")
    summary: str = Field(
        description=(
            "Business-readable support boundary that prevents consumers from inferring hidden "
            "portfolio-memory truth."
        ),
    )


class DpmPortfolioMemoryEvent(BaseModel):
    event_id: str = Field(description="Stable portfolio-memory event identifier.")
    event_identity: str = Field(
        default="",
        description=(
            "Stable cross-app event identity derived from source system, source type, source id, "
            "and source content hash posture."
        ),
    )
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
    retention_policy: str = Field(
        default=PORTFOLIO_MEMORY_RETENTION_POLICY,
        description="Retention policy for the portfolio-memory event projection.",
    )
    redaction_policy: str = Field(
        default=PORTFOLIO_MEMORY_REDACTION_POLICY,
        description="Redaction policy for timeline event metadata and source refs.",
    )
    audit_policy: str = Field(
        default=PORTFOLIO_MEMORY_AUDIT_POLICY,
        description="Audit policy for downstream portfolio-memory consumers.",
    )
    access_classification: str = Field(
        default=PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
        description="Audience and access classification for the event projection.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded metadata without raw source payloads.",
    )

    @model_validator(mode="after")
    def populate_event_identity(self) -> "DpmPortfolioMemoryEvent":
        if not self.event_identity:
            hash_part = self.content_hash or "content_hash_unavailable"
            self.event_identity = (
                f"{self.source_system}:{self.source_type}:{self.source_id}:{hash_part}"
            )
        return self


class DpmPortfolioMemory(BaseModel):
    portfolio_id: str = Field(description="Portfolio identifier.")
    event_count: int = Field(description="Returned event count.")
    supportability_state: PortfolioMemorySupportabilityState = Field(
        description="Worst supportability state represented by returned events.",
    )
    event_type_counts: dict[str, int] = Field(description="Returned event count by event type.")
    source_systems: list[str] = Field(description="Source systems represented by returned events.")
    reason_codes: list[str] = Field(description="Bounded aggregate reason codes.")
    governance_policy: dict[str, str] = Field(
        default_factory=dict,
        description="Portfolio-memory event identity, retention, redaction, access, and audit policy.",
    )
    source_event_family_posture: list[DpmPortfolioMemorySourceEventFamilyPosture] = Field(
        default_factory=list,
        description=(
            "Supported and deferred source-event families in the portfolio-memory contract, "
            "including explicit OMS, external order acknowledgement, and PM-quality projection "
            "boundaries."
        ),
    )
    external_execution_boundary: DpmPortfolioMemoryExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-OMS boundary evidence for portfolio-memory consumers."
        )
    )
    events: list[DpmPortfolioMemoryEvent] = Field(
        description="Ordered source-backed portfolio-memory events."
    )
    content_hash: str = Field(description="Canonical hash of the returned memory view.")
    generated_at: str = Field(description="UTC timestamp when the read model was generated.")


class DpmPortfolioMemorySearchItem(BaseModel):
    portfolio_id: str = Field(
        description="Portfolio identifier represented in the Manage-local memory index.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    event_count: int = Field(description="Returned memory event count for this portfolio.")
    supportability_state: PortfolioMemorySupportabilityState = Field(
        description="Worst supportability state represented by this portfolio's memory events."
    )
    event_type_counts: dict[str, int] = Field(
        description="Returned event count by portfolio-memory event type."
    )
    source_systems: list[str] = Field(
        description="Source systems represented by this portfolio's returned events."
    )
    reason_codes: list[str] = Field(description="Bounded aggregate reason codes.")
    latest_event_time: str | None = Field(
        default=None,
        description="Latest event timestamp in the returned portfolio-memory view.",
    )
    latest_event_type: PortfolioMemoryEventType | None = Field(
        default=None,
        description="Latest event type in the returned portfolio-memory view.",
    )
    content_hash: str = Field(description="Canonical hash of the portfolio-memory view.")


class DpmPortfolioMemorySearchPage(BaseModel):
    items: list[DpmPortfolioMemorySearchItem] = Field(
        description=(
            "Bounded page of Manage-local portfolio-memory summaries. The page indexes only "
            "persisted Manage evidence and caller-supplied portfolio identifiers; it is not a "
            "global portfolio-universe discovery product."
        )
    )
    limit: int = Field(description="Requested page size.", examples=[50])
    offset: int = Field(description="Requested page offset.", examples=[0])
    returned_count: int = Field(description="Number of search items returned.", examples=[1])
    total_count: int = Field(
        description="Total matching Manage-local portfolio-memory summaries before pagination.",
        examples=[1],
    )
    scanned_portfolio_count: int = Field(
        description="Number of candidate portfolio identifiers scanned from Manage-local evidence.",
        examples=[3],
    )
    generated_at: str = Field(description="UTC timestamp when the search page was generated.")
    support_boundary: str = Field(
        description=("Explicit no-claim boundary for the bounded memory search surface."),
        examples=[
            "Manage-local memory search does not discover the global portfolio universe or project OMS events."
        ],
    )
