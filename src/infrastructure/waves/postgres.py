from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.waves.models import DpmRebalanceWave
from src.core.waves.repository import (
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveVersionConflictError,
    wave_idempotency_mapping_key,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmWaveRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_WAVE_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_WAVE_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
        tenant_id: str,
    ) -> None:
        # Namespaced before storage so two tenants presenting one caller-chosen
        # key hold independent mappings rather than colliding on the primary
        # key (issue #648).
        mapping_key = (
            None
            if idempotency_key is None
            else wave_idempotency_mapping_key(tenant_id=tenant_id, idempotency_key=idempotency_key)
        )
        with closing(self._connect()) as connection:
            _raise_if_idempotency_conflict(
                connection=connection,
                wave=wave,
                idempotency_key=mapping_key,
                request_hash=request_hash,
            )
            # Stamped from the argument so the stored record cannot
            # disagree with the tenant the caller claimed.
            _insert_wave_row(
                connection=connection, wave=wave.model_copy(update={"tenant_id": tenant_id})
            )
            _insert_idempotency_marker(
                connection=connection,
                wave=wave,
                idempotency_key=mapping_key,
                request_hash=request_hash,
                tenant_id=tenant_id,
            )
            _insert_new_events(connection=connection, wave=wave)
            connection.commit()

    def get_wave(self, *, wave_id: str, tenant_id: str) -> DpmRebalanceWave | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT wave_json
                FROM dpm_rebalance_waves
                WHERE wave_id = %s
                  AND tenant_id = %s
                """,
                (wave_id, tenant_id),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmRebalanceWave, _payload(row))

    def get_wave_by_idempotency(
        self, *, idempotency_key: str, tenant_id: str
    ) -> DpmRebalanceWave | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT w.wave_json
                FROM dpm_rebalance_wave_idempotency i
                JOIN dpm_rebalance_waves w ON w.wave_id = i.wave_id
                WHERE i.idempotency_key = %s
                  AND i.tenant_id = %s
                  -- The aggregate's own owner, not only the mapping's. A wave
                  -- left unstamped by migration 0027 has w.tenant_id NULL, and
                  -- `NULL = 'anything'` is NULL rather than true, so it is
                  -- matched by no caller - the same quarantine every direct
                  -- read gets. Without this the replay path returned it.
                  AND w.tenant_id = %s
                """,
                (
                    wave_idempotency_mapping_key(
                        tenant_id=tenant_id, idempotency_key=idempotency_key
                    ),
                    tenant_id,
                    tenant_id,
                ),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmRebalanceWave, _payload(row))

    def list_waves(
        self,
        *,
        tenant_id: str,
        state: str | None = None,
        trigger_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmRebalanceWave]:
        # Seeded rather than appended conditionally: the tenant predicate is not
        # one of the optional filters and must never be absent (issue #677).
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
        if state is not None:
            clauses.append("state = %s")
            args.append(state)
        if trigger_type is not None:
            clauses.append("trigger_type = %s")
            args.append(trigger_type)
        if as_of_date is not None:
            clauses.append("as_of_date = %s")
            args.append(as_of_date)
        where_clause = f"WHERE {' AND '.join(clauses)}"
        args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT wave_json
                FROM dpm_rebalance_waves
                {where_clause}
                ORDER BY created_at DESC, wave_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmRebalanceWave, _payload(row)) for row in rows]

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int, tenant_id: str) -> None:
        # The tenant rides in the UPDATE predicate rather than a prior SELECT:
        # a check-then-write leaves a window, and this is the write half of the
        # transition path. A foreign wave matches no row and raises the same
        # version-conflict error as a stale version - indistinguishable on
        # purpose, so a caller cannot probe for wave ids it does not own.
        stamped = wave.model_copy(update={"tenant_id": tenant_id})
        with closing(self._connect()) as connection:
            result = connection.execute(
                """
                UPDATE dpm_rebalance_waves
                SET state = %s,
                    version = %s,
                    wave_json = %s,
                    retention_policy = %s
                WHERE wave_id = %s
                AND version = %s
                AND tenant_id = %s
                """,
                (
                    stamped.state,
                    stamped.version,
                    dump_model_json(stamped),
                    stamped.retention_policy,
                    stamped.wave_id,
                    expected_version,
                    tenant_id,
                ),
            )
            if result.rowcount != 1:
                raise DpmWaveVersionConflictError("DPM_WAVE_VERSION_CONFLICT")
            _insert_new_events(connection=connection, wave=stamped)
            connection.commit()

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage:waves",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _wave_row_args(wave: DpmRebalanceWave) -> tuple[Any, ...]:
    return (
        wave.wave_id,
        wave.state,
        wave.trigger.trigger_type,
        wave.as_of_date,
        wave.created_at,
        wave.created_by,
        wave.correlation_id,
        wave.version,
        dump_model_json(wave),
        wave.retention_policy,
        # Persisted as its own column, not only inside wave_json, so the fence
        # is an indexable predicate rather than a JSON extraction (issue #677).
        wave.tenant_id,
    )


def _raise_if_idempotency_conflict(
    *,
    connection: Any,
    wave: DpmRebalanceWave,
    idempotency_key: str | None,
    request_hash: str | None,
) -> None:
    if idempotency_key is None:
        return
    existing = connection.execute(
        """
        SELECT wave_id, request_hash
        FROM dpm_rebalance_wave_idempotency
        WHERE idempotency_key = %s
        """,
        (idempotency_key,),
    ).fetchone()
    if existing is not None and (
        existing["wave_id"] != wave.wave_id or existing["request_hash"] != request_hash
    ):
        raise DpmWaveIdempotencyConflictError("DPM_WAVE_IDEMPOTENCY_CONFLICT")


def _insert_wave_row(*, connection: Any, wave: DpmRebalanceWave) -> None:
    result = connection.execute(
        """
        INSERT INTO dpm_rebalance_waves (
            wave_id,
            state,
            trigger_type,
            as_of_date,
            created_at,
            created_by,
            correlation_id,
            version,
            wave_json,
            retention_policy,
            tenant_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (wave_id) DO NOTHING
        """,
        _wave_row_args(wave),
    )
    if result.rowcount != 1:
        raise DpmWaveAlreadyExistsError("DPM_WAVE_ALREADY_EXISTS")


def _insert_idempotency_marker(
    *,
    connection: Any,
    wave: DpmRebalanceWave,
    idempotency_key: str | None,
    request_hash: str | None,
    tenant_id: str,
) -> None:
    if idempotency_key is None:
        return
    connection.execute(
        """
        INSERT INTO dpm_rebalance_wave_idempotency (
            idempotency_key,
            wave_id,
            request_hash,
            created_at,
            tenant_id
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO NOTHING
        """,
        (
            idempotency_key,
            wave.wave_id,
            request_hash,
            datetime.now(timezone.utc),
            tenant_id,
        ),
    )


def _insert_new_events(*, connection: Any, wave: DpmRebalanceWave) -> None:
    for event in wave.events:
        connection.execute(
            """
            INSERT INTO dpm_rebalance_wave_events (
                event_id,
                wave_id,
                from_state,
                to_state,
                event_type,
                actor_id,
                reason_code,
                correlation_id,
                created_at,
                event_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
            """,
            (
                event.event_id,
                event.wave_id,
                event.from_state,
                event.to_state,
                event.event_type,
                event.actor_id,
                event.reason_code,
                event.correlation_id,
                event.created_at,
                dump_model_json(event),
            ),
        )


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["wave_json"]
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return json.dumps(payload, default=str)
    return payload


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
