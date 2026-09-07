"""Which statements a fake psycopg connection should acknowledge, not model.

Three fake connections carried their own copy of this keyword list, so
migration 0027 - which drops one index and creates another - broke two of them
and left the third latently broken. Adding a keyword in three places is the
kind of duplication that gets fixed twice and forgotten once.

The fakes exist to model DML for one table each. Schema statements from
`apply_postgres_migrations` are not theirs to model, and are proven against a
real engine in the PostgreSQL lanes; acknowledging them here keeps the fake
loud about DML it genuinely does not handle.
"""

from __future__ import annotations

# The migration runner splits each file on `;`, so a statement is matched on
# its own rather than inheriting a keyword from earlier in its file - an index
# statement needs its own entry even when its migration also creates a table.
# `CREATE UNIQUE INDEX` does not contain the substring `CREATE INDEX`, and
# `DROP INDEX` shares no keyword with any of the others.
MIGRATION_DDL_KEYWORDS = (
    "CREATE TABLE",
    "ALTER TABLE",
    "CREATE INDEX",
    "CREATE UNIQUE INDEX",
    "DROP INDEX",
    "schema_migrations",
)


def is_migration_ddl(sql: str) -> bool:
    """True when this statement is schema work a table fake should let pass.

    Migration files open with a comment block, so a startswith check on the
    keyword never matches - the keyword is looked for anywhere in the text.
    """

    return any(keyword in sql for keyword in MIGRATION_DDL_KEYWORDS)
