"""Real PostgreSQL proof for composite-definition and membership durability (#714)."""

from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any
import uuid

import pytest
import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

import src.infrastructure.postgres_migrations as migrations_module
from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
    DpmCompositeMembershipRevisionCommand,
    DpmCompositeUniverseAttestationCommand,
)
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_universe import DpmCompositeUniverseSourceProduct
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


def _retry_revision_command(
    repository: PostgresDpmCompositeRepository, revision: DpmCompositeMembershipRevision
) -> DpmCompositeMembershipRevision:
    return DpmCompositeMembershipApplicationService(repository=repository).save_membership_revision(
        command=DpmCompositeMembershipRevisionCommand(
            tenant_id=revision.tenant_id,
            composite_id=revision.composite_id,
            definition_version=revision.definition_version,
            membership_revision=revision.membership_revision,
            policy_version=revision.policy_version,
            source_cut_id=revision.source_cut_id,
            decisions=revision.decisions,
            actor_id=revision.decided_by,
            correlation_id=revision.correlation_id,
            supersedes_membership_revision=revision.supersedes_membership_revision,
            affected_from=revision.affected_from,
            affected_to=revision.affected_to,
        )
    )


def _universe_command(
    revision: DpmCompositeMembershipRevision,
) -> DpmCompositeUniverseAttestationCommand:
    return DpmCompositeUniverseAttestationCommand(
        tenant_id=revision.tenant_id,
        composite_id=revision.composite_id,
        definition_version=revision.definition_version,
        membership_revision=revision.membership_revision,
        attestation_version="2026.10.1",
        coverage_from="2026-01-01",
        coverage_to="2026-12-31",
        policy_version=revision.policy_version,
        source_cut_id=revision.source_cut_id,
        source_products=[
            DpmCompositeUniverseSourceProduct(
                owner_service="lotus-manage",
                product_name="CompositeEligibilityUniverse",
                contract_version="v1",
                authority_scope="AUTHORITATIVE_UNIVERSE",
                source_cut_id=revision.source_cut_id,
                source_watermark="universe-sequence:1",
                content_hash="sha256:approved-universe-cut",
            )
        ],
        posture="COMPLETE",
        expected_portfolio_ids=["PB_SG_GLOBAL_BAL_001"],
        reason_code=None,
        actor_id="checker",
        correlation_id="corr-universe-race",
    )


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
    definition_page = restarted.list_definitions(tenant_id=tenant_id, limit=10, offset=0)
    assert definition_page.items == [definition]
    assert definition_page.count == 1
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
    history_page = repository.list_membership_revisions(
        tenant_id=tenant_id,
        composite_id=composite_id,
        definition_version="2026.10",
        limit=10,
        offset=0,
    )
    assert history_page.items == [correction, revision]
    assert history_page.count == 2


def test_postgres_page_counts_include_rows_beyond_offset_without_cross_tenant_leakage() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-count-{suffix}"
    other_tenant = f"tenant-other-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    for index in range(3):
        repository.save_definition(
            definition=_definition(tenant_id=tenant_id, composite_id=f"{composite_id}_{index}")
        )
    repository.save_definition(
        definition=_definition(tenant_id=other_tenant, composite_id=composite_id)
    )
    definition_page = repository.list_definitions(tenant_id=tenant_id, limit=1, offset=1)
    assert len(definition_page.items) == 1
    assert definition_page.count == 3
    assert repository.list_definitions(tenant_id=tenant_id, limit=1, offset=3).count == 3
    assert repository.list_definitions(tenant_id=other_tenant, limit=1, offset=0).count == 1

    scoped_composite = f"{composite_id}_0"
    for index in range(3):
        repository.save_membership_revision(
            revision=_revision(
                tenant_id=tenant_id,
                composite_id=scoped_composite,
                revision=f"2026.10.{index + 1}",
            )
        )
    repository.save_membership_revision(
        revision=_revision(
            tenant_id=other_tenant,
            composite_id=composite_id,
            revision="2026.10.1",
        )
    )
    history_page = repository.list_membership_revisions(
        tenant_id=tenant_id,
        composite_id=scoped_composite,
        definition_version="2026.10",
        limit=1,
        offset=1,
    )
    assert len(history_page.items) == 1
    assert history_page.count == 3
    assert (
        repository.list_membership_revisions(
            tenant_id=tenant_id,
            composite_id=scoped_composite,
            definition_version="2026.10",
            limit=1,
            offset=3,
        ).count
        == 3
    )
    assert (
        repository.list_membership_revisions(
            tenant_id=other_tenant,
            composite_id=scoped_composite,
            definition_version="2026.10",
            limit=1,
            offset=0,
        ).count
        == 0
    )


def test_registered_http_page_reports_real_postgres_total_count() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-http-count-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    base = f"/api/v1/rebalance/composites/{composite_id}/definitions/2026.10"
    headers = {"X-Tenant-Id": tenant_id, "X-Actor-Id": "pm-ops", "X-Role": "DPM_COMPOSITE_ADMIN"}
    try:
        with TestClient(app) as client:
            definition = _definition(tenant_id=tenant_id, composite_id=composite_id)
            definition_request = {
                "display_name": definition.display_name,
                "strategy_code": definition.strategy_code,
                "reporting_currency": definition.reporting_currency,
                "inception_date": definition.inception_date,
                "eligibility_policy_version": definition.eligibility_policy_version,
                "source_authority": definition.source_authority.model_dump(mode="json"),
                "correlation_id": definition.correlation_id,
            }
            assert client.put(base, headers=headers, json=definition_request).status_code == 200
            second_base = f"/api/v1/rebalance/composites/{composite_id}_SECOND/definitions/2026.10"
            assert (
                client.put(second_base, headers=headers, json=definition_request).status_code == 200
            )
            definitions = client.get(
                "/api/v1/rebalance/composites/definitions?limit=1&offset=1",
                headers=headers,
            )
            assert definitions.status_code == 200
            assert len(definitions.json()["items"]) == 1
            assert definitions.json()["count"] == 2
            for index in range(2):
                revision = _revision(
                    tenant_id=tenant_id,
                    composite_id=composite_id,
                    revision=f"2026.10.{index + 1}",
                )
                response = client.put(
                    f"{base}/membership/{revision.membership_revision}",
                    headers=headers,
                    json={
                        "policy_version": revision.policy_version,
                        "source_cut_id": revision.source_cut_id,
                        "decisions": [item.model_dump(mode="json") for item in revision.decisions],
                        "correlation_id": revision.correlation_id,
                    },
                )
                assert response.status_code == 200
            page = client.get(f"{base}/membership?limit=1&offset=1", headers=headers)
            assert page.status_code == 200
            assert len(page.json()["items"]) == 1
            assert page.json()["count"] == 2
            empty_page = client.get(f"{base}/membership?limit=1&offset=2", headers=headers)
            assert empty_page.json()["items"] == []
            assert empty_page.json()["count"] == 2
            foreign_page = client.get(
                f"{base}/membership?limit=1", headers={**headers, "X-Tenant-Id": "foreign"}
            )
            assert foreign_page.json()["count"] == 0
    finally:
        app.dependency_overrides.clear()


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
    after_response_loss = _retry_revision_command(repository, first)
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
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_RECEIPT_IMMUTABLE_CONFLICT"):
        after_restart.save_receipt(
            receipt=receipt.model_copy(update={"correlation_id": "corr-different-retrieval"})
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
            trigger_order = connection.execute(
                """
                SELECT tgname, (tgtype & 2) <> 0 AS before_insert
                FROM pg_trigger
                WHERE tgrelid = 'dpm_composite_membership_revisions'::regclass
                  AND NOT tgisinternal
                """
            ).fetchall()
            assert {row["tgname"]: row["before_insert"] for row in trigger_order} == {
                "dpm_composite_membership_revision_lock": True,
                "dpm_composite_membership_revision_publish": False,
            }
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
            # A previous application replica can still insert after the
            # migration but before traffic switches to the new writer. The
            # compatibility trigger must publish that revision atomically.
            late_revision = _revision(
                tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.2"
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
                    late_revision.definition_version,
                    late_revision.membership_revision,
                    late_revision.decided_at,
                    late_revision.content_hash,
                    dump_model_json(late_revision),
                ),
            )
            published_late = connection.execute(
                """
                SELECT membership_content_hash
                FROM dpm_composite_membership_publications
                WHERE tenant_id = %s AND membership_revision = %s
                """,
                (tenant_id, late_revision.membership_revision),
            ).fetchone()
            assert published_late is not None
            assert published_late["membership_content_hash"] == late_revision.content_hash
            apply_postgres_migrations(connection=connection, namespace="dpm")
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM dpm_composite_membership_publications"
            ).fetchone()
            assert count["count"] == 2
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
    sequence = (
        repository.list_publications(tenant_id=tenant_id, after_sequence=0, limit=1)
        .items[0]
        .sequence
    )
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
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"):
        repository.get_publication(tenant_id=tenant_id, sequence=sequence)
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"):
        repository.list_publications(tenant_id=tenant_id, after_sequence=0, limit=10)
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"):
        _retry_revision_command(repository, revision)


def test_postgres_api_retry_refuses_missing_publication() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-missing-publication-{suffix}"
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
            "DELETE FROM dpm_composite_membership_publications WHERE tenant_id = %s",
            (tenant_id,),
        )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"):
        _retry_revision_command(repository, revision)


def test_postgres_legacy_and_new_writer_share_lock_order_for_same_revision() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-mixed-writer-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    barrier = Barrier(2)

    def legacy_insert() -> None:
        with psycopg.connect(dsn) as connection:
            barrier.wait(timeout=5)
            connection.execute(
                """
                INSERT INTO dpm_composite_membership_revisions (
                    tenant_id, composite_id, definition_version, membership_revision,
                    decided_at, content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision)
                DO NOTHING
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

    def current_insert() -> None:
        barrier.wait(timeout=5)
        repository.save_membership_revision(revision=revision)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(legacy_insert), executor.submit(current_insert)]
        for future in futures:
            future.result(timeout=10)
    page = repository.list_publications(tenant_id=tenant_id, after_sequence=0, limit=10)
    assert len(page.items) == 1
    assert page.items[0].membership_content_hash == revision.content_hash


def test_registered_api_persists_universe_attestation_with_tenant_fence_and_restart() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-universe-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    base = f"/api/v1/rebalance/composites/{composite_id}/definitions/2026.10"
    revision_url = f"{base}/membership/2026.10.1"
    attestation_url = f"{revision_url}/universe-attestations/2026.10.1"
    admin_headers = {
        "X-Tenant-Id": tenant_id,
        "X-Actor-Id": "maker",
        "X-Role": "DPM_COMPOSITE_ADMIN",
    }
    attester_headers = {
        "X-Tenant-Id": tenant_id,
        "X-Actor-Id": "checker",
        "X-Role": "DPM_COMPOSITE_UNIVERSE_ATTESTER",
        "X-Service-Identity": "lotus-manage",
    }
    try:
        with TestClient(app) as client:
            definition = _definition(tenant_id=tenant_id, composite_id=composite_id)
            assert (
                client.put(
                    base,
                    headers=admin_headers,
                    json={
                        "display_name": definition.display_name,
                        "strategy_code": definition.strategy_code,
                        "reporting_currency": definition.reporting_currency,
                        "inception_date": definition.inception_date,
                        "eligibility_policy_version": definition.eligibility_policy_version,
                        "source_authority": definition.source_authority.model_dump(mode="json"),
                        "correlation_id": definition.correlation_id,
                    },
                ).status_code
                == 200
            )
            revision = _revision(
                tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1"
            )
            saved_revision = client.put(
                revision_url,
                headers=admin_headers,
                json={
                    "policy_version": revision.policy_version,
                    "source_cut_id": revision.source_cut_id,
                    "decisions": [item.model_dump(mode="json") for item in revision.decisions],
                    "correlation_id": revision.correlation_id,
                },
            )
            assert saved_revision.status_code == 200
            payload = {
                "coverage_from": "2026-01-01",
                "coverage_to": "2026-12-31",
                "policy_version": revision.policy_version,
                "source_cut_id": revision.source_cut_id,
                "source_products": [
                    {
                        "owner_service": "lotus-manage",
                        "product_name": "CompositeEligibilityUniverse",
                        "contract_version": "v1",
                        "authority_scope": "AUTHORITATIVE_UNIVERSE",
                        "source_cut_id": revision.source_cut_id,
                        "source_watermark": "universe-sequence:1",
                        "content_hash": "sha256:approved-universe-cut",
                    }
                ],
                "posture": "COMPLETE",
                "expected_portfolio_ids": ["PB_SG_GLOBAL_BAL_001"],
                "correlation_id": "corr-universe-attestation",
            }
            accepted = client.put(attestation_url, headers=attester_headers, json=payload)
            assert accepted.status_code == 200
            assert (
                accepted.json()["membership_content_hash"] == saved_revision.json()["content_hash"]
            )
            assert (
                client.get(
                    attestation_url,
                    headers={**admin_headers, "X-Tenant-Id": "foreign-tenant"},
                ).status_code
                == 404
            )

        restarted = PostgresDpmCompositeRepository(dsn=dsn)
        app.dependency_overrides[get_composite_membership_application_service] = lambda: (
            DpmCompositeMembershipApplicationService(repository=restarted)
        )
        with TestClient(app) as client:
            persisted = client.get(attestation_url, headers=admin_headers)
            replay = client.put(attestation_url, headers=attester_headers, json=payload)
            assert persisted.status_code == replay.status_code == 200
            assert persisted.json() == replay.json() == accepted.json()
            page = client.get(
                f"{revision_url}/universe-attestations?limit=1&offset=1",
                headers=admin_headers,
            )
            assert page.json()["items"] == []
            assert page.json()["count"] == 1
            conflict = client.put(
                attestation_url,
                headers=attester_headers,
                json=payload | {"correlation_id": "corr-different"},
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"]["code"] == (
                "COMPOSITE_UNIVERSE_ATTESTATION_IMMUTABLE_CONFLICT"
            )
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count, MIN(content_hash) AS content_hash
                FROM dpm_composite_universe_attestations
                WHERE tenant_id = %s AND composite_id = %s
                """,
                (tenant_id, composite_id),
            ).fetchone()
            assert row is not None
            assert row["count"] == 1
            assert row["content_hash"] == accepted.json()["content_hash"]
    finally:
        app.dependency_overrides.clear()


def test_postgres_concurrent_attestation_replay_converges_across_repository_instances() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-universe-race-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    repository.save_membership_revision(revision=revision)
    command = _universe_command(revision)
    barrier = Barrier(2)

    def attest() -> object:
        service = DpmCompositeMembershipApplicationService(
            repository=PostgresDpmCompositeRepository(dsn=dsn)
        )
        barrier.wait(timeout=5)
        return service.save_universe_attestation(command=command)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=10) for future in [executor.submit(attest) for _ in range(2)]
        ]
    assert results[0] == results[1]
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*) AS count FROM dpm_composite_universe_attestations
            WHERE tenant_id = %s AND composite_id = %s
            """,
            (tenant_id, composite_id),
        ).fetchone()
        assert count is not None
        assert count["count"] == 1


def test_postgres_universe_attestation_reads_fail_closed_on_stored_hash_divergence() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-universe-integrity-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    repository.save_definition(
        definition=_definition(tenant_id=tenant_id, composite_id=composite_id)
    )
    revision = _revision(tenant_id=tenant_id, composite_id=composite_id, revision="2026.10.1")
    repository.save_membership_revision(revision=revision)
    DpmCompositeMembershipApplicationService(repository=repository).save_universe_attestation(
        command=_universe_command(revision)
    )
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """
            UPDATE dpm_composite_universe_attestations SET content_hash = %s
            WHERE tenant_id = %s AND composite_id = %s
            """,
            ("sha256:diverged", tenant_id, composite_id),
        )
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_UNIVERSE_ATTESTATION_INTEGRITY_CONFLICT"
    ):
        repository.get_universe_attestation(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=revision.definition_version,
            membership_revision=revision.membership_revision,
            attestation_version="2026.10.1",
        )
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_UNIVERSE_ATTESTATION_INTEGRITY_CONFLICT"
    ):
        repository.list_universe_attestations(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=revision.definition_version,
            membership_revision=revision.membership_revision,
            limit=10,
            offset=0,
        )
