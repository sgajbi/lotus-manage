from contextlib import contextmanager

import psycopg
import pytest

import scripts.postgres_migrate as migration_cli
import src.infrastructure.postgres_migrations as migrations


@pytest.mark.parametrize("value", ["", " \t", "PRODUCITON", "prod", "secret-value"])
def test_invalid_profile_refuses_migration_before_driver_or_database_access(monkeypatch, value):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", value)
    monkeypatch.setattr("sys.argv", ["postgres_migrate.py", "--target", "dpm"])
    monkeypatch.setattr(
        migration_cli,
        "find_spec",
        lambda _name: pytest.fail("invalid profile consulted migration driver"),
    )
    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("invalid profile opened PostgreSQL"),
    )
    with pytest.raises(RuntimeError, match="^PERSISTENCE_PROFILE_UNSUPPORTED$"):
        migration_cli.main()


@pytest.mark.parametrize("value", [None, "LOCAL", " local ", "PRODUCTION", " production "])
def test_valid_profile_keeps_owned_migration_execution(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("APP_PERSISTENCE_PROFILE", raising=False)
    else:
        monkeypatch.setenv("APP_PERSISTENCE_PROFILE", value)
    monkeypatch.setattr("sys.argv", ["postgres_migrate.py", "--target", "dpm"])
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://synthetic-migrations")
    calls = []
    expected_connection = object()

    @contextmanager
    def connect(dsn, *, row_factory):
        assert dsn == "postgresql://synthetic-migrations"
        assert row_factory is not None
        calls.append("open")
        try:
            yield expected_connection
        finally:
            calls.append("close")

    def apply(*, connection, namespace):
        assert connection is expected_connection
        assert namespace == "dpm"
        calls.append("apply")

    monkeypatch.setattr(psycopg, "connect", connect)
    monkeypatch.setattr(migrations, "apply_postgres_migrations", apply)
    assert migration_cli.main() == 0
    assert calls == ["open", "apply", "close"]
