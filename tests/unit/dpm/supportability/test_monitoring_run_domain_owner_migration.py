from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    ROOT
    / "src"
    / "infrastructure"
    / "postgres_migrations"
    / "dpm"
    / "0031_monitoring_run_domain_owner.sql"
)


def test_monitoring_run_owner_backfill_preserves_unattributable_history() -> None:
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").lower().split())

    assert "jsonb_set( payload_json, '{tenant_id}', to_jsonb(tenant_id), true )" in sql
    assert "tenant_id is not null" in sql
    assert "payload_json is not null" in sql
    assert "payload_json -> 'filters' ->> 'tenant_id' = tenant_id" in sql
    assert "coalesce" not in sql
