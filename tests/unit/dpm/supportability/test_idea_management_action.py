from datetime import datetime, timezone

import pytest

from src.core.rebalance_runs.idea_management_action import (
    IdeaManagementActionConflictError,
    create_idea_management_action,
    record_idea_management_review_decision,
)
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepositoryConflictError,
)
from src.infrastructure.rebalance_runs.idea_management_actions_in_memory import (
    InMemoryIdeaManagementActionRepository,
)


NOW = datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc)


def _action(*, fingerprint: str = "sha256:0123456789ab"):
    return create_idea_management_action(
        intake_id="iai_001",
        tenant_id="tenant-private-bank-sg",
        legal_entity_code="SGPB",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id="idea_candidate_001",
        conversion_intent_id="conversion_intent_001",
        source_refs=(
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_candidate_001",
                "content_hash": "sha256:abc123",
            },
        ),
        request_fingerprint=fingerprint,
        idempotency_scope_hash="sha256:0123456789abcdef01234567",
        actor_id="svc-lotus-idea",
        actor_role="SERVICE",
        correlation_id="corr-intake-001",
        created_at=NOW,
    )


def test_create_management_action_is_pending_review_with_source_owned_event() -> None:
    action = _action()

    assert action.action_id.startswith("ima_")
    assert action.status == "PENDING_REVIEW"
    assert action.source_event_version == 1
    assert len(action.events) == 1
    assert action.events[0].event_type == "INTAKE_ACCEPTED"
    assert action.events[0].causation_id == "conversion_intent_001"


def test_review_decisions_follow_existing_manage_workflow_policy() -> None:
    action = _action()

    changes_requested = record_idea_management_review_decision(
        action,
        workflow_action="REQUEST_CHANGES",
        expected_source_event_version=1,
        actor_id="pm-001",
        actor_role="PORTFOLIO_MANAGER",
        reason_code="additional_mandate_evidence_required",
        correlation_id="corr-review-001",
        decided_at=NOW,
    )
    approved = record_idea_management_review_decision(
        changes_requested,
        workflow_action="APPROVE",
        expected_source_event_version=2,
        actor_id="pm-001",
        actor_role="PORTFOLIO_MANAGER",
        reason_code="management_review_approved",
        correlation_id="corr-review-002",
        decided_at=NOW,
    )

    assert changes_requested.status == "PENDING_REVIEW"
    assert approved.status == "APPROVED"
    assert approved.source_event_version == 3
    assert [event.event_type for event in approved.events] == [
        "INTAKE_ACCEPTED",
        "REQUEST_CHANGES",
        "APPROVE",
    ]
    assert approved.events[-1].causation_id == changes_requested.events[-1].event_id


def test_review_decision_rejects_stale_version_and_invalid_transition() -> None:
    action = _action()

    with pytest.raises(
        IdeaManagementActionConflictError,
        match="IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT",
    ):
        record_idea_management_review_decision(
            action,
            workflow_action="APPROVE",
            expected_source_event_version=9,
            actor_id="pm-001",
            actor_role="PORTFOLIO_MANAGER",
            reason_code="management_review_approved",
            correlation_id="corr-review-stale",
            decided_at=NOW,
        )

    approved = record_idea_management_review_decision(
        action,
        workflow_action="APPROVE",
        expected_source_event_version=1,
        actor_id="pm-001",
        actor_role="PORTFOLIO_MANAGER",
        reason_code="management_review_approved",
        correlation_id="corr-review-approved",
        decided_at=NOW,
    )
    with pytest.raises(
        IdeaManagementActionConflictError,
        match="IDEA_MANAGEMENT_ACTION_INVALID_WORKFLOW_TRANSITION",
    ):
        record_idea_management_review_decision(
            approved,
            workflow_action="APPROVE",
            expected_source_event_version=2,
            actor_id="pm-001",
            actor_role="PORTFOLIO_MANAGER",
            reason_code="duplicate_approval",
            correlation_id="corr-review-duplicate",
            decided_at=NOW,
        )


def test_repository_replays_same_intake_without_duplicating_action() -> None:
    repository = InMemoryIdeaManagementActionRepository()

    first = repository.create_or_replay(action=_action())
    replay = repository.create_or_replay(action=_action())

    assert first.created is True
    assert replay.created is False
    assert replay.action == first.action


def test_repository_rejects_changed_payload_for_same_scoped_idempotency_key() -> None:
    repository = InMemoryIdeaManagementActionRepository()
    repository.create_or_replay(action=_action())

    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT",
    ):
        repository.create_or_replay(action=_action(fingerprint="sha256:ba9876543210"))


def test_repository_optimistic_update_rejects_concurrent_stale_writer() -> None:
    repository = InMemoryIdeaManagementActionRepository()
    original = repository.create_or_replay(action=_action()).action
    approved = record_idea_management_review_decision(
        original,
        workflow_action="APPROVE",
        expected_source_event_version=1,
        actor_id="pm-001",
        actor_role="PORTFOLIO_MANAGER",
        reason_code="management_review_approved",
        correlation_id="corr-review-approved",
        decided_at=NOW,
    )
    repository.update(action=approved, expected_source_event_version=1)

    rejected_from_stale_copy = record_idea_management_review_decision(
        original,
        workflow_action="REJECT",
        expected_source_event_version=1,
        actor_id="pm-002",
        actor_role="DPM_MANAGER",
        reason_code="mandate_constraint_conflict",
        correlation_id="corr-review-rejected",
        decided_at=NOW,
    )
    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT",
    ):
        repository.update(
            action=rejected_from_stale_copy,
            expected_source_event_version=1,
        )
