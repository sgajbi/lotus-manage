from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence,
    external_execution_boundary_evidence,
    portfolio_memory_governance_policy,
    source_event_family_posture,
)
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.supportability import (
    assignment_sla_state,
    assignment_task_state,
    maker_checker_state,
    portfolio_memory_state,
    source_supportability_state,
)


def _memory_event(*, state: str, event_id: str = "event_001") -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=event_id,
        event_type="WAVE_EVENT",
        event_time="2026-05-31T00:00:00+00:00",
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DpmRebalanceWave",
        source_id=event_id,
        status=state,
        supportability_state=state,
        summary="Portfolio memory test event.",
    )


def test_portfolio_memory_governance_policy_is_explicit_and_source_owned() -> None:
    policy = portfolio_memory_governance_policy()

    assert policy["redaction_policy"] == "NO_RAW_PAYLOADS"
    assert policy["access_classification"] == "CLIENT_CONFIDENTIAL_INTERNAL"
    assert "projects source-owned facts" in policy["source_authority_policy"]


def test_portfolio_memory_boundary_evidence_blocks_unsupported_external_claims() -> None:
    execution_boundary = external_execution_boundary_evidence()
    communication_boundary = client_communication_boundary_evidence()

    assert execution_boundary.supportability_state == "BLOCKED"
    assert execution_boundary.external_execution_events_projected is False
    assert "oms_acknowledgement" in execution_boundary.blocked_capabilities
    assert execution_boundary.content_hash.startswith("sha256:")

    assert communication_boundary.supportability_state == "BLOCKED"
    assert communication_boundary.client_communication_events_projected is False
    assert "client_contact" in communication_boundary.blocked_capabilities
    assert communication_boundary.content_hash.startswith("sha256:")


def test_source_event_family_posture_separates_supported_and_deferred_families() -> None:
    postures = {posture.family_key: posture for posture in source_event_family_posture()}

    assert postures["mandate_health"].support_status == "SUPPORTED"
    assert postures["bulk_review_campaign_workflow"].support_status == "SUPPORTED"
    assert postures["external_oms_execution"].support_status == "DEFERRED_SOURCE_OWNER"
    assert postures["client_communication"].event_types == []


def test_portfolio_memory_supportability_mapping_is_fail_closed() -> None:
    assert portfolio_memory_state([]) == "EMPTY"
    assert portfolio_memory_state([_memory_event(state="READY")]) == "READY"
    assert portfolio_memory_state([_memory_event(state="BLOCKED")]) == "BLOCKED"
    assert (
        portfolio_memory_state(
            [
                _memory_event(state="READY", event_id="event_ready"),
                _memory_event(state="DEGRADED", event_id="event_degraded"),
            ]
        )
        == "DEGRADED"
    )

    assert source_supportability_state("FAILED") == "BLOCKED"
    assert source_supportability_state("PARTIAL") == "DEGRADED"
    assert source_supportability_state("CREATED") == "PENDING_REVIEW"
    assert source_supportability_state("READY") == "READY"

    assert assignment_sla_state("BREACHED_OR_BLOCKED") == "DEGRADED"
    assert assignment_task_state("CANCELLED", "ON_TRACK") == "BLOCKED"
    assert assignment_task_state("OPEN", "ON_TRACK") == "PENDING_REVIEW"
    assert maker_checker_state("EXCEPTION_OPEN") == "DEGRADED"
