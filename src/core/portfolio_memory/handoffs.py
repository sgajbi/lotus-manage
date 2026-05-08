"""Bounded portfolio-memory context for downstream report inputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.portfolio_memory.models import DpmPortfolioMemory, DpmPortfolioMemoryEvent

PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_LIMIT = 12


class DpmPortfolioMemoryReportEventRef(BaseModel):
    event_identity: str = Field(description="Stable source-backed portfolio-memory event identity.")
    event_type: str = Field(description="Portfolio-memory event type.")
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
    event_count: int = Field(description="Total event count in the source memory projection.")
    source_systems: list[str] = Field(description="Source systems represented by the memory view.")
    reason_codes: list[str] = Field(description="Aggregate bounded reason codes.")
    content_hash: str = Field(description="Canonical source-backed memory view hash.")
    governance_policy: dict[str, str] = Field(
        description="Portfolio-memory retention, redaction, access, audit, and source policy."
    )
    event_refs: list[DpmPortfolioMemoryReportEventRef] = Field(
        description="Bounded event refs for report lineage."
    )


def build_portfolio_memory_report_context(
    memory: DpmPortfolioMemory,
    *,
    event_limit: int = PORTFOLIO_MEMORY_REPORT_CONTEXT_EVENT_LIMIT,
) -> DpmPortfolioMemoryReportContext:
    """Project portfolio memory into report-safe lineage without raw source payloads."""

    return DpmPortfolioMemoryReportContext(
        portfolio_id=memory.portfolio_id,
        supportability_state=memory.supportability_state,
        event_count=memory.event_count,
        source_systems=memory.source_systems,
        reason_codes=memory.reason_codes,
        content_hash=memory.content_hash,
        governance_policy=memory.governance_policy,
        event_refs=[_event_ref(event) for event in memory.events[: max(0, event_limit)]],
    )


def _event_ref(event: DpmPortfolioMemoryEvent) -> DpmPortfolioMemoryReportEventRef:
    return DpmPortfolioMemoryReportEventRef(
        event_identity=event.event_identity,
        event_type=event.event_type,
        source_system=event.source_system,
        source_type=event.source_type,
        source_id=event.source_id,
        content_hash=event.content_hash,
        retention_policy=event.retention_policy,
        redaction_policy=event.redaction_policy,
        audit_policy=event.audit_policy,
        access_classification=event.access_classification,
    )
