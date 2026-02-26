from types import SimpleNamespace

import pytest

import src.api.production_cutover_contract as contract_module
from src.api.production_cutover_contract import (
    applied_migration_versions,
    expected_migration_versions,
    normalize_stored_migration_version,
    validate_production_cutover_contract,
)


class _FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, *, table_exists=True, rows=None):
        self._table_exists = table_exists
        self._rows = rows or []

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if "to_regclass('public.schema_migrations')" in sql:
            return _FakeCursor(
                row={"regclass": "schema_migrations" if self._table_exists else None}
            )
        if "FROM schema_migrations" in sql:
            return _FakeCursor(rows=self._rows)
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_validate_cutover_requires_production_profile(monkeypatch):
    monkeypatch.setattr(contract_module, "app_persistence_profile_name", lambda: "LOCAL")
    with pytest.raises(RuntimeError) as exc:
        validate_production_cutover_contract(check_migrations=False)
    assert str(exc.value) == "CUTOVER_PROFILE_NOT_PRODUCTION"


def test_validate_cutover_delegates_to_guardrails(monkeypatch):
    called = {"guardrails": 0}
    monkeypatch.setattr(contract_module, "app_persistence_profile_name", lambda: "PRODUCTION")
    monkeypatch.setattr(
        contract_module,
        "validate_persistence_profile_guardrails",
        lambda: called.__setitem__("guardrails", called["guardrails"] + 1),
    )
    validate_production_cutover_contract(check_migrations=False)
    assert called["guardrails"] == 1


def test_validate_cutover_can_include_migration_check(monkeypatch):
    called = {"migrations": 0}
    monkeypatch.setattr(contract_module, "app_persistence_profile_name", lambda: "PRODUCTION")
    monkeypatch.setattr(contract_module, "validate_persistence_profile_guardrails", lambda: None)
    monkeypatch.setattr(
        contract_module,
        "validate_cutover_migrations_applied",
        lambda: called.__setitem__("migrations", called["migrations"] + 1),
    )
    validate_production_cutover_contract(check_migrations=True)
    assert called["migrations"] == 1


def test_expected_migration_versions_for_namespaces():
    dpm_versions = expected_migration_versions(namespace="dpm")
    proposals_versions = expected_migration_versions(namespace="proposals")
    assert "0001" in dpm_versions
    assert "0001" in proposals_versions


def test_normalize_stored_migration_version():
    assert normalize_stored_migration_version(namespace="dpm", stored_version="dpm:0002") == "0002"
    assert normalize_stored_migration_version(namespace="dpm", stored_version="0002") == "0002"


def test_applied_migration_versions_requires_schema_migrations_table():
    connection = _FakeConnection(table_exists=False)
    with pytest.raises(RuntimeError) as exc:
        applied_migration_versions(connection=connection, namespace="dpm")
    assert str(exc.value) == "CUTOVER_SCHEMA_MIGRATIONS_TABLE_MISSING"


def test_applied_migration_versions_normalizes_namespaced_versions():
    connection = _FakeConnection(rows=[{"version": "dpm:0001"}, {"version": "0002"}])
    assert applied_migration_versions(connection=connection, namespace="dpm") == ["0001", "0002"]


def test_validate_cutover_migrations_applied_detects_missing(monkeypatch):
    class _FakePsycopg:
        @staticmethod
        def connect(_dsn, row_factory):
            assert row_factory is not None

            class _Context:
                def __enter__(self):
                    return _FakeConnection(rows=[{"version": "dpm:0001"}])

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _Context()

    monkeypatch.setattr(contract_module, "find_spec", lambda _name: object())
    monkeypatch.setitem(__import__("sys").modules, "psycopg", _FakePsycopg)
    monkeypatch.setitem(
        __import__("sys").modules,
        "psycopg.rows",
        SimpleNamespace(dict_row=object()),
    )
    monkeypatch.setattr(
        contract_module,
        "expected_migration_versions",
        lambda namespace: ["0001", "0002"] if namespace == "dpm" else ["0001"],
    )
    monkeypatch.setattr(contract_module, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(contract_module, "proposal_postgres_dsn", lambda: "postgresql://adv")

    with pytest.raises(RuntimeError) as exc:
        contract_module.validate_cutover_migrations_applied()
    assert str(exc.value) == "CUTOVER_MIGRATION_MISSING:dpm:0002"


def test_validate_cutover_migrations_applied_requires_postgres_driver(monkeypatch):
    monkeypatch.setattr(contract_module, "find_spec", lambda _name: None)
    with pytest.raises(RuntimeError) as exc:
        contract_module.validate_cutover_migrations_applied()
    assert str(exc.value) == "CUTOVER_POSTGRES_DRIVER_MISSING"


def test_expected_migration_versions_requires_existing_namespace():
    with pytest.raises(RuntimeError) as exc:
        expected_migration_versions(namespace="missing_namespace")
    assert str(exc.value) == "POSTGRES_MIGRATIONS_NAMESPACE_NOT_FOUND:missing_namespace"


def test_expected_migration_versions_rejects_empty_namespace(tmp_path, monkeypatch):
    fake_module_file = tmp_path / "api" / "production_cutover_contract.py"
    fake_module_file.parent.mkdir(parents=True)
    fake_module_file.write_text("# test", encoding="utf-8")
    empty_namespace_dir = tmp_path / "infrastructure" / "postgres_migrations" / "empty_namespace"
    empty_namespace_dir.mkdir(parents=True)
    monkeypatch.setattr(contract_module, "__file__", str(fake_module_file))

    with pytest.raises(RuntimeError) as exc:
        expected_migration_versions(namespace="empty_namespace")
    assert str(exc.value) == "CUTOVER_MIGRATIONS_EMPTY:empty_namespace"
