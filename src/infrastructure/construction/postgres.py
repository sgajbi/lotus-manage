from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresConstructionRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_CONSTRUCTION_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_CONSTRUCTION_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_alternative_set(
        self,
        *,
        alternative_set: ConstructionAlternativeSet,
        idempotency_key: str,
    ) -> None:
        query = """
            INSERT INTO dpm_construction_alternative_sets (
                alternative_set_id,
                portfolio_id,
                as_of,
                status,
                request_hash,
                idempotency_key,
                input_mode,
                source_supportability_state,
                payload_json,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alternative_set_id) DO UPDATE SET
                status=excluded.status,
                request_hash=excluded.request_hash,
                idempotency_key=excluded.idempotency_key,
                input_mode=excluded.input_mode,
                source_supportability_state=excluded.source_supportability_state,
                payload_json=excluded.payload_json,
                created_at=excluded.created_at
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    alternative_set.alternative_set_id,
                    alternative_set.portfolio_id,
                    alternative_set.as_of,
                    alternative_set.status.value,
                    alternative_set.request_hash,
                    idempotency_key,
                    alternative_set.input_mode,
                    alternative_set.source_supportability_state,
                    dump_model_json(alternative_set),
                    alternative_set.generated_at.isoformat(),
                ),
            )
            connection.commit()

    def get_alternative_set(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSet | None:
        query = "SELECT payload_json FROM dpm_construction_alternative_sets WHERE alternative_set_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (alternative_set_id,)).fetchone()
        return _alternative_set_from_row(row)

    def get_alternative_set_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> ConstructionAlternativeSet | None:
        query = """
            SELECT payload_json
            FROM dpm_construction_alternative_sets
            WHERE idempotency_key = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        return _alternative_set_from_row(row)

    def save_selection(
        self,
        *,
        selection: ConstructionAlternativeSelection,
    ) -> None:
        query = """
            INSERT INTO dpm_construction_alternative_selections (
                selection_id,
                alternative_set_id,
                alternative_id,
                actor_id,
                reason_code,
                comment,
                correlation_id,
                payload_json,
                selected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alternative_set_id) DO UPDATE SET
                selection_id=excluded.selection_id,
                alternative_id=excluded.alternative_id,
                actor_id=excluded.actor_id,
                reason_code=excluded.reason_code,
                comment=excluded.comment,
                correlation_id=excluded.correlation_id,
                payload_json=excluded.payload_json,
                selected_at=excluded.selected_at
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    selection.selection_id,
                    selection.alternative_set_id,
                    selection.alternative_id,
                    selection.actor_id,
                    selection.reason_code,
                    selection.comment,
                    selection.correlation_id,
                    dump_model_json(selection),
                    selection.selected_at.isoformat(),
                ),
            )
            connection.commit()

    def get_selection(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSelection | None:
        query = """
            SELECT payload_json
            FROM dpm_construction_alternative_selections
            WHERE alternative_set_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (alternative_set_id,)).fetchone()
        if row is None:
            return None
        return load_model_json(ConstructionAlternativeSelection, _payload(row))

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _alternative_set_from_row(row: Any) -> ConstructionAlternativeSet | None:
    if row is None:
        return None
    return load_model_json(ConstructionAlternativeSet, _payload(row))


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
