from __future__ import annotations

import pytest

from src.core.portfolio_memory.models import (
    PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
    PORTFOLIO_MEMORY_AUDIT_POLICY,
    PORTFOLIO_MEMORY_REDACTION_POLICY,
    PORTFOLIO_MEMORY_RETENTION_POLICY,
    PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    DpmPortfolioMemoryEvent,
    PortfolioMemorySupportabilityState,
    validate_portfolio_memory_aggregate_metadata,
)


def _event() -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id="memory:test:event",
        event_type="WAVE_HANDOFF_READY",
        event_time="2026-05-31T10:00:00+00:00",
        actor="ops_001",
        source_system="lotus-manage",
        source_type="DPM_MEMORY_TEST_SOURCE",
        source_id="memory:test:event",
        status="READY",
        supportability_state="READY",
        summary="Portfolio memory model helper test event.",
        reason_codes=["READY_FOR_OPERATIONS_REVIEW"],
        content_hash="sha256:memory-test-event",
    )


def _governance_policy() -> dict[str, str]:
    return {
        "event_identity_scheme": (
            "source_system:source_type:source_id:content_hash_or_content_hash_unavailable"
        ),
        "retention_policy": PORTFOLIO_MEMORY_RETENTION_POLICY,
        "redaction_policy": PORTFOLIO_MEMORY_REDACTION_POLICY,
        "audit_policy": PORTFOLIO_MEMORY_AUDIT_POLICY,
        "access_classification": PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
        "source_authority_policy": PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    }


def _validate_aggregate_metadata(
    *,
    event_count: int = 1,
    event_type_counts: dict[str, int] | None = None,
    source_systems: list[str] | None = None,
    reason_codes: list[str] | None = None,
    supportability_state: PortfolioMemorySupportabilityState = "READY",
    governance_policy: dict[str, str] | None = None,
    events: list[DpmPortfolioMemoryEvent] | None = None,
) -> None:
    validate_portfolio_memory_aggregate_metadata(
        event_count=event_count,
        event_type_counts=event_type_counts or {"WAVE_HANDOFF_READY": 1},
        source_systems=source_systems or ["lotus-manage"],
        reason_codes=reason_codes or ["READY_FOR_OPERATIONS_REVIEW"],
        supportability_state=supportability_state,
        governance_policy=governance_policy or _governance_policy(),
        events=events or [_event()],
    )


def test_validate_portfolio_memory_aggregate_metadata_accepts_consistent_metadata() -> None:
    _validate_aggregate_metadata(events=[_event()])


def test_validate_portfolio_memory_aggregate_metadata_rejects_mismatched_counts() -> None:
    with pytest.raises(ValueError, match="event_count must equal the number of events."):
        _validate_aggregate_metadata(event_count=2, events=[_event()])


def test_validate_portfolio_memory_aggregate_metadata_rejects_event_type_count_drift() -> None:
    with pytest.raises(ValueError, match="event_type_counts must match the returned events."):
        _validate_aggregate_metadata(
            event_type_counts={"MANDATE_HEALTH_SNAPSHOT": 1},
            events=[_event()],
        )


def test_validate_portfolio_memory_aggregate_metadata_rejects_source_system_drift() -> None:
    with pytest.raises(ValueError, match="source_systems must match the returned events."):
        _validate_aggregate_metadata(
            source_systems=["lotus-core"],
            events=[_event()],
        )


def test_validate_portfolio_memory_aggregate_metadata_rejects_reason_code_drift() -> None:
    with pytest.raises(ValueError, match="reason_codes must match the returned events."):
        _validate_aggregate_metadata(
            reason_codes=["STALE_REASON_CODE"],
            events=[_event()],
        )


def test_validate_portfolio_memory_aggregate_metadata_rejects_supportability_state_drift() -> None:
    with pytest.raises(ValueError, match="supportability_state must match the returned events."):
        _validate_aggregate_metadata(
            supportability_state="DEGRADED",
            events=[_event()],
        )


def test_validate_portfolio_memory_aggregate_metadata_rejects_missing_governance_key() -> None:
    governance_policy = _governance_policy()
    governance_policy.pop("source_authority_policy")

    with pytest.raises(
        ValueError,
        match="governance_policy missing required keys: source_authority_policy",
    ):
        _validate_aggregate_metadata(governance_policy=governance_policy, events=[_event()])


def test_validate_portfolio_memory_aggregate_metadata_rejects_blank_governance_value() -> None:
    governance_policy = _governance_policy()
    governance_policy["audit_policy"] = " "

    with pytest.raises(
        ValueError,
        match="governance_policy values must be non-blank for keys: audit_policy",
    ):
        _validate_aggregate_metadata(governance_policy=governance_policy, events=[_event()])


def test_validate_portfolio_memory_aggregate_metadata_rejects_event_governance_drift() -> None:
    event = _event().model_copy(update={"audit_policy": "STALE_AUDIT_POLICY"})

    with pytest.raises(ValueError, match="events must match governance_policy"):
        _validate_aggregate_metadata(events=[event])
