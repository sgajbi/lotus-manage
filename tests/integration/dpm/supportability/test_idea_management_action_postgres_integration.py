from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from src.core.rebalance_runs.idea_management_action import (
    create_idea_management_action,
    record_idea_management_review_decision,
)
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepositoryConflictError,
)
from src.infrastructure.rebalance_runs.idea_management_actions_postgres import (
    PostgresIdeaManagementActionRepository,
)


_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()
pytestmark = pytest.mark.skipif(not _DSN, reason="DPM_POSTGRES_INTEGRATION_DSN is required")


def _action(*, suffix: str, fingerprint: str = "sha256:0123456789ab"):
    return create_idea_management_action(
        intake_id=f"iai_{suffix}",
        tenant_id="tenant-private-bank-sg",
        legal_entity_code="SGPB",
        portfolio_id=f"portfolio_{suffix}",
        idea_candidate_id=f"candidate_{suffix}",
        conversion_intent_id=f"conversion_{suffix}",
        source_refs=(
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": f"candidate_{suffix}",
                "content_hash": "sha256:abc123",
            },
        ),
        request_fingerprint=fingerprint,
        idempotency_scope_hash=f"sha256:{suffix[:24]:0<24}",
        actor_id="svc-lotus-idea",
        actor_role="SERVICE",
        correlation_id=f"corr_{suffix}",
        created_at=datetime.now(timezone.utc),
    )


def test_postgres_realization_survives_restart_replays_and_fences_stale_writer() -> None:
    suffix = uuid.uuid4().hex[:20]
    repository = PostgresIdeaManagementActionRepository(dsn=_DSN)
    original = _action(suffix=suffix)

    created = repository.create_or_replay(action=original)
    restarted_repository = PostgresIdeaManagementActionRepository(dsn=_DSN)
    reloaded = restarted_repository.get_by_intake_id(
        tenant_id=original.tenant_id,
        legal_entity_code=original.legal_entity_code,
        intake_id=original.intake_id,
    )
    replay = restarted_repository.create_or_replay(action=original)

    assert created.created is True
    assert reloaded == original
    assert replay.created is False
    assert replay.action == original
    assert (
        restarted_repository.get_by_intake_id(
            tenant_id="tenant-private-bank-hk",
            legal_entity_code="HKPB",
            intake_id=original.intake_id,
        )
        is None
    )

    approved = record_idea_management_review_decision(
        original,
        workflow_action="APPROVE",
        expected_source_event_version=1,
        actor_id="pm-001",
        actor_role="PORTFOLIO_MANAGER",
        reason_code="management_review_approved",
        correlation_id=f"corr_review_{suffix}",
    )
    persisted = restarted_repository.update(
        action=approved,
        expected_source_event_version=1,
    )
    assert persisted.status == "APPROVED"
    assert persisted.source_event_version == 2

    rejected_from_stale_copy = record_idea_management_review_decision(
        original,
        workflow_action="REJECT",
        expected_source_event_version=1,
        actor_id="pm-002",
        actor_role="DPM_MANAGER",
        reason_code="mandate_constraint_conflict",
        correlation_id=f"corr_stale_{suffix}",
    )
    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT",
    ):
        restarted_repository.update(
            action=rejected_from_stale_copy,
            expected_source_event_version=1,
        )

    after_restart = PostgresIdeaManagementActionRepository(dsn=_DSN).get_by_intake_id(
        tenant_id=original.tenant_id,
        legal_entity_code=original.legal_entity_code,
        intake_id=original.intake_id,
    )
    assert after_restart is not None
    assert after_restart.status == "APPROVED"
    assert [event.event_type for event in after_restart.events] == [
        "INTAKE_ACCEPTED",
        "APPROVE",
    ]

    recovered_by_conversion = PostgresIdeaManagementActionRepository(
        dsn=_DSN
    ).get_by_conversion_intent(
        tenant_id=original.tenant_id,
        legal_entity_code=original.legal_entity_code,
        portfolio_id=original.portfolio_id,
        conversion_intent_id=original.conversion_intent_id,
    )
    assert recovered_by_conversion == after_restart
    assert (
        restarted_repository.get_by_conversion_intent(
            tenant_id=original.tenant_id,
            legal_entity_code=original.legal_entity_code,
            portfolio_id="portfolio-out-of-scope",
            conversion_intent_id=original.conversion_intent_id,
        )
        is None
    )


def test_postgres_realization_rejects_changed_request_for_scoped_idempotency() -> None:
    suffix = uuid.uuid4().hex[:20]
    repository = PostgresIdeaManagementActionRepository(dsn=_DSN)
    repository.create_or_replay(action=_action(suffix=suffix))

    with pytest.raises(
        IdeaManagementActionRepositoryConflictError,
        match="IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT",
    ):
        repository.create_or_replay(
            action=_action(suffix=suffix, fingerprint="sha256:ba9876543210")
        )
