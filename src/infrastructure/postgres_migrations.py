from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PostgresMigration:
    version: str
    sql_path: Path
    checksum: str


def apply_postgres_migrations(*, connection: Any, namespace: str) -> None:
    lock_key = _migration_lock_key(namespace=namespace)
    connection.execute("SELECT pg_advisory_lock(%s::bigint)", (lock_key,))
    try:
        _apply_migrations_locked(connection=connection, namespace=namespace)
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        connection.execute("SELECT pg_advisory_unlock(%s::bigint)", (lock_key,))


def _apply_migrations_locked(*, connection: Any, namespace: str) -> None:
    migrations = _load_migrations(namespace=namespace)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            namespace TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    rows = connection.execute(
        """
        SELECT version, checksum
        FROM schema_migrations
        WHERE namespace = %s
        ORDER BY version ASC
        """,
        (namespace,),
    ).fetchall()
    applied: dict[str, str] = {}
    for row in rows:
        version = _extract_namespace_version(
            namespace=namespace,
            stored_version=str(row["version"]),
        )
        checksum = str(row["checksum"])
        existing_checksum = applied.get(version)
        if existing_checksum is not None and existing_checksum != checksum:
            raise RuntimeError(f"POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}")
        applied[version] = checksum
    for migration in migrations:
        existing_checksum = applied.get(migration.version)
        if existing_checksum is not None:
            if existing_checksum != migration.checksum:
                raise RuntimeError(
                    f"POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{migration.version}"
                )
            continue
        sql = migration.sql_path.read_text(encoding="utf-8")
        _execute_sql_statements(connection=connection, sql=sql)
        connection.execute(
            """
            INSERT INTO schema_migrations (
                version,
                namespace,
                checksum,
                applied_at
            ) VALUES (%s, %s, %s, %s)
            """,
            (
                _stored_version(namespace=namespace, version=migration.version),
                namespace,
                migration.checksum,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    connection.commit()


def _execute_sql_statements(*, connection: Any, sql: str) -> None:
    for statement in sql.split(";"):
        normalized = statement.strip()
        if not normalized:
            continue
        connection.execute(normalized)


def _load_migrations(*, namespace: str) -> list[PostgresMigration]:
    namespace_path = Path(__file__).with_name("postgres_migrations") / namespace
    if not namespace_path.exists():
        raise RuntimeError(f"POSTGRES_MIGRATIONS_NAMESPACE_NOT_FOUND:{namespace}")
    migrations: list[PostgresMigration] = []
    for sql_path in sorted(namespace_path.glob("*.sql")):
        version = sql_path.stem.split("_", maxsplit=1)[0]
        sql = sql_path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(
            PostgresMigration(
                version=version,
                sql_path=sql_path,
                checksum=checksum,
            )
        )
    return migrations


def _migration_lock_key(*, namespace: str) -> int:
    digest = hashlib.sha256(namespace.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


def _stored_version(*, namespace: str, version: str) -> str:
    return f"{namespace}:{version}"


def _extract_namespace_version(*, namespace: str, stored_version: str) -> str:
    prefix = f"{namespace}:"
    if stored_version.startswith(prefix):
        return stored_version[len(prefix) :]
    return stored_version
