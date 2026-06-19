"""Domain models for source-backed portfolio memory."""

from typing import Any, Iterable, Literal, cast

from pydantic import BaseModel, Field, model_validator

from src.core.portfolio_memory.event_projection import (
    event_source_systems,
    portfolio_memory_supportability_state,
)

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
    "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
    "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
    "OUTCOME_REVIEW_CREATED",
    "OUTCOME_REVIEW_EVENT",
    "PM_QUALITY_SCORE_RUN",
    "PM_QUALITY_REVIEW_ACTION",
    "PM_QUALITY_SUMMARY_INVOCATION",
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
PORTFOLIO_MEMORY_REQUIRED_GOVERNANCE_KEYS = frozenset(
    {
        "event_identity_scheme",
        "retention_policy",
        "redaction_policy",
        "audit_policy",
        "access_classification",
        "source_authority_policy",
    }
)
PORTFOLIO_MEMORY_EVENT_GOVERNANCE_FIELDS = {
    "retention_policy": "retention_policy",
    "redaction_policy": "redaction_policy",
    "audit_policy": "audit_policy",
    "access_classification": "access_classification",
}


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
    promotion_requirements: list[str] = Field(
        description=(
            "Governance, source-product, lineage, reconciliation, consumer, and downstream "
            "realization requirements that must be met before external execution source events "
            "can be promoted into portfolio memory."
        ),
        examples=[
            [
                "certified_execution_oms_source_owner",
                "ExternalOrderExecutionAcknowledgement:v1",
            ]
        ],
    )
    summary: str = Field(description="Operator-facing no-claim memory boundary summary.")
    content_hash: str = Field(description="Canonical hash of the boundary evidence payload.")


class DpmPortfolioMemoryClientCommunicationBoundaryEvidence(BaseModel):
    boundary_id: Literal["DPM_PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_BOUNDARY"] = Field(
        default="DPM_PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_BOUNDARY",
        description="Stable unsupported client-communication boundary identifier.",
    )
    supportability_state: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Fail-closed supportability state for portfolio-memory client communication.",
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
    client_communication_events_projected: Literal[False] = Field(
        default=False,
        description="Portfolio memory does not project client contact or message events.",
    )
    client_delivery_events_projected: Literal[False] = Field(
        default=False,
        description="Portfolio memory does not project client delivery confirmation events.",
    )
    client_approval_events_projected: Literal[False] = Field(
        default=False,
        description="Portfolio memory does not project client approval or consent events.",
    )
    reason_code: str = Field(
        description="Bounded reason code for the client-communication memory boundary.",
        examples=["PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_EVENTS_NOT_SUPPORTED"],
    )
    blocked_capabilities: list[str] = Field(
        description="Client communication capabilities blocked from portfolio-memory projection.",
        examples=[["client_contact", "client_message_generation", "delivery_confirmation"]],
    )
    required_owner: str = Field(
        description="Future owner required before client communication memory can be promoted.",
        examples=["future client-communication owner"],
    )
    required_source_product: str = Field(
        description="Source product required before Manage can consume client communication truth.",
        examples=["ClientCommunicationRecord:v1"],
    )
    promotion_requirements: list[str] = Field(
        description=(
            "Governance, source-product, lineage, delivery/audit, consumer, and downstream "
            "realization requirements that must be met before client communication source events "
            "can be promoted into portfolio memory."
        ),
        examples=[
            [
                "certified_client_communication_source_owner",
                "ClientCommunicationRecord:v1",
            ]
        ],
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
            "including explicit campaign task-transition, OMS, external order acknowledgement, "
            "client communication, and PM-quality projection boundaries."
        ),
    )
    external_execution_boundary: DpmPortfolioMemoryExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-OMS boundary evidence for portfolio-memory consumers."
        )
    )
    client_communication_boundary: DpmPortfolioMemoryClientCommunicationBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-client-contact boundary evidence for portfolio-memory "
            "consumers."
        )
    )
    events: list[DpmPortfolioMemoryEvent] = Field(
        description="Ordered source-backed portfolio-memory events."
    )
    content_hash: str = Field(
        description=(
            "Canonical hash of the returned memory view excluding generated_at, so audit "
            "consumers can reconcile equivalent source-backed views without timestamp churn."
        )
    )
    generated_at: str = Field(description="UTC timestamp when the read model was generated.")

    @model_validator(mode="after")
    def validate_aggregate_metadata(self) -> "DpmPortfolioMemory":
        validate_portfolio_memory_aggregate_metadata(
            event_count=self.event_count,
            event_type_counts=self.event_type_counts,
            source_systems=self.source_systems,
            reason_codes=self.reason_codes,
            supportability_state=self.supportability_state,
            governance_policy=self.governance_policy,
            events=self.events,
        )
        return self


class DpmPortfolioMemoryEventLookup(BaseModel):
    portfolio_id: str = Field(description="Portfolio identifier used for the memory lookup.")
    event_id: str = Field(description="Stable portfolio-memory event identifier requested.")
    event_identity: str = Field(
        description=(
            "Cross-app event identity for the returned event, derived from source system, "
            "source type, source id, and content-hash posture."
        )
    )
    event: DpmPortfolioMemoryEvent = Field(
        description="Exact source-backed portfolio-memory event matching the requested event id."
    )
    memory_content_hash: str = Field(
        description="Canonical hash of the portfolio-memory view from which the event was selected."
    )
    content_hash: str = Field(
        description=(
            "Canonical hash of the event lookup envelope excluding generated_at, so audit "
            "consumers can reconcile equivalent drilldown responses without timestamp churn."
        )
    )
    generated_at: str = Field(description="UTC timestamp when the lookup view was generated.")
    support_boundary: str = Field(
        description="Explicit no-claim boundary for the bounded memory event lookup surface.",
        examples=[
            "Manage-local memory event lookup does not query external source-owner event stores or project OMS events."
        ],
    )


class DpmPortfolioMemorySearchItem(BaseModel):
    portfolio_id: str = Field(
        description="Portfolio identifier represented in the Manage-local memory index.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    event_count: int = Field(ge=0, description="Returned memory event count for this portfolio.")
    supportability_state: PortfolioMemorySupportabilityState = Field(
        description="Worst supportability state represented by this portfolio's memory events."
    )
    event_type_counts: dict[str, int] = Field(
        description="Returned event count by portfolio-memory event type."
    )
    source_systems: list[str] = Field(
        description=(
            "Source systems represented by this portfolio's returned events, including event "
            "owners, source refs, and artifact refs."
        )
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
    matching_event_count: int = Field(
        ge=0,
        description=(
            "Number of events in this portfolio-memory view that match the applied event, source "
            "system, source type, and supportability filters. When no filters are supplied this equals "
            "event_count."
        ),
        examples=[1],
    )
    latest_matching_event_time: str | None = Field(
        default=None,
        description=(
            "Latest event timestamp among events that match the applied filters. This may differ "
            "from latest_event_time when an older event caused the search hit."
        ),
    )
    latest_matching_event_type: PortfolioMemoryEventType | None = Field(
        default=None,
        description=(
            "Latest event type among events that match the applied filters. This preserves why a "
            "search result matched without changing the latest overall event posture."
        ),
    )
    latest_matching_event_id: str | None = Field(
        default=None,
        description=(
            "Stable event id for the latest matching portfolio-memory event so audit and operator "
            "consumers can load or reconcile the exact matching timeline row."
        ),
    )
    latest_matching_event_identity: str | None = Field(
        default=None,
        description=(
            "Cross-app event identity for the latest matching event, derived from source system, "
            "source type, source id, and content-hash posture."
        ),
    )
    latest_matching_event_source_system: str | None = Field(
        default=None,
        description="Source system that owns the latest matching portfolio-memory event.",
    )
    latest_matching_event_source_type: str | None = Field(
        default=None,
        description="Source artifact or event type for the latest matching portfolio-memory event.",
    )
    latest_matching_event_source_id: str | None = Field(
        default=None,
        description="Source identifier for the latest matching portfolio-memory event.",
    )
    latest_matching_event_content_hash: str | None = Field(
        default=None,
        description="Canonical source content hash for the latest matching event when available.",
    )
    content_hash: str = Field(
        description=(
            "Canonical hash of the portfolio-memory view excluding generated_at, so search rows "
            "remain replay-stable when the underlying source-backed memory is unchanged."
        )
    )

    @model_validator(mode="after")
    def validate_search_item_metadata(self) -> "DpmPortfolioMemorySearchItem":
        _validate_search_item_metadata(
            event_count=self.event_count,
            event_type_counts=self.event_type_counts,
            source_systems=self.source_systems,
            reason_codes=self.reason_codes,
            supportability_state=self.supportability_state,
            matching_event_count=self.matching_event_count,
            latest_event_time=self.latest_event_time,
            latest_event_type=self.latest_event_type,
            latest_matching_event_time=self.latest_matching_event_time,
            latest_matching_event_type=self.latest_matching_event_type,
            latest_matching_event_id=self.latest_matching_event_id,
            latest_matching_event_identity=self.latest_matching_event_identity,
            latest_matching_event_source_system=self.latest_matching_event_source_system,
            latest_matching_event_source_type=self.latest_matching_event_source_type,
            latest_matching_event_source_id=self.latest_matching_event_source_id,
            latest_matching_event_content_hash=self.latest_matching_event_content_hash,
        )

        return self


def _validate_search_item_metadata(
    *,
    event_count: int,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
    supportability_state: PortfolioMemorySupportabilityState,
    matching_event_count: int,
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
    latest_matching_event_time: str | None,
    latest_matching_event_type: PortfolioMemoryEventType | None,
    latest_matching_event_id: str | None,
    latest_matching_event_identity: str | None,
    latest_matching_event_source_system: str | None,
    latest_matching_event_source_type: str | None,
    latest_matching_event_source_id: str | None,
    latest_matching_event_content_hash: str | None,
) -> None:
    _validate_search_item_counts(
        event_count=event_count,
        event_type_counts=event_type_counts,
        matching_event_count=matching_event_count,
    )
    _validate_search_item_sorted_aggregates(
        source_systems=source_systems,
        reason_codes=reason_codes,
    )
    _validate_search_item_latest_event_metadata(
        event_count=event_count,
        supportability_state=supportability_state,
        event_type_counts=event_type_counts,
        source_systems=source_systems,
        reason_codes=reason_codes,
        latest_event_time=latest_event_time,
        latest_event_type=latest_event_type,
    )
    _validate_search_item_latest_matching_event_metadata(
        matching_event_count=matching_event_count,
        latest_matching_event_time=latest_matching_event_time,
        latest_matching_event_type=latest_matching_event_type,
        latest_matching_event_id=latest_matching_event_id,
        latest_matching_event_identity=latest_matching_event_identity,
        latest_matching_event_source_system=latest_matching_event_source_system,
        latest_matching_event_source_type=latest_matching_event_source_type,
        latest_matching_event_source_id=latest_matching_event_source_id,
        latest_matching_event_content_hash=latest_matching_event_content_hash,
    )


def _validate_search_item_counts(
    *,
    event_count: int,
    event_type_counts: dict[str, int],
    matching_event_count: int,
) -> None:
    expected_event_count = sum(event_type_counts.values())
    if event_count != expected_event_count:
        raise ValueError("event_count must equal the sum of event_type_counts.")

    if matching_event_count > event_count:
        raise ValueError("matching_event_count must not exceed event_count.")


def _validate_search_item_sorted_aggregates(
    *,
    source_systems: list[str],
    reason_codes: list[str],
) -> None:
    if source_systems != sorted(set(source_systems)):
        raise ValueError("source_systems must be sorted and unique.")

    if reason_codes != sorted(set(reason_codes)):
        raise ValueError("reason_codes must be sorted and unique.")


def _validate_search_item_latest_event_metadata(
    *,
    event_count: int,
    supportability_state: PortfolioMemorySupportabilityState,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> None:
    if event_count == 0:
        _validate_empty_search_item_latest_event_metadata(
            supportability_state=supportability_state,
            event_type_counts=event_type_counts,
            source_systems=source_systems,
            reason_codes=reason_codes,
            latest_event_time=latest_event_time,
            latest_event_type=latest_event_type,
        )
        return

    _validate_populated_search_item_latest_event_metadata(
        supportability_state=supportability_state,
        latest_event_time=latest_event_time,
        latest_event_type=latest_event_type,
    )


def _validate_empty_search_item_latest_event_metadata(
    *,
    supportability_state: PortfolioMemorySupportabilityState,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> None:
    _validate_empty_search_item_supportability_state(supportability_state)
    _validate_empty_search_item_aggregate_metadata(
        event_type_counts=event_type_counts,
        source_systems=source_systems,
        reason_codes=reason_codes,
    )
    _validate_empty_search_item_latest_event_presence(
        latest_event_time=latest_event_time,
        latest_event_type=latest_event_type,
    )


def _validate_empty_search_item_supportability_state(
    supportability_state: PortfolioMemorySupportabilityState,
) -> None:
    if supportability_state != "EMPTY":
        raise ValueError("empty search items must use EMPTY supportability_state.")


def _validate_empty_search_item_aggregate_metadata(
    *,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
) -> None:
    if event_type_counts or source_systems or reason_codes:
        raise ValueError("empty search items must not carry aggregate event metadata.")


def _validate_empty_search_item_latest_event_presence(
    *,
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> None:
    if _latest_event_metadata_is_present(
        latest_event_time=latest_event_time,
        latest_event_type=latest_event_type,
    ):
        raise ValueError("empty search items must not carry latest event metadata.")


def _validate_populated_search_item_latest_event_metadata(
    *,
    supportability_state: PortfolioMemorySupportabilityState,
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> None:
    if supportability_state == "EMPTY":
        raise ValueError("non-empty search items must not use EMPTY supportability_state.")
    if not _latest_event_metadata_is_complete(
        latest_event_time=latest_event_time,
        latest_event_type=latest_event_type,
    ):
        raise ValueError("non-empty search items must carry latest event metadata.")


def _latest_event_metadata_is_present(
    *,
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> bool:
    return latest_event_time is not None or latest_event_type is not None


def _latest_event_metadata_is_complete(
    *,
    latest_event_time: str | None,
    latest_event_type: PortfolioMemoryEventType | None,
) -> bool:
    return latest_event_time is not None and latest_event_type is not None


def _validate_search_item_latest_matching_event_metadata(
    *,
    matching_event_count: int,
    latest_matching_event_time: str | None,
    latest_matching_event_type: PortfolioMemoryEventType | None,
    latest_matching_event_id: str | None,
    latest_matching_event_identity: str | None,
    latest_matching_event_source_system: str | None,
    latest_matching_event_source_type: str | None,
    latest_matching_event_source_id: str | None,
    latest_matching_event_content_hash: str | None,
) -> None:
    latest_matching_fields = [
        latest_matching_event_time,
        latest_matching_event_type,
        latest_matching_event_id,
        latest_matching_event_identity,
        latest_matching_event_source_system,
        latest_matching_event_source_type,
        latest_matching_event_source_id,
    ]
    if matching_event_count == 0:
        if any(value is not None for value in latest_matching_fields):
            raise ValueError(
                "search items with no matching events must not carry latest matching event metadata."
            )
        if latest_matching_event_content_hash is not None:
            raise ValueError(
                "search items with no matching events must not carry latest matching event content hash."
            )
    elif any(value is None for value in latest_matching_fields):
        raise ValueError(
            "search items with matching events must carry latest matching event metadata."
        )


class DpmPortfolioMemorySearchAppliedFilters(BaseModel):
    portfolio_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Normalized caller-supplied portfolio identifiers after blank values are removed. "
            "An empty list means the bounded Manage-local candidate set was used."
        ),
    )
    event_type: str | None = Field(
        default=None,
        description="Event-type filter applied to matching portfolio-memory events, when supplied.",
    )
    supportability_state: PortfolioMemorySupportabilityState | None = Field(
        default=None,
        description=(
            "Portfolio-memory supportability-state filter applied to summaries and matching "
            "events, when supplied."
        ),
    )
    source_system: str | None = Field(
        default=None,
        description=(
            "Source-system filter applied to matching events, source refs, and artifact refs, "
            "when supplied."
        ),
    )
    source_type: str | None = Field(
        default=None,
        description=(
            "Source-type filter applied to matching events, source refs, and artifact refs, "
            "when supplied."
        ),
    )


class DpmPortfolioMemorySearchPage(BaseModel):
    items: list[DpmPortfolioMemorySearchItem] = Field(
        description=(
            "Bounded page of Manage-local portfolio-memory summaries. The page indexes only "
            "persisted Manage evidence and caller-supplied portfolio identifiers; it is not a "
            "global portfolio-universe discovery product."
        )
    )
    limit: int = Field(ge=1, description="Requested page size.", examples=[50])
    offset: int = Field(ge=0, description="Requested page offset.", examples=[0])
    returned_count: int = Field(ge=0, description="Number of search items returned.", examples=[1])
    total_count: int = Field(
        ge=0,
        description="Total matching Manage-local portfolio-memory summaries before pagination.",
        examples=[1],
    )
    has_more: bool = Field(
        description=(
            "Whether additional matching Manage-local portfolio-memory summaries are available "
            "after this page."
        ),
        examples=[False],
    )
    next_offset: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Offset to request the next page when has_more is true; null when this page exhausts "
            "the bounded Manage-local result set."
        ),
        examples=[50],
    )
    scanned_portfolio_count: int = Field(
        ge=0,
        description="Number of candidate portfolio identifiers scanned from Manage-local evidence.",
        examples=[3],
    )
    source_scan_limit: int = Field(
        ge=1,
        description=(
            "Maximum rows requested from each Manage-local evidence repository while building this "
            "bounded search page."
        ),
        examples=[500],
    )
    applied_filters: DpmPortfolioMemorySearchAppliedFilters = Field(
        description=(
            "Normalized portfolio-memory search filters applied to this bounded page. This echo "
            "supports audit review and pagination without implying external source-owner search."
        )
    )
    supportability_state_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of matching portfolio-memory summaries by supportability state before "
            "pagination. Counts are derived from Manage-local search results only and are not a "
            "global portfolio-universe census."
        ),
        examples=[{"READY": 2, "PENDING_REVIEW": 1}],
    )
    event_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of matching portfolio-memory events by event type before pagination. "
            "Counts are derived from returned Manage-local memory evidence and do not imply "
            "external source-owner event search."
        ),
        examples=[{"WAVE_HANDOFF_READY": 1, "OUTCOME_REVIEW_CREATED": 1}],
    )
    matching_event_supportability_state_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of matching portfolio-memory events by supportability state before "
            "pagination. Counts are derived from events that satisfied the applied search filters, "
            "not from the portfolio aggregate supportability state."
        ),
        examples=[{"READY": 2, "PENDING_REVIEW": 1}],
    )
    matching_event_source_system_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of source systems represented on matching portfolio-memory events "
            "before pagination. Counts include the event source system plus source and artifact "
            "refs on events that satisfied the applied search filters, not every source system "
            "represented by the portfolio memory summary."
        ),
        examples=[{"lotus-manage": 2, "lotus-core": 1}],
    )
    matching_event_source_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of source types represented on matching portfolio-memory events "
            "before pagination. Counts include the event source type plus source and artifact "
            "refs on events that satisfied the applied search filters, not every source type "
            "represented by the portfolio memory summary."
        ),
        examples=[{"DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF": 1}],
    )
    source_system_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Aggregate count of matching portfolio-memory summaries by represented source system "
            "before pagination. Counts are derived from Manage-local evidence only."
        ),
        examples=[{"lotus-manage": 2, "lotus-core": 1}],
    )
    source_event_family_posture: list[DpmPortfolioMemorySourceEventFamilyPosture] = Field(
        default_factory=list,
        description=(
            "Supported and deferred source-event family posture for the bounded portfolio-memory "
            "search surface. This lets Gateway, Workbench, audit, and operations consumers "
            "discover which Manage/report/AI/archive/PM-quality families are supported and "
            "which OMS or client-communication families remain deferred without querying "
            "external source-owner stores."
        ),
    )
    external_execution_boundary: DpmPortfolioMemoryExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-OMS boundary evidence for portfolio-memory search consumers."
        )
    )
    client_communication_boundary: DpmPortfolioMemoryClientCommunicationBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-client-contact boundary evidence for portfolio-memory "
            "search consumers."
        )
    )
    content_hash: str = Field(
        description=(
            "Canonical hash of the bounded search page excluding generated_at, so audit consumers "
            "can reconcile the page posture without timestamp churn."
        )
    )
    generated_at: str = Field(description="UTC timestamp when the search page was generated.")
    support_boundary: str = Field(
        description=("Explicit no-claim boundary for the bounded memory search surface."),
        examples=[
            "Manage-local memory search does not discover the global portfolio universe or project OMS events."
        ],
    )

    @model_validator(mode="after")
    def validate_search_page_metadata(self) -> "DpmPortfolioMemorySearchPage":
        _validate_search_page_pagination(
            returned_count=self.returned_count,
            item_count=len(self.items),
            total_count=self.total_count,
            offset=self.offset,
            has_more=self.has_more,
            next_offset=self.next_offset,
        )
        _validate_search_page_count_maps(
            total_count=self.total_count,
            supportability_state_counts=self.supportability_state_counts,
            event_type_counts=self.event_type_counts,
            matching_event_supportability_state_counts=(
                self.matching_event_supportability_state_counts
            ),
            matching_event_source_system_counts=self.matching_event_source_system_counts,
            matching_event_source_type_counts=self.matching_event_source_type_counts,
            source_system_counts=self.source_system_counts,
        )
        page_supportability_counts = _search_page_supportability_counts(self.items)
        page_source_system_counts = _search_page_source_system_counts(self.items)
        _validate_search_page_returned_counts_covered(
            reported_counts=self.supportability_state_counts,
            page_counts=page_supportability_counts,
            message="supportability_state_counts must cover returned page item states.",
        )
        _validate_search_page_returned_counts_covered(
            reported_counts=self.source_system_counts,
            page_counts=page_source_system_counts,
            message="source_system_counts must cover returned page item sources.",
        )
        _validate_complete_search_page_counts(
            total_count=self.total_count,
            returned_count=self.returned_count,
            supportability_state_counts=self.supportability_state_counts,
            page_supportability_counts=page_supportability_counts,
            source_system_counts=self.source_system_counts,
            page_source_system_counts=page_source_system_counts,
            matching_event_supportability_state_counts=(
                self.matching_event_supportability_state_counts
            ),
            expected_matching_event_count=sum(item.matching_event_count for item in self.items),
        )

        return self


def _validate_search_page_pagination(
    *,
    returned_count: int,
    item_count: int,
    total_count: int,
    offset: int,
    has_more: bool,
    next_offset: int | None,
) -> None:
    if returned_count != item_count:
        raise ValueError("returned_count must equal the number of items.")

    if returned_count > total_count:
        raise ValueError("returned_count must not exceed total_count.")

    expected_has_more = _page_has_more(
        offset=offset,
        returned_count=returned_count,
        total_count=total_count,
    )
    if has_more != expected_has_more:
        raise ValueError("has_more must match pagination posture.")

    _validate_search_page_next_offset(
        offset=offset,
        returned_count=returned_count,
        has_more=has_more,
        next_offset=next_offset,
    )


def _page_has_more(
    *,
    offset: int,
    returned_count: int,
    total_count: int,
) -> bool:
    return offset + returned_count < total_count


def _expected_search_page_next_offset(
    *,
    offset: int,
    returned_count: int,
    has_more: bool,
) -> int | None:
    if has_more:
        return offset + returned_count
    return None


def _validate_search_page_next_offset(
    *,
    offset: int,
    returned_count: int,
    has_more: bool,
    next_offset: int | None,
) -> None:
    expected_next_offset = _expected_search_page_next_offset(
        offset=offset,
        returned_count=returned_count,
        has_more=has_more,
    )
    if _search_page_is_terminal(has_more):
        _validate_terminal_search_page_next_offset(next_offset)
        return
    if not _next_offset_matches_expected(
        next_offset=next_offset,
        expected_next_offset=expected_next_offset,
    ):
        raise ValueError("next_offset must equal offset plus returned_count.")
    assert next_offset is not None
    if not _next_offset_advances(offset=offset, next_offset=next_offset):
        raise ValueError("next_offset must advance when has_more is true.")


def _search_page_is_terminal(has_more: bool) -> bool:
    return not has_more


def _validate_terminal_search_page_next_offset(next_offset: int | None) -> None:
    if next_offset is not None:
        raise ValueError("next_offset must be null when has_more is false.")


def _next_offset_matches_expected(
    *,
    next_offset: int | None,
    expected_next_offset: int | None,
) -> bool:
    return next_offset is not None and next_offset == expected_next_offset


def _next_offset_advances(*, offset: int, next_offset: int) -> bool:
    return next_offset > offset


def _validate_search_page_count_maps(
    *,
    total_count: int,
    supportability_state_counts: dict[str, int],
    event_type_counts: dict[str, int],
    matching_event_supportability_state_counts: dict[str, int],
    matching_event_source_system_counts: dict[str, int],
    matching_event_source_type_counts: dict[str, int],
    source_system_counts: dict[str, int],
) -> None:
    count_maps = {
        "supportability_state_counts": supportability_state_counts,
        "event_type_counts": event_type_counts,
        "matching_event_supportability_state_counts": matching_event_supportability_state_counts,
        "matching_event_source_system_counts": matching_event_source_system_counts,
        "matching_event_source_type_counts": matching_event_source_type_counts,
        "source_system_counts": source_system_counts,
    }
    for label, counts in count_maps.items():
        _validate_non_negative_counts(label=label, counts=counts)
    if sum(supportability_state_counts.values()) != total_count:
        raise ValueError("supportability_state_counts must sum to total_count.")


def _search_page_supportability_counts(
    items: list[DpmPortfolioMemorySearchItem],
) -> dict[str, int]:
    return _counts(item.supportability_state for item in items)


def _search_page_source_system_counts(
    items: list[DpmPortfolioMemorySearchItem],
) -> dict[str, int]:
    return _counts(source_system for item in items for source_system in item.source_systems)


def _validate_search_page_returned_counts_covered(
    *,
    reported_counts: dict[str, int],
    page_counts: dict[str, int],
    message: str,
) -> None:
    for key, count in page_counts.items():
        if reported_counts.get(key, 0) < count:
            raise ValueError(message)


def _validate_complete_search_page_counts(
    *,
    total_count: int,
    returned_count: int,
    supportability_state_counts: dict[str, int],
    page_supportability_counts: dict[str, int],
    source_system_counts: dict[str, int],
    page_source_system_counts: dict[str, int],
    matching_event_supportability_state_counts: dict[str, int],
    expected_matching_event_count: int,
) -> None:
    if total_count != returned_count:
        return
    if supportability_state_counts != page_supportability_counts:
        raise ValueError(
            "supportability_state_counts must match returned items when the page is complete."
        )
    if source_system_counts != page_source_system_counts:
        raise ValueError(
            "source_system_counts must match returned items when the page is complete."
        )
    if sum(matching_event_supportability_state_counts.values()) != expected_matching_event_count:
        raise ValueError(
            "matching_event_supportability_state_counts must sum to matching events when the page is complete."
        )


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def validate_portfolio_memory_aggregate_metadata(
    *,
    event_count: int,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
    supportability_state: PortfolioMemorySupportabilityState,
    governance_policy: dict[str, str],
    events: list[DpmPortfolioMemoryEvent],
) -> None:
    _validate_portfolio_memory_event_aggregates(
        event_count=event_count,
        event_type_counts=event_type_counts,
        source_systems=source_systems,
        reason_codes=reason_codes,
        supportability_state=supportability_state,
        events=events,
    )
    _validate_portfolio_memory_governance_policy(governance_policy)
    _validate_portfolio_memory_event_governance(
        events=events,
        governance_policy=governance_policy,
    )


def _validate_portfolio_memory_event_aggregates(
    *,
    event_count: int,
    event_type_counts: dict[str, int],
    source_systems: list[str],
    reason_codes: list[str],
    supportability_state: PortfolioMemorySupportabilityState,
    events: list[DpmPortfolioMemoryEvent],
) -> None:
    _validate_portfolio_memory_aggregate_match(
        actual=event_count,
        expected=_portfolio_memory_event_count(events),
        message="event_count must equal the number of events.",
    )
    _validate_portfolio_memory_aggregate_match(
        actual=event_type_counts,
        expected=_portfolio_memory_event_type_counts(events),
        message="event_type_counts must match the returned events.",
    )
    _validate_portfolio_memory_aggregate_match(
        actual=source_systems,
        expected=_portfolio_memory_source_systems(events),
        message="source_systems must match the returned events.",
    )
    _validate_portfolio_memory_aggregate_match(
        actual=reason_codes,
        expected=_portfolio_memory_reason_codes(events),
        message="reason_codes must match the returned events.",
    )
    _validate_portfolio_memory_aggregate_match(
        actual=supportability_state,
        expected=_portfolio_memory_supportability_state(events),
        message="supportability_state must match the returned events.",
    )


def _validate_portfolio_memory_aggregate_match(
    *,
    actual: object,
    expected: object,
    message: str,
) -> None:
    if actual != expected:
        raise ValueError(message)


def _portfolio_memory_event_count(events: list[DpmPortfolioMemoryEvent]) -> int:
    return len(events)


def _portfolio_memory_event_type_counts(
    events: list[DpmPortfolioMemoryEvent],
) -> dict[str, int]:
    return _counts(event.event_type for event in events)


def _portfolio_memory_source_systems(events: list[DpmPortfolioMemoryEvent]) -> list[str]:
    return sorted(
        {source_system for event in events for source_system in event_source_systems(event)}
    )


def _portfolio_memory_reason_codes(events: list[DpmPortfolioMemoryEvent]) -> list[str]:
    return sorted({reason for event in events for reason in event.reason_codes})


def _validate_portfolio_memory_governance_policy(
    governance_policy: dict[str, str],
) -> None:
    missing_governance_keys = PORTFOLIO_MEMORY_REQUIRED_GOVERNANCE_KEYS - governance_policy.keys()
    if missing_governance_keys:
        raise ValueError(
            "governance_policy missing required keys: "
            f"{', '.join(sorted(missing_governance_keys))}."
        )

    blank_governance_keys = [key for key, value in governance_policy.items() if not value.strip()]
    if blank_governance_keys:
        raise ValueError(
            "governance_policy values must be non-blank for keys: "
            f"{', '.join(sorted(blank_governance_keys))}."
        )


def _validate_portfolio_memory_event_governance(
    *,
    events: list[DpmPortfolioMemoryEvent],
    governance_policy: dict[str, str],
) -> None:
    for event_field, governance_key in PORTFOLIO_MEMORY_EVENT_GOVERNANCE_FIELDS.items():
        expected_value = governance_policy[governance_key]
        mismatched_events = [
            event.event_identity
            for event in events
            if getattr(event, event_field) != expected_value
        ]
        if mismatched_events:
            raise ValueError(
                "events must match governance_policy."
                f"{governance_key} for {event_field}: "
                f"{', '.join(mismatched_events)}."
            )


def _validate_non_negative_counts(*, label: str, counts: dict[str, int]) -> None:
    negative_keys = [key for key, value in counts.items() if value < 0]
    if negative_keys:
        raise ValueError(
            f"{label} values must be non-negative for keys: {', '.join(negative_keys)}."
        )


def _portfolio_memory_supportability_state(
    events: list[DpmPortfolioMemoryEvent],
) -> PortfolioMemorySupportabilityState:
    return cast(PortfolioMemorySupportabilityState, portfolio_memory_supportability_state(events))
