from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import closing, contextmanager
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import (
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
    require_construction_tenant_id,
)
from src.infrastructure.mandates.serialization import dump_model_json
from src.infrastructure.postgres_access import connect_postgres, connect_postgres_coordination
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresConstructionRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_CONSTRUCTION_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_CONSTRUCTION_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    @contextmanager
    def idempotency_guard(self, *, tenant_id: str, idempotency_key: str) -> Iterator[None]:
        lock_key = _construction_advisory_lock_key(
            tenant_id=require_construction_tenant_id(tenant_id),
            idempotency_key=idempotency_key,
        )
        with closing(self._connect_coordination()) as connection:
            connection.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
            try:
                yield
            finally:
                connection.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))

    def save_alternative_set(
        self,
        *,
        alternative_set: ConstructionAlternativeSet,
        idempotency_key: str,
    ) -> ConstructionAlternativeSet:
        tenant_id = require_construction_tenant_id(alternative_set.tenant_id)
        owned_set = alternative_set.model_copy(update={"tenant_id": tenant_id})
        query = """
            INSERT INTO dpm_construction_alternative_sets (
                alternative_set_id,
                tenant_id,
                portfolio_id,
                as_of,
                status,
                request_hash,
                idempotency_key,
                input_mode,
                source_supportability_state,
                payload_json,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING tenant_id, payload_json
        """
        with closing(self._connect()) as connection:
            row = connection.execute(
                query,
                (
                    owned_set.alternative_set_id,
                    tenant_id,
                    owned_set.portfolio_id,
                    owned_set.as_of,
                    owned_set.status.value,
                    owned_set.request_hash,
                    idempotency_key,
                    owned_set.input_mode,
                    owned_set.source_supportability_state,
                    dump_model_json(owned_set),
                    owned_set.generated_at.isoformat(),
                ),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT tenant_id, payload_json
                    FROM dpm_construction_alternative_sets
                    WHERE tenant_id = %s AND idempotency_key = %s
                    """,
                    (tenant_id, idempotency_key),
                ).fetchone()
            if row is None:
                raise ConstructionIdempotencyConflictError(
                    "CONSTRUCTION_ALTERNATIVE_SET_ID_CONFLICT"
                )
            connection.commit()
        persisted = _alternative_set_from_row(row)
        if persisted is None:
            raise ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")
        return persisted

    def get_alternative_set(
        self,
        *,
        alternative_set_id: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSet | None:
        query = """
            SELECT tenant_id, payload_json
            FROM dpm_construction_alternative_sets
            WHERE alternative_set_id = %s AND tenant_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (alternative_set_id, tenant_id)).fetchone()
        return _alternative_set_from_row(row)

    def get_alternative_set_by_idempotency(
        self,
        *,
        idempotency_key: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSet | None:
        query = """
            SELECT tenant_id, payload_json
            FROM dpm_construction_alternative_sets
            WHERE tenant_id = %s AND idempotency_key = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (tenant_id, idempotency_key)).fetchone()
        return _alternative_set_from_row(row)

    def list_alternative_sets(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
        limit: int,
    ) -> list[ConstructionAlternativeSet]:
        query = """
            SELECT tenant_id, payload_json
            FROM dpm_construction_alternative_sets
            WHERE tenant_id = %s AND portfolio_id = %s
            ORDER BY created_at DESC, alternative_set_id DESC
            LIMIT %s
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (tenant_id, portfolio_id, limit)).fetchall()
        return [
            alternative_set
            for row in rows
            if (alternative_set := _alternative_set_from_row(row)) is not None
        ]

    def save_selection(
        self,
        *,
        selection: ConstructionAlternativeSelection,
    ) -> None:
        tenant_id = require_construction_tenant_id(selection.tenant_id)
        owned_selection = selection.model_copy(update={"tenant_id": tenant_id})
        query = """
            INSERT INTO dpm_construction_alternative_selections (
                selection_id,
                alternative_set_id,
                tenant_id,
                alternative_id,
                actor_id,
                reason_code,
                comment,
                correlation_id,
                payload_json,
                selected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alternative_set_id) DO UPDATE SET
                selection_id=excluded.selection_id,
                alternative_id=excluded.alternative_id,
                actor_id=excluded.actor_id,
                reason_code=excluded.reason_code,
                comment=excluded.comment,
                correlation_id=excluded.correlation_id,
                payload_json=excluded.payload_json,
                selected_at=excluded.selected_at
            WHERE dpm_construction_alternative_selections.tenant_id = excluded.tenant_id
            RETURNING selection_id
        """
        with closing(self._connect()) as connection:
            owner = connection.execute(
                """
                SELECT 1
                FROM dpm_construction_alternative_sets
                WHERE alternative_set_id = %s AND tenant_id = %s
                """,
                (owned_selection.alternative_set_id, tenant_id),
            ).fetchone()
            if owner is None:
                raise ConstructionAlternativeSetNotFoundError(
                    "CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND"
                )
            row = connection.execute(
                query,
                (
                    owned_selection.selection_id,
                    owned_selection.alternative_set_id,
                    tenant_id,
                    owned_selection.alternative_id,
                    owned_selection.actor_id,
                    owned_selection.reason_code,
                    owned_selection.comment,
                    owned_selection.correlation_id,
                    dump_model_json(owned_selection),
                    owned_selection.selected_at.isoformat(),
                ),
            ).fetchone()
            if row is None:
                raise ConstructionAlternativeSetNotFoundError(
                    "CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND"
                )
            connection.commit()

    def get_selection(
        self,
        *,
        alternative_set_id: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSelection | None:
        query = """
            SELECT tenant_id, payload_json
            FROM dpm_construction_alternative_selections
            WHERE alternative_set_id = %s AND tenant_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (alternative_set_id, tenant_id)).fetchone()
        if row is None:
            return None
        return _selection_from_row(row)

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage:construction",
        )

    def _connect_coordination(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres_coordination(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage:construction-coordination",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _alternative_set_from_row(row: Any) -> ConstructionAlternativeSet | None:
    if row is None:
        return None
    return ConstructionAlternativeSet.model_validate(_owned_payload_from_row(row))


def _selection_from_row(row: Any) -> ConstructionAlternativeSelection:
    return ConstructionAlternativeSelection.model_validate(_owned_payload_from_row(row))


def _owned_payload_from_row(row: Any) -> dict[str, Any]:
    payload = _payload(row)
    decoded = dict(payload) if isinstance(payload, dict) else json.loads(payload)
    payload_tenant = decoded.get("tenant_id")
    row_tenant = row["tenant_id"]
    if payload_tenant is not None and payload_tenant != row_tenant:
        raise RuntimeError("DPM_CONSTRUCTION_TENANT_DRIFT")
    decoded["tenant_id"] = row_tenant
    return decoded


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["payload_json"]
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return json.dumps(payload, default=str)
    return payload


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _construction_advisory_lock_key(*, tenant_id: str, idempotency_key: str) -> int:
    digest = hashlib.sha256(f"{tenant_id}\0{idempotency_key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
