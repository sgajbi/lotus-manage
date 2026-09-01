from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    ROOT
    / "src"
    / "infrastructure"
    / "postgres_migrations"
    / "dpm"
    / "0021_idea_management_actions.sql"
)


def test_idea_management_action_migration_enforces_scope_version_and_history() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS dpm_idea_management_actions" in sql
    assert "UNIQUE (tenant_id, legal_entity_code, intake_id)" in sql
    assert "idempotency_scope_hash TEXT NOT NULL UNIQUE" in sql
    assert "CHECK (status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED'))" in sql
    assert "CHECK (source_event_version >= 1)" in sql
    assert "CREATE TABLE IF NOT EXISTS dpm_idea_management_action_events" in sql
    assert "UNIQUE (action_id, source_event_version)" in sql
    assert "ON DELETE RESTRICT" in sql
