import json
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

import pytest

from src.core.construction import build_alternative_set, build_do_nothing_baseline
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.construction import postgres as postgres_module
from src.infrastructure.construction.postgres import PostgresConstructionRepository
from tests.unit.dpm.construction.test_alternative_engine import _ready_rebalance_result


def _alternative_set() -> ConstructionAlternativeSet:
    result = _ready_rebalance_result()
    return build_alternative_set(
        alternative_set_id="cas_repo_001",
        portfolio_id="pf_construct_1",
        as_of="2026-05-03",
        alternatives=[build_do_nothing_baseline(result=result)],
    ).model_copy(update={"tenant_id": "tenant_001", "request_hash": "sha256:repo"})


def test_in_memory_repository_persists_alternative_set_and_idempotency_lookup() -> None:
    repository = InMemoryConstructionRepository()
    alternative_set = _alternative_set()

    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-repo-001",
    )

    by_id = repository.get_alternative_set(
        alternative_set_id="cas_repo_001", tenant_id="tenant_001"
    )
    by_idempotency = repository.get_alternative_set_by_idempotency(
        idempotency_key="idem-repo-001", tenant_id="tenant_001"
    )

    assert by_id == alternative_set
    assert by_idempotency == alternative_set
    assert by_id is not alternative_set


def test_in_memory_repository_lists_alternative_sets_by_portfolio_newest_first() -> None:
    repository = InMemoryConstructionRepository()
    older = _alternative_set().model_copy(update={"alternative_set_id": "cas_repo_older"})
    newer = _alternative_set().model_copy(
        update={
            "alternative_set_id": "cas_repo_newer",
            "generated_at": older.generated_at + timedelta(seconds=1),
        }
    )
    other = _alternative_set().model_copy(
        update={"alternative_set_id": "cas_repo_other", "portfolio_id": "other_pf"}
    )

    repository.save_alternative_set(alternative_set=older, idempotency_key="idem-older")
    repository.save_alternative_set(alternative_set=other, idempotency_key="idem-other")
    repository.save_alternative_set(alternative_set=newer, idempotency_key="idem-newer")

    assert [
        row.alternative_set_id
        for row in repository.list_alternative_sets(
            portfolio_id="pf_construct_1", tenant_id="tenant_001", limit=10
        )
    ] == ["cas_repo_newer", "cas_repo_older"]
    assert [
        row.alternative_set_id
        for row in repository.list_alternative_sets(
            portfolio_id="pf_construct_1", tenant_id="tenant_001", limit=1
        )
    ] == ["cas_repo_newer"]


def test_in_memory_repository_records_latest_selection_decision() -> None:
    repository = InMemoryConstructionRepository()
    repository.save_alternative_set(
        alternative_set=_alternative_set(),
        idempotency_key="idem-repo-002",
    )
    selection = ConstructionAlternativeSelection(
        selection_id="casel_repo_001",
        tenant_id="tenant_001",
        alternative_set_id="cas_repo_001",
        alternative_id="alt_do_nothing_baseline",
        actor_id="pm_001",
        reason_code="CLIENT_TAX_SENSITIVITY",
        comment="Keep turnover at zero.",
        correlation_id="corr-selection-repo",
    )

    repository.save_selection(selection=selection)

    assert (
        repository.get_selection(alternative_set_id="cas_repo_001", tenant_id="tenant_001")
        == selection
    )


def test_in_memory_repository_scopes_ids_idempotency_lists_and_selections_by_tenant() -> None:
    repository = InMemoryConstructionRepository()
    tenant_a = _alternative_set()
    tenant_b = tenant_a.model_copy(
        update={"alternative_set_id": "cas_repo_tenant_b", "tenant_id": "tenant_002"}
    )
    repository.save_alternative_set(alternative_set=tenant_a, idempotency_key="shared-key")
    repository.save_alternative_set(alternative_set=tenant_b, idempotency_key="shared-key")

    assert (
        repository.get_alternative_set(
            alternative_set_id=tenant_a.alternative_set_id, tenant_id="tenant_002"
        )
        is None
    )
    assert (
        repository.get_alternative_set_by_idempotency(
            idempotency_key="shared-key", tenant_id="tenant_001"
        )
        == tenant_a
    )
    assert (
        repository.get_alternative_set_by_idempotency(
            idempotency_key="shared-key", tenant_id="tenant_002"
        )
        == tenant_b
    )
    assert repository.list_alternative_sets(
        portfolio_id="pf_construct_1", tenant_id="tenant_001", limit=10
    ) == [tenant_a]

    legacy = tenant_a.model_copy(update={"alternative_set_id": "cas_legacy", "tenant_id": None})
    repository._alternative_sets[legacy.alternative_set_id] = legacy  # noqa: SLF001
    assert (
        repository.get_alternative_set(
            alternative_set_id=legacy.alternative_set_id, tenant_id="tenant_001"
        )
        is None
    )


def test_postgres_repository_requires_dsn() -> None:
    try:
        PostgresConstructionRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_CONSTRUCTION_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing construction Postgres DSN")


def test_postgres_repository_requires_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.construction.postgres.has_psycopg", lambda: False)

    try:
        PostgresConstructionRepository(dsn="postgresql://user:pass@localhost:5432/manage")
    except RuntimeError as exc:
        assert str(exc) == "DPM_CONSTRUCTION_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing construction Postgres driver")


def test_postgres_repository_initializes_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _FakeConnection()
    monkeypatch.setattr("src.infrastructure.construction.postgres.has_psycopg", lambda: True)
    monkeypatch.setattr(
        "src.infrastructure.construction.postgres._import_psycopg",
        lambda: (_FakePsycopg(connection), "dict_row"),
    )
    applied: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        "src.infrastructure.construction.postgres.apply_postgres_migrations",
        lambda *, connection, namespace: applied.append((connection, namespace)),
    )

    repository = PostgresConstructionRepository(dsn="postgresql://user:pass@localhost:5432/manage")

    assert repository._dsn == "postgresql://user:pass@localhost:5432/manage"
    assert applied[0][0]._connection is connection  # noqa: SLF001
    assert applied[0][1] == "dpm"


def test_postgres_repository_persists_alternative_set_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    repository = _postgres_repository(monkeypatch, connection)
    alternative_set = _alternative_set()

    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-postgres-001",
    )
    by_id = repository.get_alternative_set(
        alternative_set_id="cas_repo_001", tenant_id="tenant_001"
    )
    by_idempotency = repository.get_alternative_set_by_idempotency(
        idempotency_key="idem-postgres-001", tenant_id="tenant_001"
    )

    assert by_id == alternative_set
    assert by_idempotency == alternative_set
    assert connection.commits == 1


def test_postgres_idempotency_guard_uses_managed_autocommit_coordination_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    repository = _postgres_repository(monkeypatch, connection)

    with repository.idempotency_guard(
        tenant_id="tenant_001",
        idempotency_key="idem-guard-001",
    ):
        assert connection.autocommit is True

    coordination_call = connection.connection_args[-1]
    assert coordination_call["application_name"] == "lotus-manage:construction-coordination"
    assert coordination_call["options"].startswith("-c statement_timeout=60000 ")
    assert sum("pg_advisory_lock" in query for query in connection.executed_queries) == 1
    assert sum("pg_advisory_unlock" in query for query in connection.executed_queries) == 1


def test_postgres_repository_lists_alternative_sets_by_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    repository = _postgres_repository(monkeypatch, connection)
    alternative_set = _alternative_set()

    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-postgres-list",
    )

    assert repository.list_alternative_sets(
        portfolio_id="pf_construct_1", tenant_id="tenant_001", limit=10
    ) == [alternative_set]
    assert (
        repository.list_alternative_sets(portfolio_id="other_pf", tenant_id="tenant_001", limit=10)
        == []
    )


def test_postgres_repository_records_latest_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _FakeConnection()
    repository = _postgres_repository(monkeypatch, connection)
    repository.save_alternative_set(
        alternative_set=_alternative_set(), idempotency_key="idem-selection"
    )
    selection = ConstructionAlternativeSelection(
        selection_id="casel_repo_001",
        tenant_id="tenant_001",
        alternative_set_id="cas_repo_001",
        alternative_id="alt_do_nothing_baseline",
        actor_id="pm_001",
        reason_code="CLIENT_TAX_SENSITIVITY",
        comment="Keep turnover at zero.",
        correlation_id="corr-selection-repo",
    )

    repository.save_selection(selection=selection)

    assert (
        repository.get_selection(alternative_set_id="cas_repo_001", tenant_id="tenant_001")
        == selection
    )
    assert connection.commits == 2


def test_postgres_repository_returns_none_for_missing_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    repository = _postgres_repository(monkeypatch, connection)

    assert repository.get_selection(alternative_set_id="missing", tenant_id="tenant_001") is None


def test_postgres_repository_payload_helpers_cover_missing_and_non_string_rows() -> None:
    assert postgres_module._alternative_set_from_row(None) is None
    assert postgres_module._payload({"payload_json": {"a": 1}}) == {"a": 1}
    assert postgres_module._payload({"payload_json": 3}) == "3"


def _postgres_repository(
    monkeypatch: pytest.MonkeyPatch,
    connection: "_FakeConnection",
) -> PostgresConstructionRepository:
    monkeypatch.setattr("src.infrastructure.construction.postgres.has_psycopg", lambda: True)
    monkeypatch.setattr(
        "src.infrastructure.construction.postgres._import_psycopg",
        lambda: (_FakePsycopg(connection), "dict_row"),
    )
    monkeypatch.setattr(
        "src.infrastructure.construction.postgres.apply_postgres_migrations",
        lambda *, connection, namespace: None,
    )
    return PostgresConstructionRepository(dsn="postgresql://user:pass@localhost:5432/manage")


class _FakePsycopg:
    def __init__(self, connection: "_FakeConnection") -> None:
        self._connection = connection

    def connect(self, dsn: str, **kwargs: Any) -> "_FakeConnection":
        self._connection.connection_args.append({"dsn": dsn, **kwargs})
        return self._connection


class _FakeConnection:
    def __init__(self) -> None:
        self.alternative_sets_by_id: dict[str, dict[str, Any]] = {}
        self.alternative_sets_by_idempotency: dict[str, dict[str, Any]] = {}
        self.selections_by_set_id: dict[str, dict[str, Any]] = {}
        self.connection_args: list[dict[str, Any]] = []
        self.executed_queries: list[str] = []
        self.commits = 0
        self.autocommit = False

    def execute(self, query: str, params: Sequence[Any] = ()) -> "_FakeCursor":
        normalized = " ".join(query.split())
        self.executed_queries.append(normalized)
        if normalized.startswith("SELECT pg_advisory_"):
            return _FakeCursor({})
        if normalized.startswith("INSERT INTO dpm_construction_alternative_sets"):
            return self._insert_alternative_set(params)
        if (
            "FROM dpm_construction_alternative_sets" in normalized
            and "WHERE alternative_set_id = %s AND tenant_id = %s" in normalized
        ):
            row = self.alternative_sets_by_id.get(str(params[0]))
            return _FakeCursor(row if row and row["tenant_id"] == str(params[1]) else None)
        if "WHERE tenant_id = %s AND idempotency_key = %s" in normalized:
            return _FakeCursor(self.alternative_sets_by_idempotency.get(f"{params[0]}:{params[1]}"))
        if "WHERE tenant_id = %s AND portfolio_id = %s" in normalized:
            return _FakeCursor(
                [
                    row
                    for row in self.alternative_sets_by_id.values()
                    if row["tenant_id"] == str(params[0]) and row["portfolio_id"] == str(params[1])
                ][: int(params[2])]
            )
        if normalized.startswith("INSERT INTO dpm_construction_alternative_selections"):
            return self._insert_selection(params)
        if "FROM dpm_construction_alternative_selections WHERE alternative_set_id" in normalized:
            row = self.selections_by_set_id.get(str(params[0]))
            return _FakeCursor(row if row and row["tenant_id"] == str(params[1]) else None)
        raise AssertionError(f"Unexpected construction repository query: {normalized}")

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass

    def _insert_alternative_set(self, params: Sequence[Any]) -> "_FakeCursor":
        alternative_set_id = str(params[0])
        tenant_id = str(params[1])
        idempotency_key = str(params[6])
        row = {
            "tenant_id": tenant_id,
            "portfolio_id": str(params[2]),
            "payload_json": json.loads(str(params[9])),
        }
        self.alternative_sets_by_id[alternative_set_id] = row
        self.alternative_sets_by_idempotency[f"{tenant_id}:{idempotency_key}"] = row
        return _FakeCursor(row)

    def _insert_selection(self, params: Sequence[Any]) -> "_FakeCursor":
        alternative_set_id = str(params[1])
        row = {"tenant_id": str(params[2]), "payload_json": json.loads(str(params[8]))}
        self.selections_by_set_id[alternative_set_id] = row
        return _FakeCursor({"selection_id": str(params[0])})


class _FakeCursor:
    def __init__(self, row: dict[str, Any] | list[dict[str, Any]] | None) -> None:
        self._row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self._row if isinstance(self._row, dict) else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._row if isinstance(self._row, list) else []
