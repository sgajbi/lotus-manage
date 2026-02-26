import sys
from types import SimpleNamespace

import src.infrastructure.dpm_policy_packs.postgres as postgres_module
from src.core.dpm.policy_packs import DpmPolicyPackDefinition
from src.infrastructure.dpm_policy_packs.postgres import PostgresDpmPolicyPackRepository


class _FakeCursor:
    def __init__(self, row=None, rows=None, rowcount=0):
        self._row = row
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self):
        self.policy_packs = {}
        self.schema_migrations = {}

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql == "SELECT pg_advisory_lock(%s::bigint)":
            return _FakeCursor()
        if sql == "SELECT pg_advisory_unlock(%s::bigint)":
            return _FakeCursor()
        if sql.startswith("CREATE TABLE"):
            return _FakeCursor()
        if "FROM schema_migrations" in sql:
            namespace = args[0]
            rows = [
                {"version": version, "checksum": checksum}
                for (stored_namespace, version), checksum in self.schema_migrations.items()
                if stored_namespace == namespace
            ]
            rows = sorted(rows, key=lambda row: row["version"])
            return _FakeCursor(rows=rows)
        if "INSERT INTO schema_migrations" in sql:
            self.schema_migrations[(args[1], args[0])] = args[2]
            return _FakeCursor()
        if "SELECT policy_pack_id, version, definition_json FROM dpm_policy_packs ORDER BY" in sql:
            rows = sorted(self.policy_packs.values(), key=lambda row: row["policy_pack_id"])
            return _FakeCursor(rows=rows)
        if "SELECT policy_pack_id, version, definition_json FROM dpm_policy_packs WHERE" in sql:
            return _FakeCursor(self.policy_packs.get(args[0]))
        if "INSERT INTO dpm_policy_packs" in sql:
            self.policy_packs[args[0]] = {
                "policy_pack_id": args[0],
                "version": args[1],
                "definition_json": args[2],
            }
            return _FakeCursor()
        if "DELETE FROM dpm_policy_packs WHERE policy_pack_id = %s" in sql:
            existed = args[0] in self.policy_packs
            self.policy_packs.pop(args[0], None)
            return _FakeCursor(rowcount=1 if existed else 0)
        raise AssertionError(f"Unhandled SQL: {sql}")

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def _build_repository(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        PostgresDpmPolicyPackRepository,
        "_connect",
        lambda self: connection,  # noqa: ARG005
    )
    return (
        PostgresDpmPolicyPackRepository(dsn="postgresql://user:pass@localhost:5432/dpm"),
        connection,
    )


def test_postgres_policy_pack_repository_requires_dsn():
    try:
        PostgresDpmPolicyPackRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing policy pack postgres dsn")


def test_postgres_policy_pack_repository_requires_driver(monkeypatch):
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)
    try:
        PostgresDpmPolicyPackRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    except RuntimeError as exc:
        assert str(exc) == "DPM_POLICY_PACK_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing psycopg driver")


def test_postgres_policy_pack_repository_roundtrip(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    policy_pack = DpmPolicyPackDefinition(
        policy_pack_id="dpm_standard_v1",
        version="1",
    )
    repository.upsert_policy_pack(policy_pack)

    loaded = repository.get_policy_pack(policy_pack_id="dpm_standard_v1")
    assert loaded is not None
    assert loaded.policy_pack_id == "dpm_standard_v1"
    assert loaded.version == "1"

    rows = repository.list_policy_packs()
    assert [row.policy_pack_id for row in rows] == ["dpm_standard_v1"]

    assert repository.delete_policy_pack(policy_pack_id="dpm_standard_v1") is True
    assert repository.delete_policy_pack(policy_pack_id="dpm_standard_v1") is False


def test_postgres_policy_pack_repository_connect_uses_imported_driver(monkeypatch):
    calls = {}

    class _FakePsycopg:
        @staticmethod
        def connect(dsn, row_factory):
            calls["dsn"] = dsn
            calls["row_factory"] = row_factory
            return object()

    class _FakeRepository(PostgresDpmPolicyPackRepository):
        def _init_db(self):
            return None

    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (_FakePsycopg, "DICT_ROW"),
    )

    repository = _FakeRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    repository._connect()
    assert calls == {
        "dsn": "postgresql://user:pass@localhost:5432/dpm",
        "row_factory": "DICT_ROW",
    }


def test_import_psycopg_returns_driver_and_row_factory(monkeypatch):
    fake_psycopg = object()
    fake_dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", SimpleNamespace(dict_row=fake_dict_row))

    psycopg, dict_row = postgres_module._import_psycopg()
    assert psycopg is fake_psycopg
    assert dict_row is fake_dict_row
