from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    ROOT
    / "src"
    / "infrastructure"
    / "postgres_migrations"
    / "dpm"
    / "0019_mandate_temporal_read_indexes.sql"
)
IDENTITY_MIGRATION = MIGRATION.with_name("0020_mandate_temporal_snapshot_identity.sql")


def test_temporal_read_migration_defines_deterministic_covering_indexes() -> None:
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").lower().split())

    assert "idx_dpm_mandate_snapshots_portfolio_temporal" in sql
    assert "portfolio_id, as_of_date desc, mandate_version desc, mandate_id desc" in sql
    assert "idx_dpm_mandate_health_mandate_temporal" in sql
    assert "mandate_id, as_of_date desc, created_at desc, health_snapshot_id desc" in sql


def test_temporal_snapshot_identity_preserves_unchanged_binding_versions() -> None:
    sql = " ".join(IDENTITY_MIGRATION.read_text(encoding="utf-8").lower().split())

    assert "drop constraint if exists dpm_mandate_snapshots_mandate_id_mandate_version_key" in sql
    assert "unique (mandate_id, mandate_version, as_of_date)" in sql
