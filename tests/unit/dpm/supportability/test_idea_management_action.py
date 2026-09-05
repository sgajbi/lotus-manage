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


def _action(
    *,
    fingerprint: str = "sha256:0123456789ab",
    intake_id: str = "iai_001",
    candidate_id: str = "idea_candidate_001",
    idempotency_scope_hash: str = "sha256:0123456789abcdef01234567",
):
    return create_idea_management_action(
        intake_id=intake_id,
        tenant_id="tenant-private-bank-sg",
        legal_entity_code="SGPB",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        idea_candidate_id=candidate_id,
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
        idempotency_scope_hash=idempotency_scope_hash,
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


def test_repository_reads_current_action_by_exact_conversion_scope() -> None:
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

    recovered = repository.get_by_conversion_intent(
        tenant_id=approved.tenant_id,
        legal_entity_code=approved.legal_entity_code,
        portfolio_id=approved.portfolio_id,
        conversion_intent_id=approved.conversion_intent_id,
    )

    assert recovered == approved
    assert (
        repository.get_by_conversion_intent(
            tenant_id=approved.tenant_id,
            legal_entity_code=approved.legal_entity_code,
            portfolio_id="PB_SG_OTHER_001",
            conversion_intent_id=approved.conversion_intent_id,
        )
        is None
    )


def test_repository_rejects_second_action_for_same_conversion_scope() -> None:
    repository = InMemoryIdeaManagementActionRepository()
    original = _action()
    repository.create_or_replay(action=original)
    conflicting = _action(
        fingerprint="sha256:ba9876543210",
        intake_id="iai_changed",
        candidate_id="idea_candidate_changed",
        idempotency_scope_hash="sha256:ba9876543210ba9876543210",
    )

    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT",
    ):
        repository.create_or_replay(action=conflicting)

    assert (
        repository.get_by_conversion_intent(
            tenant_id=original.tenant_id,
            legal_entity_code=original.legal_entity_code,
            portfolio_id=original.portfolio_id,
            conversion_intent_id=original.conversion_intent_id,
        )
        == original
    )


def test_conversion_lookup_rejects_portfolio_scope_before_repository_io() -> None:
    from src.api.services.idea_management_action_service import (
        IdeaManagementActionService,
    )
    from src.core.rebalance_runs.idea_action_intake import IdeaActionIntakeScopeError
    from src.core.rebalance_runs.idea_action_intake_authority import (
        IdeaActionIntakePrincipal,
    )

    class _RepositoryThatMustNotBeCalled:
        def get_by_conversion_intent(self, **kwargs):
            raise AssertionError("repository I/O must follow portfolio authorization")

    principal = IdeaActionIntakePrincipal(
        actor_id="svc-lotus-idea",
        role="SERVICE",
        tenant_id="tenant-private-bank-sg",
        legal_entity_code="SGPB",
        correlation_id="corr-read-001",
        service_identity="lotus-idea",
        capabilities=frozenset({"manage.idea_action_intake.read"}),
        portfolio_ids=frozenset({"PB_SG_GLOBAL_BAL_001"}),
    )
    service = IdeaManagementActionService(repository=_RepositoryThatMustNotBeCalled())

    with pytest.raises(
        IdeaActionIntakeScopeError,
        match="IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN",
    ):
        service.get_outcome_history_by_conversion_intent(
            portfolio_id="PB_SG_OTHER_001",
            conversion_intent_id="conversion_intent_001",
            principal=principal,
        )


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


def _action_at(created_at):
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
        request_fingerprint="sha256:0123456789ab",
        idempotency_scope_hash="sha256:0123456789abcdef01234567",
        actor_id="svc-lotus-idea",
        actor_role="SERVICE",
        correlation_id="corr-intake-001",
        created_at=created_at,
    )


def test_domain_fields_refuse_blank_and_naive_time() -> None:
    """The aggregate's own validation: identity fields are never whitespace
    and event time is never naive - a naive timestamp silently reinterpreted
    as local time would corrupt the monotonic history it orders."""

    action = _action()
    event = action.events[0]

    # event_type is a Literal (its own guard); the trim validator protects the
    # plain identity strings - whitespace passes min_length and must still fail.
    with pytest.raises(ValueError, match="IDEA_MANAGEMENT_ACTION_EVENT_FIELD_REQUIRED"):
        type(event).model_validate({**event.model_dump(), "actor_id": "  "})
    with pytest.raises(ValueError, match="IDEA_MANAGEMENT_ACTION_FIELD_REQUIRED"):
        action.model_validate({**action.model_dump(), "tenant_id": "   "})
    # The factory converts caller time to UTC; a naive datetime silently
    # reinterpreted as local would corrupt the monotonic history it orders,
    # so it is refused at the door rather than guessed at.
    with pytest.raises(ValueError, match="IDEA_MANAGEMENT_ACTION_TIMEZONE_REQUIRED"):
        _action_at(datetime(2026, 4, 22, 9, 0, 0))


def test_in_memory_update_speaks_the_full_conflict_vocabulary() -> None:
    """The fake must fail exactly like the real adapter: unknown action,
    stale expected version, and a non-sequential next version are three
    distinct conflicts, not one."""

    repository = InMemoryIdeaManagementActionRepository()
    action = _action()
    repository.create_or_replay(action=action)

    unknown = action.model_copy(update={"action_id": "act-unknown"})
    with pytest.raises(
        IdeaManagementActionRepositoryConflictError, match="IDEA_MANAGEMENT_ACTION_NOT_FOUND"
    ):
        repository.update(action=unknown, expected_source_event_version=1)

    skipping = action.model_copy(update={"source_event_version": 5})
    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_MANAGEMENT_ACTION_VERSION_SEQUENCE_INVALID",
    ):
        repository.update(action=skipping, expected_source_event_version=1)


def test_intake_vocabulary_refuses_whitespace_where_length_checks_cannot() -> None:
    """min_length counts raw characters, so "  " passes it; the trim
    validators are what keep a whitespace identifier, source-ref field, or
    reason code from masquerading as a value. One test per vocabulary,
    because each guards a different contract surface."""

    from src.core.rebalance_runs.idea_action_intake import (
        IDEA_ACTION_INTAKE_REQUEST_EXAMPLE,
        IdeaActionIntakeRequest,
        IdeaActionSourceRef,
        IdeaManagementActionDecisionRequest,
        idea_action_received_at,
    )

    # None is a legitimate absence for optional ref fields - only whitespace
    # masquerading as a value is refused.
    assert (
        IdeaActionSourceRef.model_validate(
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_candidate_001",
                "content_hash": None,
            }
        ).content_hash
        is None
    )

    with pytest.raises(ValueError, match="IDEA_ACTION_SOURCE_REF_REQUIRED"):
        IdeaActionSourceRef.model_validate(
            {
                "source_system": "lotus-idea",
                "source_type": "  ",
                "source_id": "idea_candidate_001",
                "content_hash": "sha256:abc123",
            }
        )

    with pytest.raises(ValueError, match="IDEA_ACTION_IDENTIFIER_REQUIRED"):
        IdeaActionIntakeRequest.model_validate(
            {**IDEA_ACTION_INTAKE_REQUEST_EXAMPLE, "portfolio_id": "   "}
        )

    with pytest.raises(ValueError, match="IDEA_MANAGEMENT_ACTION_REASON_CODE_REQUIRED"):
        IdeaManagementActionDecisionRequest.model_validate(
            {
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "  ",
            }
        )

    # A naive received-at reinterpreted as local time would skew every
    # receipt it stamps; refused, never guessed.
    with pytest.raises(ValueError, match="IDEA_ACTION_INTAKE_TIMEZONE_REQUIRED"):
        idea_action_received_at(datetime(2026, 4, 22, 9, 0, 0))


def test_service_translates_repository_update_conflict_to_domain_conflict() -> None:
    """The service speaks domain vocabulary upward: a repository update
    conflict (stale fencing version) surfaces as the domain's conflict error,
    which the API maps to 409 - never the raw repository type."""

    from src.api.services.idea_management_action_service import (
        IdeaManagementActionService,
    )
    from src.core.rebalance_runs.idea_management_action import (
        IdeaManagementActionConflictError,
    )
    from src.core.rebalance_runs.idea_action_intake_authority import (
        IdeaActionIntakePrincipal,
    )

    repository = InMemoryIdeaManagementActionRepository()
    action = _action()
    repository.create_or_replay(action=action)
    principal = IdeaActionIntakePrincipal(
        actor_id="pm-001",
        role="PORTFOLIO_MANAGER",
        tenant_id=action.tenant_id,
        legal_entity_code=action.legal_entity_code,
        correlation_id="corr-review-001",
        service_identity="lotus-manage-ui",
        capabilities=frozenset({"manage.idea_action_intake.review"}),
        portfolio_ids=frozenset({action.portfolio_id}),
    )

    class _ConflictOnUpdate:
        """A concurrent writer lands between the service's read and its
        update: the domain check passes (expected matches what was read) and
        the REPOSITORY is the layer that detects the race."""

        def get_by_intake_id(self, *, tenant_id, legal_entity_code, intake_id):
            return repository.get_by_intake_id(
                tenant_id=tenant_id,
                legal_entity_code=legal_entity_code,
                intake_id=intake_id,
            )

        def update(self, *, action, expected_source_event_version):
            raise IdeaManagementActionRepositoryConflictError(
                "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT"
            )

    racing_service = IdeaManagementActionService(repository=_ConflictOnUpdate())

    with pytest.raises(IdeaManagementActionConflictError):
        racing_service.record_review_decision(
            intake_id=action.intake_id,
            workflow_action="APPROVE",
            expected_source_event_version=1,
            reason_code="REVIEWED_OK",
            principal=principal,
            correlation_id="corr-review-001",
        )


def test_postgres_adapter_translates_unavailability_at_its_connection_funnel(monkeypatch) -> None:
    """The one branch real-Postgres integration cannot hit without killing
    the database mid-suite: every operation reaches PostgreSQL through
    _connect, and an access failure there must surface as the repository
    protocol's own unavailability error - never a Postgres type crossing the
    boundary the router-infrastructure gate protects."""

    import src.infrastructure.rebalance_runs.idea_management_actions_postgres as adapter_module
    from src.core.rebalance_runs.idea_management_action_repository import (
        IdeaManagementActionRepositoryUnavailableError,
    )
    from src.infrastructure.postgres_access import PostgresUnavailableError

    adapter = adapter_module.PostgresIdeaManagementActionRepository.__new__(
        adapter_module.PostgresIdeaManagementActionRepository
    )
    adapter._dsn = "postgresql://manage:manage@127.0.0.1:1/never"

    def _refuse(*args, **kwargs):
        raise PostgresUnavailableError("POSTGRES_CONNECTION_UNAVAILABLE")

    monkeypatch.setattr(adapter_module, "connect_postgres", _refuse)

    with pytest.raises(IdeaManagementActionRepositoryUnavailableError):
        adapter._connect()


def test_postgres_adapter_refuses_misconfiguration_at_construction(monkeypatch) -> None:
    """An empty DSN and a missing driver are configuration facts caught at
    the door, each with its own bounded reason - the dependency layer
    translates them to the repository's unavailability for callers."""

    import src.infrastructure.rebalance_runs.idea_management_actions_postgres as adapter_module
    from src.infrastructure.postgres_access import PostgresConfigurationError

    with pytest.raises(
        PostgresConfigurationError, match="DPM_IDEA_MANAGEMENT_ACTION_POSTGRES_DSN_REQUIRED"
    ):
        adapter_module.PostgresIdeaManagementActionRepository(dsn="")

    monkeypatch.setattr(adapter_module, "has_psycopg", lambda: False)
    with pytest.raises(
        PostgresConfigurationError, match="DPM_IDEA_MANAGEMENT_ACTION_POSTGRES_DRIVER_MISSING"
    ):
        adapter_module.PostgresIdeaManagementActionRepository(dsn="postgresql://x")
