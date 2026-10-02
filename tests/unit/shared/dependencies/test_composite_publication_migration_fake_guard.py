from tests.support.postgres_migration_sql import is_composite_publication_backfill


def test_fake_acknowledges_only_the_known_publication_backfill() -> None:
    migration_sql = """
        INSERT INTO dpm_composite_membership_publications (
            tenant_id, composite_id, definition_version, membership_revision,
            membership_content_hash
        ) SELECT tenant_id, composite_id, definition_version, membership_revision, content_hash
          FROM dpm_composite_membership_revisions
          ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision) DO NOTHING
    """
    assert is_composite_publication_backfill(migration_sql)
    assert not is_composite_publication_backfill(
        "INSERT INTO dpm_composite_membership_publications (tenant_id) VALUES ('spoof')"
    )
    assert not is_composite_publication_backfill(
        migration_sql.replace("FROM dpm_composite_membership_revisions", "FROM untrusted_rows")
    )
