"""Bounded portfolio-memory context for downstream report inputs."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.portfolio_memory.models import DpmPortfolioMemory, DpmPortfolioMemoryEvent

PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_LIMIT = 12
PORTFOLIO_MEMORY_REPORT_CONTEXT_SUPPORT_BOUNDARY = (
    "Portfolio-memory report context is bounded lineage evidence for downstream report and AI "
    "handoffs. It preserves report-safe event refs and hashes only; it does not project raw "
    "source payloads, query external source-owner event stores, discover the global portfolio "
    "universe, reconstruct source-owner methodology, project OMS acknowledgement/fill/settlement "
    "events, or project client communication events."
)
PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_REF_SELECTION_POLICY = (
    "LATEST_EVENTS_BY_EVENT_TIME_DESC_THEN_EVENT_ID_DESC"
)
PORTFOLIO_MEMORY_REPORT_CONTEXT_REQUIRED_GOVERNANCE_KEYS = frozenset(
    {
        "event_identity_scheme",
        "retention_policy",
        "redaction_policy",
        "audit_policy",
        "access_classification",
        "source_authority_policy",
    }
)
PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_REF_GOVERNANCE_FIELDS = {
    "retention_policy": "retention_policy",
    "redaction_policy": "redaction_policy",
    "audit_policy": "audit_policy",
    "access_classification": "access_classification",
}


class DpmPortfolioMemoryReportEventRef(BaseModel):
    event_identity: str = Field(description="Stable source-backed portfolio-memory event identity.")
    event_type: str = Field(description="Portfolio-memory event type.")
    event_time: str = Field(description="UTC event timestamp used for bounded ref selection.")
    event_ref_selection_rank: int = Field(
        ge=1,
        description=(
            "One-based rank assigned by the bounded event-ref selection policy after sorting."
        ),
    )
    source_system: str = Field(description="System that owns the source event.")
    source_type: str = Field(description="Source artifact or event type.")
    source_id: str = Field(description="Source identifier.")
    content_hash: str | None = Field(
        default=None,
        description="Canonical source content hash when available.",
    )
    retention_policy: str = Field(description="Retention policy for the event projection.")
    redaction_policy: str = Field(description="Redaction policy for downstream consumers.")
    audit_policy: str = Field(description="Audit policy for downstream consumers.")
    access_classification: str = Field(description="Audience and access classification.")


class DpmPortfolioMemoryReportContext(BaseModel):
    portfolio_id: str = Field(description="Portfolio identifier.")
    supportability_state: str = Field(
        description="Aggregate portfolio-memory supportability state."
    )
    event_count: int = Field(
        ge=0,
        description="Total event count in the source memory projection.",
    )
    source_systems: list[str] = Field(description="Source systems represented by the memory view.")
    reason_codes: list[str] = Field(description="Aggregate bounded reason codes.")
    content_hash: str = Field(description="Canonical source-backed memory view hash.")
    event_ref_limit: int = Field(
        ge=0,
        description="Maximum number of event refs projected into this bounded handoff context.",
    )
    event_ref_selection_policy: str = Field(
        description=(
            "Deterministic policy used to select bounded event refs from the source memory view."
        )
    )
    event_refs_returned: int = Field(
        ge=0, description="Number of event refs actually projected into this handoff context."
    )
    event_refs_omitted: int = Field(
        ge=0,
        description=(
            "Number of source memory events omitted from this bounded handoff context after "
            "applying the event-ref limit."
        ),
    )
    event_refs_truncated: bool = Field(
        description=(
            "Whether the source memory view contains more events than this bounded handoff "
            "context projects."
        )
    )
    support_boundary: str = Field(
        description=(
            "Explicit no-claim boundary for a bounded portfolio-memory surface, including "
            "unsupported source payload, global discovery, source-owner methodology, OMS, "
            "and client-communication projections."
        )
    )
    context_content_hash: str = Field(
        description=(
            "Canonical hash of this bounded report-context envelope, including event refs and "
            "the source memory content hash, so downstream report and AI consumers can reconcile "
            "equivalent lineage contexts without relying on the full memory view."
        )
    )
    governance_policy: dict[str, str] = Field(
        description=(
            "Portfolio-memory governance policy carrying event_identity_scheme, "
            "retention_policy, redaction_policy, audit_policy, access_classification, and "
            "source_authority_policy."
        )
    )
    event_refs: list[DpmPortfolioMemoryReportEventRef] = Field(
        description="Bounded event refs for report lineage."
    )

    @model_validator(mode="after")
    def validate_bounded_event_ref_metadata(self) -> "DpmPortfolioMemoryReportContext":
        _validate_event_ref_counts(
            event_count=self.event_count,
            event_refs_returned=self.event_refs_returned,
            event_refs_omitted=self.event_refs_omitted,
            event_refs_truncated=self.event_refs_truncated,
            event_ref_count=len(self.event_refs),
        )
        _validate_event_ref_ranks(self.event_refs)
        _validate_governance_policy(self.governance_policy)
        _validate_event_ref_governance(
            governance_policy=self.governance_policy,
            event_refs=self.event_refs,
        )

        return self


def build_portfolio_memory_report_context(
    memory: DpmPortfolioMemory,
    *,
    event_limit: int = PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_LIMIT,
) -> DpmPortfolioMemoryReportContext:
    """Project portfolio memory into report-safe lineage without raw source payloads."""

    bounded_event_limit = max(0, event_limit)
    event_refs = [
        _event_ref(event, event_ref_selection_rank=index)
        for index, event in enumerate(memory.events[:bounded_event_limit], start=1)
    ]
    event_refs_returned = len(event_refs)
    event_refs_omitted = max(0, memory.event_count - event_refs_returned)
    payload = DpmPortfolioMemoryReportContext(
        portfolio_id=memory.portfolio_id,
        supportability_state=memory.supportability_state,
        event_count=memory.event_count,
        source_systems=memory.source_systems,
        reason_codes=memory.reason_codes,
        content_hash=memory.content_hash,
        event_ref_limit=bounded_event_limit,
        event_ref_selection_policy=PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_REF_SELECTION_POLICY,
        event_refs_returned=event_refs_returned,
        event_refs_omitted=event_refs_omitted,
        event_refs_truncated=event_refs_omitted > 0,
        support_boundary=PORTFOLIO_MEMORY_REPORT_CONTEXT_SUPPORT_BOUNDARY,
        context_content_hash="sha256:pending",
        governance_policy=memory.governance_policy,
        event_refs=event_refs,
    ).model_dump(mode="json")
    payload["context_content_hash"] = hash_canonical_payload(
        strip_keys(payload, exclude={"context_content_hash"})
    )
    return DpmPortfolioMemoryReportContext.model_validate(payload)


def _event_ref(
    event: DpmPortfolioMemoryEvent, *, event_ref_selection_rank: int
) -> DpmPortfolioMemoryReportEventRef:
    return DpmPortfolioMemoryReportEventRef(
        event_identity=event.event_identity,
        event_type=event.event_type,
        event_time=event.event_time,
        event_ref_selection_rank=event_ref_selection_rank,
        source_system=event.source_system,
        source_type=event.source_type,
        source_id=event.source_id,
        content_hash=event.content_hash,
        retention_policy=event.retention_policy,
        redaction_policy=event.redaction_policy,
        audit_policy=event.audit_policy,
        access_classification=event.access_classification,
    )


def _validate_event_ref_counts(
    *,
    event_count: int,
    event_refs_returned: int,
    event_refs_omitted: int,
    event_refs_truncated: bool,
    event_ref_count: int,
) -> None:
    if event_refs_returned != event_ref_count:
        raise ValueError("event_refs_returned must equal the number of event_refs.")

    expected_omitted = max(0, event_count - event_refs_returned)
    if event_refs_omitted != expected_omitted:
        raise ValueError("event_refs_omitted must equal event_count minus event_refs_returned.")

    if event_refs_truncated != (event_refs_omitted > 0):
        raise ValueError("event_refs_truncated must match event_refs_omitted posture.")


def _validate_event_ref_ranks(event_refs: list[DpmPortfolioMemoryReportEventRef]) -> None:
    expected_ranks = list(range(1, len(event_refs) + 1))
    observed_ranks = [event_ref.event_ref_selection_rank for event_ref in event_refs]
    if observed_ranks != expected_ranks:
        raise ValueError("event_ref_selection_rank values must be contiguous one-based ranks.")


def _validate_governance_policy(governance_policy: dict[str, str]) -> None:
    missing_governance_keys = (
        PORTFOLIO_MEMORY_REPORT_CONTEXT_REQUIRED_GOVERNANCE_KEYS - governance_policy.keys()
    )
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


def _validate_event_ref_governance(
    *,
    governance_policy: dict[str, str],
    event_refs: list[DpmPortfolioMemoryReportEventRef],
) -> None:
    for (
        event_ref_field,
        governance_key,
    ) in PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_REF_GOVERNANCE_FIELDS.items():
        expected_value = governance_policy[governance_key]
        mismatched_refs = [
            event_ref.event_identity
            for event_ref in event_refs
            if getattr(event_ref, event_ref_field) != expected_value
        ]
        if mismatched_refs:
            raise ValueError(
                "event_refs must match governance_policy."
                f"{governance_key} for {event_ref_field}: "
                f"{', '.join(mismatched_refs)}."
            )
