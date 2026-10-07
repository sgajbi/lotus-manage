import pytest

from src.infrastructure.postgres_migrations import _load_migrations, _split_sql_statements
from tests.support.postgres_migration_sql import (
    is_composite_publication_backfill,
    is_migration_ddl,
)
from tests.unit.dpm.supportability.test_dpm_policy_pack_postgres_repository import (
    _FakeConnection as PolicyPackConnection,
)
from tests.unit.dpm.supportability.test_dpm_postgres_repository_scaffold import (
    _FakeConnection as RunConnection,
)


def _reserved_definition_trigger():
    migration = next(
        migration for migration in _load_migrations(namespace="dpm") if migration.version == "0042"
    )
    statements = _split_sql_statements(migration.sql_path.read_text(encoding="utf-8"))
    return next(
        statement.strip()
        for statement in statements
        if statement.strip().startswith("CREATE CONSTRAINT TRIGGER")
    )


@pytest.mark.parametrize("connection_type", [PolicyPackConnection, RunConnection])
def test_supportability_fake_acknowledges_exact_deferred_finalization_ddl(connection_type):
    statement = _reserved_definition_trigger()
    assert is_migration_ddl(statement)
    assert connection_type().execute(statement) is not None


@pytest.mark.parametrize("connection_type", [PolicyPackConnection, RunConnection])
@pytest.mark.parametrize("change", ["name", "timing", "table", "function", "unknown_sql"])
def test_supportability_fake_still_refuses_unknown_constraint_and_product_sql(
    connection_type, change
):
    statement = _reserved_definition_trigger()
    unsupported = {
        "name": statement.replace(
            "dpm_composite_reserved_definition_finalization", "unrecognized_trigger"
        ),
        "timing": statement.replace("DEFERRABLE INITIALLY DEFERRED", "NOT DEFERRABLE"),
        "table": statement.replace("ON dpm_composite_definitions", "ON unrecognized_table"),
        "function": statement.replace(
            "dpm_require_composite_eligibility_finalization()", "unrecognized_function()"
        ),
        "unknown_sql": "SELECT unrecognized_product_mutation()",
    }[change]
    assert not is_migration_ddl(unsupported)
    with pytest.raises(AssertionError, match="Unhandled SQL|Unexpected SQL"):
        connection_type().execute(unsupported)


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


def test_fake_accepts_trigger_ddl_but_not_product_insert() -> None:
    assert is_migration_ddl(
        "CREATE FUNCTION dpm_publish_composite_membership_revision() RETURNS trigger"
    )
    assert is_migration_ddl("CREATE TRIGGER dpm_composite_membership_revision_publish AFTER INSERT")
    assert not is_migration_ddl(
        "INSERT INTO dpm_composite_membership_publications VALUES ('untrusted')"
    )
