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
    _ensure_schema_migrations_table(connection=connection)
    applied = _load_applied_migration_checksums(connection=connection, namespace=namespace)
    for migration in migrations:
        existing_checksum = applied.get(migration.version)
        if existing_checksum is not None:
            _raise_if_checksum_changed(
                namespace=namespace,
                version=migration.version,
                stored_checksum=existing_checksum,
                expected_checksum=migration.checksum,
            )
            continue
        sql = migration.sql_path.read_text(encoding="utf-8")
        _execute_sql_statements(connection=connection, sql=sql)
        _insert_schema_migration_record(
            connection=connection,
            namespace=namespace,
            migration=migration,
        )
    connection.commit()


def _ensure_schema_migrations_table(*, connection: Any) -> None:
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


def _load_applied_migration_checksums(*, connection: Any, namespace: str) -> dict[str, str]:
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
        if existing_checksum is not None:
            _raise_if_checksum_changed(
                namespace=namespace,
                version=version,
                stored_checksum=existing_checksum,
                expected_checksum=checksum,
            )
        applied[version] = checksum
    return applied


def _raise_if_checksum_changed(
    *,
    namespace: str,
    version: str,
    stored_checksum: str,
    expected_checksum: str,
) -> None:
    if stored_checksum != expected_checksum:
        raise RuntimeError(f"POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}")


def _insert_schema_migration_record(
    *,
    connection: Any,
    namespace: str,
    migration: PostgresMigration,
) -> None:
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


def _execute_sql_statements(*, connection: Any, sql: str) -> None:
    for statement in _split_sql_statements(sql):
        normalized = statement.strip()
        if not normalized:
            continue
        connection.execute(normalized)


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    start = 0
    index = 0
    dollar_tag: str | None = None
    in_single_quote = False
    in_double_quote = False
    while index < len(sql):
        char = sql[index]
        if dollar_tag is not None:
            index, dollar_tag = _advance_dollar_quoted_sql(
                sql=sql,
                index=index,
                dollar_tag=dollar_tag,
            )
            continue
        if in_single_quote:
            index, in_single_quote = _advance_single_quoted_sql(sql=sql, index=index)
            continue
        if in_double_quote:
            index, in_double_quote = _advance_double_quoted_sql(sql=sql, index=index)
            continue
        if char == "'":
            in_single_quote = True
            index += 1
            continue
        if char == '"':
            in_double_quote = True
            index += 1
            continue
        if char == "$":
            tag = _dollar_quote_tag_at(sql=sql, index=index)
            if tag is not None:
                dollar_tag = tag
                index += len(tag)
                continue
        # Comments are skipped whole. Without this a semicolon inside a comment
        # ends the statement, and the migration silently runs a truncated
        # fragment plus a nonsense one - the failure looks like invalid SQL
        # somewhere in the middle of a comment, which is a confusing place to
        # start debugging. Explaining a statement is exactly when a semicolon
        # gets written.
        if sql.startswith("--", index):
            index = _advance_line_comment_sql(sql=sql, index=index)
            continue
        if sql.startswith("/*", index):
            index = _advance_block_comment_sql(sql=sql, index=index)
            continue
        if char == ";":
            statements.append(sql[start:index])
            start = index + 1
        index += 1
    statements.append(sql[start:])
    return statements


def _advance_line_comment_sql(*, sql: str, index: int) -> int:
    """Return the index just past a ``--`` comment, which ends at the newline."""

    newline = sql.find("\n", index)
    return len(sql) if newline == -1 else newline + 1


def _advance_block_comment_sql(*, sql: str, index: int) -> int:
    """Return the index just past a ``/* */`` comment.

    PostgreSQL nests block comments, so the depth is tracked rather than
    stopping at the first ``*/``. An unterminated comment consumes the rest of
    the input, which is what PostgreSQL would also reject.
    """

    depth = 0
    while index < len(sql):
        if sql.startswith("/*", index):
            depth += 1
            index += 2
            continue
        if sql.startswith("*/", index):
            depth -= 1
            index += 2
            if depth == 0:
                return index
            continue
        index += 1
    return index


def _advance_dollar_quoted_sql(
    *,
    sql: str,
    index: int,
    dollar_tag: str,
) -> tuple[int, str | None]:
    if sql.startswith(dollar_tag, index):
        return index + len(dollar_tag), None
    return index + 1, dollar_tag


def _advance_single_quoted_sql(*, sql: str, index: int) -> tuple[int, bool]:
    char = sql[index]
    if char == "'" and index + 1 < len(sql) and sql[index + 1] == "'":
        return index + 2, True
    if char == "'":
        return index + 1, False
    return index + 1, True


def _advance_double_quoted_sql(*, sql: str, index: int) -> tuple[int, bool]:
    if sql[index] == '"':
        return index + 1, False
    return index + 1, True


def _dollar_quote_tag_at(*, sql: str, index: int) -> str | None:
    end = sql.find("$", index + 1)
    if end == -1:
        return None
    tag_body = sql[index + 1 : end]
    if tag_body and not (
        (tag_body[0].isalpha() or tag_body[0] == "_")
        and all(char.isalnum() or char == "_" for char in tag_body)
    ):
        return None
    return sql[index : end + 1]


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
