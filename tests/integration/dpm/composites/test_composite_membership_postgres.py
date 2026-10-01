"""Real PostgreSQL proof for composite-definition and membership durability (#714)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

import pytest

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "composite membership durable PostgreSQL proof"


def _definition(*, tenant_id: str, composite_id: str, **updates: Any) -> DpmCompositeDefinition:
    values: dict[str, Any] = {
        "tenant_id": tenant_id,
        "composite_id": composite_id,
        "definition_version": "2026.10",
        "display_name": "Private Banking Global Balanced Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": DpmCompositeSourceAuthority(
            policy_version="composite-source-authority.v1"
        ),
        "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "created_by": "pm-ops",
        "correlation_id": f"corr-definition-{composite_id}",
    }
    values.update(updates)
    return DpmCompositeDefinition(**values)


def _revision(
    *, tenant_id: str, composite_id: str, revision: str, **updates: Any
) -> DpmCompositeMembershipRevision:
    values: dict[str, Any] = {
        "tenant_id": tenant_id,
        "composite_id": composite_id,
        "definition_version": "2026.10",
        "membership_revision": revision,
        "policy_version": "composite-eligibility.v1",
        "source_cut_id": "core-cut-2026-10-01",
        "decisions": [
            DpmCompositeMembershipDecision(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                effective_from="2026-01-01",
                source_snapshot_id="manage-membership-source-2026-01-01",
            )
        ],
        "decided_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "decided_by": "composite-committee",
        "correlation_id": f"corr-membership-{composite_id}-{revision}",
    }
    values.update(updates)
    return DpmCompositeMembershipRevision(**values)


def test_postgres_preserves_tenant_fence_immutable_replay_and_restart_read() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-composite-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    definition = _definition(tenant_id=tenant_id, composite_id=composite_id)
    repository.save_definition(definition=definition)
    repository.save_definition(definition=definition)

    restarted = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    assert (
        restarted.get_definition(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition.definition_version,
        )
        == definition
    )
    assert (
        restarted.get_definition(
            tenant_id="other-tenant",
            composite_id=composite_id,
            definition_version=definition.definition_version,
        )
        is None
    )
    assert restarted.list_definitions(tenant_id=tenant_id, limit=10, offset=0) == [definition]
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT"):
        restarted.save_definition(
            definition=_definition(
                tenant_id=tenant_id,
                composite_id=composite_id,
                display_name="Conflicting composite definition",
            )
        )

    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    restarted.save_membership_revision(revision=revision)
    restarted.save_membership_revision(revision=revision)
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT"
    ):
        restarted.save_membership_revision(
            revision=_revision(
                tenant_id=tenant_id,
                composite_id=composite_id,
                revision=revision.membership_revision,
                policy_version="composite-eligibility.v2",
            )
        )
    assert (
        restarted.get_membership_revision(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition.definition_version,
            membership_revision=revision.membership_revision,
        )
        == revision
    )
    assert (
        restarted.get_membership_revision(
            tenant_id="other-tenant",
            composite_id=composite_id,
            definition_version=definition.definition_version,
            membership_revision=revision.membership_revision,
        )
        is None
    )


def test_postgres_requires_existing_definition_and_correction_parent() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-composite-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_DEFINITION_NOT_FOUND"
    ):
        repository.save_membership_revision(revision=revision)

    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    correction = _revision(
        tenant_id=tenant_id,
        composite_id=composite_id,
        revision="2026.10.2",
        supersedes_membership_revision=revision.membership_revision,
        affected_from="2026-02-01",
        affected_to="2026-02-28",
    )
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND"
    ):
        repository.save_membership_revision(revision=correction)

    repository.save_membership_revision(revision=revision)
    repository.save_membership_revision(revision=correction)
    assert repository.list_membership_revisions(
        tenant_id=tenant_id,
        composite_id=composite_id,
        definition_version="2026.10",
        limit=10,
        offset=0,
    ) == [correction, revision]
