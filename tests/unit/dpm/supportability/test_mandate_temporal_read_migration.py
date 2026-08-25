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


def test_temporal_read_migration_defines_deterministic_covering_indexes() -> None:
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").lower().split())

    assert "idx_dpm_mandate_snapshots_portfolio_temporal" in sql
    assert "portfolio_id, as_of_date desc, mandate_version desc, mandate_id desc" in sql
    assert "idx_dpm_mandate_health_mandate_temporal" in sql
    assert "mandate_id, as_of_date desc, created_at desc, health_snapshot_id desc" in sql
