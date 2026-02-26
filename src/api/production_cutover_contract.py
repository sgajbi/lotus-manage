from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Any

from src.api.persistence_profile import (
    app_persistence_profile_name,
    validate_persistence_profile_guardrails,
)
from src.api.routers.dpm_runs_config import supportability_postgres_dsn
from src.api.routers.proposals_config import proposal_postgres_dsn


def validate_production_cutover_contract(*, check_migrations: bool) -> None:
    if app_persistence_profile_name() != "PRODUCTION":
        raise RuntimeError("CUTOVER_PROFILE_NOT_PRODUCTION")
    validate_persistence_profile_guardrails()
    if check_migrations:
        validate_cutover_migrations_applied()


def validate_cutover_migrations_applied() -> None:
    if find_spec("psycopg") is None:
        raise RuntimeError("CUTOVER_POSTGRES_DRIVER_MISSING")
    import psycopg
    from psycopg.rows import dict_row

    for namespace, dsn in (
        ("dpm", supportability_postgres_dsn()),
        ("proposals", proposal_postgres_dsn()),
    ):
        expected_versions = expected_migration_versions(namespace=namespace)
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            applied_versions = applied_migration_versions(
                connection=connection,
                namespace=namespace,
            )
        missing = sorted(set(expected_versions) - set(applied_versions))
        if missing:
            raise RuntimeError(f"CUTOVER_MIGRATION_MISSING:{namespace}:{missing[0]}")


def expected_migration_versions(*, namespace: str) -> list[str]:
    migrations_path = (
        Path(__file__).parents[1] / "infrastructure" / "postgres_migrations" / namespace
    )
    if not migrations_path.exists():
        raise RuntimeError(f"POSTGRES_MIGRATIONS_NAMESPACE_NOT_FOUND:{namespace}")
    versions = [
        migration_path.stem.split("_", maxsplit=1)[0]
        for migration_path in sorted(migrations_path.glob("*.sql"))
    ]
    if not versions:
        raise RuntimeError(f"CUTOVER_MIGRATIONS_EMPTY:{namespace}")
    return versions


def applied_migration_versions(*, connection: Any, namespace: str) -> list[str]:
    exists_row = connection.execute(
        "SELECT to_regclass('public.schema_migrations') AS regclass"
    ).fetchone()
    if not exists_row or exists_row["regclass"] is None:
        raise RuntimeError("CUTOVER_SCHEMA_MIGRATIONS_TABLE_MISSING")
    rows = connection.execute(
        """
        SELECT version
        FROM schema_migrations
        WHERE namespace = %s
        ORDER BY version ASC
        """,
        (namespace,),
    ).fetchall()
    return [
        normalize_stored_migration_version(
            namespace=namespace,
            stored_version=row["version"],
        )
        for row in rows
    ]


def normalize_stored_migration_version(*, namespace: str, stored_version: str) -> str:
    prefix = f"{namespace}:"
    return stored_version[len(prefix) :] if stored_version.startswith(prefix) else stored_version
