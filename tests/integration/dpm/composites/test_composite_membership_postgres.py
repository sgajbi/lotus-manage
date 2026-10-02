"""Real PostgreSQL proof for composite-definition and membership durability (#714)."""

from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import uuid

import pytest
import psycopg
from psycopg.rows import dict_row

import src.infrastructure.postgres_migrations as migrations_module
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
    DpmCompositeMembershipRevisionCommand,
)
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from src.infrastructure.mandates.serialization import dump_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations
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


def test_postgres_publication_cursor_receipt_and_restart() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-publication-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    first = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    second = _revision(
        tenant_id=tenant_id,
        composite_id=composite_id,
        revision="2026.10.2",
        supersedes_membership_revision="2026.10.1",
        affected_from="2026-02-01",
        affected_to="2026-02-28",
    )
    repository.save_membership_revision(revision=first)
    repository.save_membership_revision(revision=first)
    after_response_loss = DpmCompositeMembershipApplicationService(
        repository=repository
    ).save_membership_revision(
        command=DpmCompositeMembershipRevisionCommand(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=first.definition_version,
            membership_revision=first.membership_revision,
            policy_version=first.policy_version,
            source_cut_id=first.source_cut_id,
            decisions=first.decisions,
            actor_id=first.decided_by,
            correlation_id=first.correlation_id,
            supersedes_membership_revision=None,
            affected_from=None,
            affected_to=None,
        )
    )
    assert after_response_loss == first
    repository.save_membership_revision(revision=second)

    restarted = PostgresDpmCompositeRepository(dsn=dsn)
    first_page = restarted.list_publications(tenant_id=tenant_id, after_sequence=0, limit=1)
    assert len(first_page.items) == 1
    assert first_page.has_more is True
    assert first_page.items[0].membership_content_hash == first.content_hash
    assert first_page.items[0].completeness == "UNVERIFIED"
    second_page = restarted.list_publications(
        tenant_id=tenant_id, after_sequence=first_page.next_sequence, limit=1
    )
    assert len(second_page.items) == 1
    assert second_page.items[0].membership_content_hash == second.content_hash
    assert second_page.items[0].supersedes_membership_revision == "2026.10.1"
    assert second_page.has_more is False
    assert second_page.high_watermark == first_page.high_watermark
    assert (
        restarted.get_publication(tenant_id="other-tenant", sequence=first_page.next_sequence)
        is None
    )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_CURSOR_AHEAD"):
        restarted.list_publications(
            tenant_id=tenant_id, after_sequence=second_page.high_watermark + 1, limit=1
        )

    from src.core.composite_publication import DpmCompositePublicationReceipt

    receipt = DpmCompositePublicationReceipt(
        tenant_id=tenant_id,
        publication_sequence=first_page.next_sequence,
        membership_content_hash=first.content_hash,
        consumer_id="lotus-performance",
        receipt_evidence_hash="sha256:consumer-retrieval-proof",
        disposition="RECEIVED",
        received_at=datetime.now(timezone.utc),
        correlation_id="corr-consumer-retrieval",
    )
    assert restarted.save_receipt(receipt=receipt) is True
    assert restarted.save_receipt(receipt=receipt) is False
    after_restart = PostgresDpmCompositeRepository(dsn=dsn)
    assert after_restart.list_receipts(
        tenant_id=tenant_id, publication_sequence=first_page.next_sequence
    ) == [receipt]
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_HASH_MISMATCH"):
        after_restart.save_receipt(
            receipt=receipt.model_copy(update={"membership_content_hash": "sha256:wrong"})
        )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_NOT_FOUND"):
        after_restart.save_receipt(
            receipt=receipt.model_copy(
                update={"publication_sequence": second_page.high_watermark + 100}
            )
        )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_RECEIPT_IMMUTABLE_CONFLICT"):
        after_restart.save_receipt(
            receipt=receipt.model_copy(update={"receipt_evidence_hash": "sha256:different"})
        )


def test_postgres_migration_backfills_preexisting_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = postgres_dsn_or_skip(_PROOF)
    suffix = uuid.uuid4().hex[:12]
    schema = f"composite_publication_{suffix}"
    tenant_id = f"tenant-upgrade-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    all_migrations = migrations_module._load_migrations(namespace="dpm")  # noqa: SLF001
    prior_migrations = [migration for migration in all_migrations if migration.version < "0036"]
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute(f'CREATE SCHEMA "{schema}"')
        connection.commit()
        try:
            connection.execute(f'SET search_path TO "{schema}"')
            monkeypatch.setattr(
                migrations_module, "_load_migrations", lambda namespace: prior_migrations
            )
            apply_postgres_migrations(connection=connection, namespace="dpm")
            definition = _definition(tenant_id=tenant_id, composite_id=composite_id)
            revision = _revision(
                tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1"
            )
            connection.execute(
                """
                INSERT INTO dpm_composite_definitions (
                    tenant_id, composite_id, definition_version, inception_date,
                    content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    tenant_id,
                    composite_id,
                    definition.definition_version,
                    definition.inception_date,
                    definition.content_hash,
                    dump_model_json(definition),
                ),
            )
            connection.execute(
                """
                INSERT INTO dpm_composite_membership_revisions (
                    tenant_id, composite_id, definition_version, membership_revision,
                    decided_at, content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    tenant_id,
                    composite_id,
                    revision.definition_version,
                    revision.membership_revision,
                    revision.decided_at,
                    revision.content_hash,
                    dump_model_json(revision),
                ),
            )
            connection.commit()
            monkeypatch.setattr(
                migrations_module, "_load_migrations", lambda namespace: all_migrations
            )
            apply_postgres_migrations(connection=connection, namespace="dpm")
            row = connection.execute(
                """
                SELECT p.sequence, p.membership_content_hash, p.published_at
                FROM dpm_composite_membership_publications AS p
                WHERE p.tenant_id = %s
                """,
                (tenant_id,),
            ).fetchone()
            assert row is not None
            assert row["membership_content_hash"] == revision.content_hash
            assert row["published_at"] > revision.decided_at
            apply_postgres_migrations(connection=connection, namespace="dpm")
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM dpm_composite_membership_publications"
            ).fetchone()
            assert count["count"] == 1
        finally:
            connection.rollback()
            connection.execute("SET search_path TO public")
            connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
            connection.commit()


def test_postgres_concurrent_publishers_leave_no_tenant_cursor_gap() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-parallel-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    revisions = [
        _revision(tenant_id=tenant_id, composite_id=composite_id, revision=f"2026.10.{index}")
        for index in range(1, 7)
    ]
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(
            executor.map(
                lambda revision: repository.save_membership_revision(revision=revision), revisions
            )
        )
    page = repository.list_publications(tenant_id=tenant_id, after_sequence=0, limit=10)
    assert len(page.items) == 6
    assert len({item.sequence for item in page.items}) == 6
    assert {item.membership_content_hash for item in page.items} == {
        revision.content_hash for revision in revisions
    }
    assert page.has_more is False


def test_postgres_refuses_publication_hash_divergence() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-integrity-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    repository.save_membership_revision(revision=revision)
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """
            UPDATE dpm_composite_membership_publications
            SET membership_content_hash = %s
            WHERE tenant_id = %s AND composite_id = %s
            """,
            ("sha256:diverged", tenant_id, composite_id),
        )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_IMMUTABLE_CONFLICT"):
        repository.save_membership_revision(revision=revision)
