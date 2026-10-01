"""PostgreSQL storage for immutable approved-instruction package records."""

from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.instruction_packages import (
    DpmApprovedInstructionPackage,
    DpmInstructionPackageConflictError,
    DpmInstructionPackageReceipt,
    DpmInstructionPackageRepository,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmInstructionPackageRepository(DpmInstructionPackageRepository):
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_INSTRUCTION_PACKAGE_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_INSTRUCTION_PACKAGE_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_package(self, *, package: DpmApprovedInstructionPackage) -> bool:
        with closing(self._connect()) as connection:
            inserted = connection.execute(
                """
                INSERT INTO dpm_approved_instruction_packages (
                    tenant_id, package_id, package_version, portfolio_id, wave_id, wave_item_id,
                    created_at, content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, package_id, package_version) DO NOTHING
                RETURNING package_id
                """,
                (
                    package.tenant_id,
                    package.package_id,
                    package.package_version,
                    package.portfolio_id,
                    package.wave_id,
                    package.wave_item_id,
                    package.created_at,
                    package.content_hash,
                    dump_model_json(package),
                ),
            ).fetchone()
            if inserted is not None:
                connection.commit()
                return True
            existing = connection.execute(
                """
                SELECT content_hash FROM dpm_approved_instruction_packages
                WHERE tenant_id = %s AND package_id = %s AND package_version = %s
                """,
                (package.tenant_id, package.package_id, package.package_version),
            ).fetchone()
            connection.rollback()
        if existing is None or existing["content_hash"] != package.content_hash:
            raise DpmInstructionPackageConflictError("INSTRUCTION_PACKAGE_IMMUTABLE_CONFLICT")
        return False

    def get_package(
        self, *, tenant_id: str, package_id: str, package_version: str
    ) -> DpmApprovedInstructionPackage | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM dpm_approved_instruction_packages
                WHERE tenant_id = %s AND package_id = %s AND package_version = %s
                """,
                (tenant_id, package_id, package_version),
            ).fetchone()
        return _load_package(row) if row is not None else None

    def list_packages(
        self,
        *,
        tenant_id: str,
        created_before: datetime,
        limit: int,
        offset: int,
    ) -> tuple[list[DpmApprovedInstructionPackage], int]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_approved_instruction_packages
                WHERE tenant_id = %s AND created_at <= %s
                ORDER BY created_at DESC, package_id DESC, package_version DESC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, created_before, limit, offset),
            ).fetchall()
            count_row = connection.execute(
                """
                SELECT count(*) AS total_count FROM dpm_approved_instruction_packages
                WHERE tenant_id = %s AND created_at <= %s
                """,
                (tenant_id, created_before),
            ).fetchone()
        return [_load_package(row) for row in rows], int(count_row["total_count"])

    def get_package_by_wave_item(
        self, *, tenant_id: str, wave_id: str, wave_item_id: str
    ) -> list[DpmApprovedInstructionPackage]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_approved_instruction_packages
                WHERE tenant_id = %s AND wave_id = %s AND wave_item_id = %s
                ORDER BY created_at DESC, package_id DESC, package_version DESC
                """,
                (tenant_id, wave_id, wave_item_id),
            ).fetchall()
        return [_load_package(row) for row in rows]

    def save_receipt(self, *, receipt: DpmInstructionPackageReceipt) -> bool:
        with closing(self._connect()) as connection:
            inserted = connection.execute(
                """
                INSERT INTO dpm_approved_instruction_package_receipts (
                    tenant_id, package_id, package_version, consumer_id, receipt_id,
                    receipt_evidence_hash, received_at, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, package_id, package_version, consumer_id) DO NOTHING
                RETURNING receipt_id
                """,
                (
                    receipt.tenant_id,
                    receipt.package_id,
                    receipt.package_version,
                    receipt.consumer_id,
                    receipt.receipt_id,
                    receipt.receipt_evidence_hash,
                    receipt.received_at,
                    dump_model_json(receipt),
                ),
            ).fetchone()
            if inserted is not None:
                connection.commit()
                return True
            existing = connection.execute(
                """
                SELECT receipt_evidence_hash FROM dpm_approved_instruction_package_receipts
                WHERE tenant_id = %s AND package_id = %s AND package_version = %s
                  AND consumer_id = %s
                """,
                (
                    receipt.tenant_id,
                    receipt.package_id,
                    receipt.package_version,
                    receipt.consumer_id,
                ),
            ).fetchone()
            connection.rollback()
        if existing is None or existing["receipt_evidence_hash"] != receipt.receipt_evidence_hash:
            raise DpmInstructionPackageConflictError(
                "INSTRUCTION_PACKAGE_RECEIPT_IMMUTABLE_CONFLICT"
            )
        return False

    def get_receipt(
        self,
        *,
        tenant_id: str,
        package_id: str,
        package_version: str,
        consumer_id: str,
    ) -> DpmInstructionPackageReceipt | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM dpm_approved_instruction_package_receipts
                WHERE tenant_id = %s AND package_id = %s AND package_version = %s
                  AND consumer_id = %s
                """,
                (tenant_id, package_id, package_version, consumer_id),
            ).fetchone()
        return _load_receipt(row) if row is not None else None

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage:instruction-packages",
        )


def _load_package(row: Any) -> DpmApprovedInstructionPackage:
    return load_model_json(DpmApprovedInstructionPackage, _payload(row))


def _load_receipt(row: Any) -> DpmInstructionPackageReceipt:
    return load_model_json(DpmInstructionPackageReceipt, _payload(row))


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["payload_json"]
    if isinstance(payload, (str, dict)):
        return payload
    return json.dumps(payload, default=str)


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


__all__ = ["PostgresDpmInstructionPackageRepository"]
