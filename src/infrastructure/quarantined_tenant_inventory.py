"""Read-only inventory of rows retained without verified tenant attribution."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


_SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
INVENTORY_SCHEMA_VERSION = "lotus-manage.quarantined-tenant-inventory.v1"


@dataclass(frozen=True)
class QuarantinedTenantDataset:
    """One database dataset whose NULL tenant rows remain fail-closed."""

    name: str
    migration_version: str
    migration_path: str
    identifying_columns: tuple[str, ...]
    hashed_columns: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        identifiers = (self.name, *self.identifying_columns)
        if not self.identifying_columns or any(
            _SAFE_IDENTIFIER.fullmatch(identifier) is None for identifier in identifiers
        ):
            raise ValueError("QUARANTINE_INVENTORY_UNSAFE_REGISTRY_IDENTIFIER")
        if not self.hashed_columns <= set(self.identifying_columns):
            raise ValueError("QUARANTINE_INVENTORY_INVALID_HASHED_COLUMN")


QUARANTINED_TENANT_DATASETS = (
    QuarantinedTenantDataset(
        name="dpm_mandate_snapshots",
        migration_version="0024",
        migration_path="src/infrastructure/postgres_migrations/dpm/0024_mandate_tenant_scope.sql",
        identifying_columns=(
            "mandate_snapshot_id",
            "mandate_id",
            "portfolio_id",
            "mandate_version",
            "as_of_date",
            "created_at",
        ),
    ),
    QuarantinedTenantDataset(
        name="dpm_mandate_health_snapshots",
        migration_version="0024",
        migration_path="src/infrastructure/postgres_migrations/dpm/0024_mandate_tenant_scope.sql",
        identifying_columns=(
            "health_snapshot_id",
            "mandate_id",
            "portfolio_id",
            "as_of_date",
            "created_at",
        ),
    ),
    QuarantinedTenantDataset(
        name="dpm_monitoring_exceptions",
        migration_version="0025",
        migration_path=(
            "src/infrastructure/postgres_migrations/dpm/0025_monitoring_exception_tenant_scope.sql"
        ),
        identifying_columns=(
            "exception_id",
            "monitoring_run_id",
            "mandate_id",
            "portfolio_id",
            "as_of_date",
            "detected_at",
        ),
    ),
    QuarantinedTenantDataset(
        name="dpm_rebalance_wave_idempotency",
        migration_version="0026",
        migration_path=(
            "src/infrastructure/postgres_migrations/dpm/0026_wave_idempotency_tenant_scope.sql"
        ),
        identifying_columns=("idempotency_key", "wave_id", "created_at"),
        hashed_columns=frozenset({"idempotency_key"}),
    ),
    QuarantinedTenantDataset(
        name="dpm_rebalance_waves",
        migration_version="0027",
        migration_path="src/infrastructure/postgres_migrations/dpm/0027_wave_tenant_scope.sql",
        identifying_columns=("wave_id", "as_of_date", "created_at"),
    ),
    QuarantinedTenantDataset(
        name="dpm_pre_trade_proof_packs",
        migration_version="0028",
        migration_path=(
            "src/infrastructure/postgres_migrations/dpm/0028_proof_pack_tenant_scope.sql"
        ),
        identifying_columns=(
            "proof_pack_id",
            "portfolio_id",
            "mandate_id",
            "source_type",
            "status",
            "created_at",
        ),
    ),
    QuarantinedTenantDataset(
        name="dpm_monitoring_runs",
        migration_version="0029",
        migration_path=(
            "src/infrastructure/postgres_migrations/dpm/"
            "0029_monitoring_run_quarantine_inventory.sql"
        ),
        identifying_columns=("monitoring_run_id", "as_of_date", "status", "started_at"),
    ),
)


def build_quarantined_tenant_inventory(*, connection: Any, limit: int) -> dict[str, Any]:
    """Return a consistent bounded inventory and always roll back the read-only transaction."""

    if limit < 1 or limit > 100:
        raise ValueError("QUARANTINE_INVENTORY_LIMIT_OUT_OF_RANGE")

    connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    try:
        read_only_row = connection.execute("SHOW transaction_read_only").fetchone()
        if str(_row_value(read_only_row, "transaction_read_only")).lower() != "on":
            raise RuntimeError("QUARANTINE_INVENTORY_TRANSACTION_NOT_READ_ONLY")

        migration_checksums = _load_migration_checksums(connection)
        datasets = [
            _inventory_dataset(
                connection=connection,
                dataset=dataset,
                limit=limit,
                migration_checksums=migration_checksums,
            )
            for dataset in QUARANTINED_TENANT_DATASETS
        ]
        return {
            "schemaVersion": INVENTORY_SCHEMA_VERSION,
            "status": "success",
            "readOnly": True,
            "limitPerDataset": limit,
            "totalQuarantinedRows": sum(item["totalCount"] for item in datasets),
            "datasets": datasets,
        }
    finally:
        connection.rollback()


def _load_migration_checksums(connection: Any) -> dict[str, str]:
    rows = connection.execute(
        """
        SELECT version, checksum
        FROM schema_migrations
        WHERE namespace = %s
        ORDER BY version ASC
        """,
        ("dpm",),
    ).fetchall()
    return {str(_row_value(row, "version")): str(_row_value(row, "checksum")) for row in rows}


def _inventory_dataset(
    *,
    connection: Any,
    dataset: QuarantinedTenantDataset,
    limit: int,
    migration_checksums: dict[str, str],
) -> dict[str, Any]:
    stored_version = f"dpm:{dataset.migration_version}"
    checksum = migration_checksums.get(stored_version) or migration_checksums.get(
        dataset.migration_version
    )
    if checksum is None:
        raise RuntimeError(f"QUARANTINE_INVENTORY_MIGRATION_NOT_APPLIED:{stored_version}")

    count_row = connection.execute(
        f"SELECT COUNT(*) AS total_count FROM {dataset.name} WHERE tenant_id IS NULL"
    ).fetchone()
    total_count = int(_row_value(count_row, "total_count"))
    columns = ", ".join(dataset.identifying_columns)
    detail_rows = connection.execute(
        f"SELECT {columns} FROM {dataset.name} "
        f"WHERE tenant_id IS NULL ORDER BY {dataset.identifying_columns[0]} ASC LIMIT %s",
        (limit,),
    ).fetchall()
    rows = [_safe_detail_row(row=row, dataset=dataset) for row in detail_rows]
    return {
        "dataset": dataset.name,
        "migration": {
            "namespace": "dpm",
            "version": dataset.migration_version,
            "storedVersion": stored_version,
            "path": dataset.migration_path,
            "checksum": checksum,
        },
        "totalCount": total_count,
        "returnedCount": len(rows),
        "truncated": total_count > len(rows),
        "rows": rows,
    }


def _safe_detail_row(
    *, row: Any, dataset: QuarantinedTenantDataset
) -> dict[str, str | int | float | bool | None]:
    detail: dict[str, str | int | float | bool | None] = {}
    for column in dataset.identifying_columns:
        value = _row_value(row, column)
        if column in dataset.hashed_columns:
            detail[f"{column}Sha256"] = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        else:
            detail[column] = _json_scalar(value)
    return detail


def _row_value(row: Any, column: str) -> Any:
    if isinstance(row, dict):
        return row[column]
    try:
        return row[column]
    except (KeyError, TypeError):
        raise RuntimeError("QUARANTINE_INVENTORY_ROW_FACTORY_REQUIRED") from None


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)
