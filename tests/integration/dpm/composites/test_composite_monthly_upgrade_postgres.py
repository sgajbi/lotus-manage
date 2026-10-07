"""Forward upgrade preserves populated canonical v1/v2 rows and retrieval receipts."""

from datetime import datetime, timezone

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

import src.infrastructure.postgres_migrations as migrations
from src.core.composite_definition_versions import decode_composite_definition
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_publication import DpmCompositePublicationReceipt
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.infrastructure.composites import membership_store, universe_store, publication
from tests.composite_authority_helpers import frozen_authority_pack
from tests.composite_monthly_eligibility_helpers import retained_repository, source_snapshot
from tests.integration.dpm.network_runtime import disposable_database


TABLES = (
    "dpm_composite_definitions",
    "dpm_composite_membership_revisions",
    "dpm_composite_universe_attestations",
    "dpm_composite_membership_publications",
    "dpm_composite_publication_receipts",
)


def retained_rows(dsn):
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        return {
            table: connection.execute(
                sql.SQL("SELECT to_jsonb(t) AS row FROM {} t ORDER BY to_jsonb(t)::text").format(
                    sql.Identifier(table)
                )
            ).fetchall()
            for table in TABLES
        }


def seed_historical_canonical(connection, definition, membership, universe):
    """Seed the actual0039 schema; current definition writes require0042 custody."""
    connection.execute(
        "INSERT INTO dpm_composite_definitions (tenant_id,composite_id,definition_version,inception_date,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
        (
            definition.tenant_id,
            definition.composite_id,
            definition.definition_version,
            definition.inception_date,
            definition.content_hash,
            definition.model_dump_json(),
        ),
    )
    membership_store.store_membership_revision(connection=connection, revision=membership)
    universe_store.store_universe_attestation(connection=connection, attestation=universe)


def test_0039_populated_v1_v2_upgrade_to_0041_is_additive_and_repeatable(monkeypatch):
    original_loader = migrations._load_migrations
    with monkeypatch.context() as before:
        before.setattr(
            migrations,
            "_load_migrations",
            lambda *, namespace: [
                item for item in original_loader(namespace=namespace) if item.version <= "0039"
            ],
        )
        with disposable_database() as dsn:
            snapshot = source_snapshot()
            seed, universe = retained_repository(snapshot)
            scope = dict(
                tenant_id=snapshot.tenant_id,
                composite_id=snapshot.composite_id,
                definition_version=snapshot.definition_version,
            )
            packet = frozen_authority_pack()["external_versions"]["original"]
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                seed_historical_canonical(
                    connection,
                    seed.get_definition(**scope),
                    seed.get_membership_revision(
                        **scope, membership_revision="synthetic-membership"
                    ),
                    universe,
                )
                seed_historical_canonical(
                    connection,
                    decode_composite_definition(packet["definition"]),
                    DpmCompositeMembershipRevision.model_validate(packet["membership"]),
                    DpmCompositeUniverseAttestation.model_validate(packet["attestation"]),
                )
                for tenant in (snapshot.tenant_id, packet["definition"]["tenant_id"]):
                    published = connection.execute(
                        "SELECT sequence,membership_content_hash FROM dpm_composite_membership_publications WHERE tenant_id=%s",
                        (tenant,),
                    ).fetchone()
                    assert publication.save_receipt(
                        connection=connection,
                        receipt=DpmCompositePublicationReceipt(
                            tenant_id=tenant,
                            publication_sequence=published["sequence"],
                            membership_content_hash=published["membership_content_hash"],
                            consumer_id="lotus-performance",
                            receipt_evidence_hash="sha256:" + "b" * 64,
                            disposition="RECEIVED",
                            received_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                            correlation_id="synthetic-upgrade-receipt",
                        ),
                    )
            prior = retained_rows(dsn)
            assert all(prior[table] for table in TABLES)
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                assert (
                    connection.execute(
                        "SELECT to_regclass('dpm_composite_monthly_policy_proposals') AS name"
                    ).fetchone()["name"]
                    is None
                )
            # Preserve this historical0039→0041 proof. The separate staged-upgrade
            # test owns populated0041→0042 and current repository replay.
            before.setattr(
                migrations,
                "_load_migrations",
                lambda *, namespace: [
                    item for item in original_loader(namespace=namespace) if item.version <= "0041"
                ],
            )
            for _ in range(2):
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    records = connection.execute(
                        "SELECT version FROM schema_migrations WHERE version IN ('dpm:0040','dpm:0041') ORDER BY version"
                    ).fetchall()
                    assert [row["version"] for row in records] == ["dpm:0040", "dpm:0041"]
                    assert (
                        connection.execute(
                            "SELECT to_regclass('dpm_composite_eligibility_subjects') AS name"
                        ).fetchone()["name"]
                        is None
                    )
                assert retained_rows(dsn) == prior
