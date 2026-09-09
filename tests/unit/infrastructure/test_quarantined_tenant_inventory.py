from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from src.infrastructure.quarantined_tenant_inventory import (
    QUARANTINED_TENANT_DATASETS,
    QuarantinedTenantDataset,
    _json_scalar,
    _row_value,
    build_quarantined_tenant_inventory,
)


class _Result:
    def __init__(
        self, *, row: dict[str, Any] | None = None, rows: list[dict[str, Any]] | None = None
    ):
        self._row = row
        self._rows = rows or []

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _StringRow:
    def __getitem__(self, column: str) -> str:
        assert column == "value"
        return "indexed"


class _Connection:
    def __init__(
        self,
        *,
        rows: dict[str, list[dict[str, Any]]] | None = None,
        applied_versions: set[str] | None = None,
        read_only: str = "on",
    ) -> None:
        self.rows = rows or {}
        self.applied_versions = applied_versions or {
            "dpm:0003",
            "dpm:0024",
            "dpm:0025",
            "dpm:0026",
            "dpm:0027",
            "dpm:0028",
            "dpm:0029",
        }
        self.statements: list[str] = []
        self.rollback_count = 0
        self.read_only = read_only

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> _Result:
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if normalized == "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY":
            return _Result()
        if normalized == "SHOW transaction_read_only":
            return _Result(row={"transaction_read_only": self.read_only})
        if "FROM schema_migrations" in normalized:
            return _Result(
                rows=[
                    {"version": version, "checksum": f"checksum:{version}"}
                    for version in sorted(self.applied_versions)
                ]
            )
        table = re.search(r" FROM (dpm_[a-z0-9_]+) ", f" {normalized} ")
        assert table is not None, normalized
        dataset_rows = self.rows.get(table.group(1), [])
        if normalized.startswith("SELECT COUNT(*)"):
            return _Result(row={"total_count": len(dataset_rows)})
        assert params is not None
        return _Result(rows=dataset_rows[: int(params[0])])

    def rollback(self) -> None:
        self.rollback_count += 1


def test_registry_matches_every_final_nullable_tenant_dataset() -> None:
    migrations = Path("src/infrastructure/postgres_migrations/dpm")
    nullable_tables: set[str] = set()
    not_null_tables: set[str] = set()
    for path in sorted(migrations.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        for table, definition in re.findall(
            r"CREATE TABLE IF NOT EXISTS\s+(dpm_[a-z0-9_]+)\s*\((.*?)\);",
            sql,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            tenant_column = re.search(r"tenant_id\s+TEXT([^,\n]*)", definition, re.IGNORECASE)
            if tenant_column and "NOT NULL" not in tenant_column.group(1).upper():
                nullable_tables.add(table)
        nullable_tables.update(
            re.findall(
                r"ALTER TABLE\s+(dpm_[a-z0-9_]+).*?"
                r"ADD COLUMN IF NOT EXISTS tenant_id\s+TEXT(?:\s+NULL)?\s*;",
                sql,
                flags=re.DOTALL | re.IGNORECASE,
            )
        )
        not_null_tables.update(
            re.findall(
                r"ALTER TABLE\s+(dpm_[a-z0-9_]+)\s+ALTER COLUMN tenant_id SET NOT NULL",
                sql,
                flags=re.IGNORECASE,
            )
        )

    final_nullable_tables = nullable_tables - not_null_tables
    assert {dataset.name for dataset in QUARANTINED_TENANT_DATASETS} == final_nullable_tables
    assert len(QUARANTINED_TENANT_DATASETS) == 7


def test_monitoring_run_inventory_requires_its_bounded_scan_index() -> None:
    migration = Path(
        "src/infrastructure/postgres_migrations/dpm/0029_monitoring_run_quarantine_inventory.sql"
    ).read_text(encoding="utf-8")

    assert "idx_dpm_monitoring_runs_null_tenant_inventory" in migration
    assert "ON dpm_monitoring_runs (monitoring_run_id)" in migration
    assert "WHERE tenant_id IS NULL" in migration
    monitoring_runs = next(
        dataset for dataset in QUARANTINED_TENANT_DATASETS if dataset.name == "dpm_monitoring_runs"
    )
    assert monitoring_runs.migration_version == "0029"


def test_clean_estate_is_an_explicit_successful_zero_read_only_report() -> None:
    connection = _Connection()

    report = build_quarantined_tenant_inventory(connection=connection, limit=20)

    assert report["status"] == "success"
    assert report["readOnly"] is True
    assert report["totalQuarantinedRows"] == 0
    assert len(report["datasets"]) == 7
    assert all(dataset["totalCount"] == 0 for dataset in report["datasets"])
    assert all(dataset["rows"] == [] for dataset in report["datasets"])
    assert all(dataset["truncated"] is False for dataset in report["datasets"])
    assert connection.statements[0] == "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert connection.rollback_count == 1
    assert not any(
        re.match(r"^(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE)\b", statement)
        for statement in connection.statements
    )


def test_inventory_is_bounded_stable_and_hashes_caller_idempotency_keys() -> None:
    connection = _Connection(
        rows={
            "dpm_rebalance_wave_idempotency": [
                {
                    "idempotency_key": "caller-secret-key-1",
                    "wave_id": "wave-1",
                    "created_at": "2026-09-09T00:00:00+00:00",
                },
                {
                    "idempotency_key": "caller-secret-key-2",
                    "wave_id": "wave-2",
                    "created_at": "2026-09-09T00:01:00+00:00",
                },
            ]
        }
    )

    report = build_quarantined_tenant_inventory(connection=connection, limit=1)

    dataset = next(
        item for item in report["datasets"] if item["dataset"] == "dpm_rebalance_wave_idempotency"
    )
    assert dataset["totalCount"] == 2
    assert dataset["returnedCount"] == 1
    assert dataset["truncated"] is True
    assert dataset["rows"] == [
        {
            "idempotency_keySha256": (
                "0fd39fd4ea576370872afdec5b8cc0e87bba36f68097d8702ab17e19509a99d5"
            ),
            "wave_id": "wave-1",
            "created_at": "2026-09-09T00:00:00+00:00",
        }
    ]
    assert "caller-secret-key" not in str(report)


def test_missing_schema_provenance_is_failure_and_still_rolls_back() -> None:
    connection = _Connection(applied_versions={"dpm:0003"})

    with pytest.raises(
        RuntimeError,
        match="QUARANTINE_INVENTORY_MIGRATION_NOT_APPLIED:dpm:0024",
    ):
        build_quarantined_tenant_inventory(connection=connection, limit=20)

    assert connection.rollback_count == 1


def test_registry_rejects_unsafe_or_inconsistent_definitions() -> None:
    with pytest.raises(ValueError, match="QUARANTINE_INVENTORY_UNSAFE_REGISTRY_IDENTIFIER"):
        QuarantinedTenantDataset(
            name="unsafe; DROP TABLE evidence",
            migration_version="9999",
            migration_path="unsafe.sql",
            identifying_columns=("id",),
        )
    with pytest.raises(ValueError, match="QUARANTINE_INVENTORY_INVALID_HASHED_COLUMN"):
        QuarantinedTenantDataset(
            name="safe_table",
            migration_version="9999",
            migration_path="safe.sql",
            identifying_columns=("id",),
            hashed_columns=frozenset({"not_selected"}),
        )


def test_database_must_confirm_the_transaction_is_read_only() -> None:
    connection = _Connection(read_only="off")

    with pytest.raises(RuntimeError, match="QUARANTINE_INVENTORY_TRANSACTION_NOT_READ_ONLY"):
        build_quarantined_tenant_inventory(connection=connection, limit=20)

    assert connection.rollback_count == 1


def test_row_factory_and_scalar_serialization_fail_closed() -> None:
    assert _row_value({"value": "found"}, "value") == "found"
    assert _row_value(_StringRow(), "value") == "indexed"
    with pytest.raises(RuntimeError, match="QUARANTINE_INVENTORY_ROW_FACTORY_REQUIRED"):
        _row_value(("positional",), "value")
    assert _json_scalar(date(2026, 9, 9)) == "2026-09-09"
    assert _json_scalar(Path("safe-value")) == "safe-value"


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_is_strictly_bounded(limit: int) -> None:
    connection = _Connection()

    with pytest.raises(ValueError, match="QUARANTINE_INVENTORY_LIMIT_OUT_OF_RANGE"):
        build_quarantined_tenant_inventory(connection=connection, limit=limit)

    assert connection.statements == []
