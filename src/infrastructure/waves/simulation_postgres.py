"""PostgreSQL persistence and fencing for asynchronous wave simulation."""

from __future__ import annotations

import json
import uuid
from contextlib import closing
from datetime import datetime
from typing import Any, cast

from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemClaim,
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
    WaveSimulationItemStatus,
    WaveSimulationOperationStatus,
    derive_wave_simulation_operation_status_from_counts,
)
from src.core.waves.simulation_repository import DpmWaveSimulationOperationConflictError
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.waves.simulation_publication import DpmWaveSimulationPublicationMixin


class PostgresDpmWaveSimulationMixin(DpmWaveSimulationPublicationMixin):
    """Mixin requiring the host repository's ``_connect`` method."""

    def admit_simulation_operation(
        self,
        *,
        operation: DpmWaveSimulationOperation,
        items: list[DpmWaveSimulationItemRecord],
        simulating_wave: DpmRebalanceWave,
    ) -> tuple[DpmWaveSimulationOperation, bool]:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            wave_row = connection.execute(
                """
                SELECT wave_json, version
                FROM dpm_rebalance_waves
                WHERE wave_id = %s AND tenant_id = %s
                FOR UPDATE
                """,
                (operation.wave_id, operation.tenant_id),
            ).fetchone()
            if wave_row is None:
                raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_WAVE_NOT_FOUND")
            existing = _select_operation_by_idempotency(
                connection=connection,
                tenant_id=operation.tenant_id,
                idempotency_key_hash=operation.idempotency_key_hash,
            )
            if existing is not None:
                if existing.request_hash != operation.request_hash:
                    raise DpmWaveSimulationOperationConflictError(
                        "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT"
                    )
                connection.rollback()
                return existing, True
            if int(wave_row["version"]) != operation.admitted_wave_version:
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT"
                )
            wave = load_model_json(DpmRebalanceWave, wave_row["wave_json"])
            _validate_admission_items(operation=operation, items=items, wave=wave)
            if (
                simulating_wave.wave_id != wave.wave_id
                or simulating_wave.tenant_id != operation.tenant_id
                or simulating_wave.state != "SIMULATING"
                or simulating_wave.version != wave.version + 1
            ):
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_TRANSITION_CONFLICT"
                )
            if (
                _select_operation_by_correlation(
                    connection=connection,
                    tenant_id=operation.tenant_id,
                    correlation_id=operation.correlation_id,
                )
                is not None
            ):
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_CORRELATION_CONFLICT"
                )
            try:
                _insert_operation(connection=connection, operation=operation)
                for item in items:
                    _insert_item(connection=connection, item=item)
                _update_wave_to_simulating(connection=connection, wave=simulating_wave)
                connection.commit()
            except Exception as exc:
                connection.rollback()
                constraint = _constraint_name(exc)
                if constraint and "idempotency_key_hash" in constraint:
                    raise DpmWaveSimulationOperationConflictError(
                        "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT"
                    ) from exc
                if constraint and "correlation" in constraint:
                    raise DpmWaveSimulationOperationConflictError(
                        "DPM_WAVE_SIMULATION_CORRELATION_CONFLICT"
                    ) from exc
                raise
        return operation, False

    def get_simulation_operation(
        self, *, tenant_id: str, operation_id: str
    ) -> DpmWaveSimulationOperation | None:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            row = connection.execute(
                """
                SELECT * FROM dpm_wave_simulation_operations
                WHERE tenant_id = %s AND operation_id = %s
                """,
                (tenant_id, operation_id),
            ).fetchone()
        return None if row is None else _operation_from_row(row)

    def get_simulation_operation_by_idempotency(
        self, *, tenant_id: str, idempotency_key_hash: str
    ) -> DpmWaveSimulationOperation | None:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            return _select_operation_by_idempotency(
                connection=connection,
                tenant_id=tenant_id,
                idempotency_key_hash=idempotency_key_hash,
            )

    def list_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        limit: int,
        offset: int,
    ) -> DpmWaveSimulationItemPage:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total_count
                FROM dpm_wave_simulation_items i
                JOIN dpm_wave_simulation_operations o USING (operation_id)
                WHERE i.tenant_id = %s
                  AND o.tenant_id = %s
                  AND i.operation_id = %s
                """,
                (tenant_id, tenant_id, operation_id),
            ).fetchone()
            total_count = 0 if count_row is None else int(count_row["total_count"])
            rows = connection.execute(
                """
                SELECT i.*
                FROM dpm_wave_simulation_items i
                JOIN dpm_wave_simulation_operations o USING (operation_id)
                WHERE i.tenant_id = %s
                  AND o.tenant_id = %s
                  AND i.operation_id = %s
                ORDER BY i.ordinal ASC, i.wave_item_id ASC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, tenant_id, operation_id, limit, offset),
            ).fetchall()
        items = [_item_from_row(row) for row in rows]
        next_offset = offset + len(items) if offset + len(items) < total_count else None
        return DpmWaveSimulationItemPage(
            items=items,
            total_count=total_count,
            next_offset=next_offset,
        )

    def simulation_item_counts(self, *, tenant_id: str, operation_id: str) -> dict[str, int]:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            row = connection.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE i.status = 'PENDING') AS pending_count,
                    COUNT(*) FILTER (WHERE i.status = 'RUNNING') AS running_count,
                    COUNT(*) FILTER (WHERE i.status = 'SUCCEEDED') AS succeeded_count,
                    COUNT(*) FILTER (WHERE i.status = 'FAILED') AS failed_count,
                    COUNT(*) FILTER (WHERE i.status = 'CANCELLED') AS cancelled_count
                FROM dpm_wave_simulation_items i
                JOIN dpm_wave_simulation_operations o USING (operation_id)
                WHERE i.tenant_id = %s
                  AND o.tenant_id = %s
                  AND i.operation_id = %s
                """,
                (tenant_id, tenant_id, operation_id),
            ).fetchone()
        if row is None:
            return {}
        return {
            "PENDING": int(row["pending_count"]),
            "RUNNING": int(row["running_count"]),
            "SUCCEEDED": int(row["succeeded_count"]),
            "FAILED": int(row["failed_count"]),
            "CANCELLED": int(row["cancelled_count"]),
        }

    def claim_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        worker_id: str,
        limit: int,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> list[DpmWaveSimulationItemClaim]:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            operation_row = connection.execute(
                """
                SELECT * FROM dpm_wave_simulation_operations
                WHERE tenant_id = %s AND operation_id = %s
                FOR UPDATE
                """,
                (tenant_id, operation_id),
            ).fetchone()
            if operation_row is None:
                return []
            operation = _operation_from_row(operation_row)
            if operation.status in {"CANCEL_REQUESTED", "CANCELLED", "SUCCEEDED", "FAILED"}:
                connection.rollback()
                return []
            active_row = connection.execute(
                """
                SELECT COUNT(*) AS active_count
                FROM dpm_wave_simulation_items
                WHERE tenant_id = %s AND operation_id = %s
                  AND status = 'RUNNING'
                  AND lease_expires_at > %s
                """,
                (tenant_id, operation_id, claimed_at),
            ).fetchone()
            active_count = 0 if active_row is None else int(active_row["active_count"])
            claim_limit = min(max(0, limit), max(0, operation.max_concurrency - active_count))
            candidate_rows = connection.execute(
                """
                SELECT *
                FROM dpm_wave_simulation_items
                WHERE tenant_id = %s
                  AND operation_id = %s
                  AND (
                      status = 'PENDING'
                      OR (status = 'RUNNING' AND lease_expires_at <= %s)
                  )
                ORDER BY ordinal ASC, wave_item_id ASC
                LIMIT %s
                FOR UPDATE
                """,
                (tenant_id, operation_id, claimed_at, claim_limit),
            ).fetchall()
            candidates = [_item_from_row(row) for row in candidate_rows]
            claims = [
                _claim_item(
                    connection=connection,
                    operation=operation,
                    item=item,
                    worker_id=worker_id,
                    claimed_at=claimed_at,
                    lease_expires_at=lease_expires_at,
                )
                for item in candidates
            ]
            _refresh_operation_status(
                connection=connection, operation=operation, updated_at=claimed_at
            )
            connection.commit()
            return claims

    def retry_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        wave_item_ids: list[str] | None,
        retried_at: datetime,
    ) -> int:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            operation_row = connection.execute(
                """
                SELECT * FROM dpm_wave_simulation_operations
                WHERE tenant_id = %s AND operation_id = %s
                FOR UPDATE
                """,
                (tenant_id, operation_id),
            ).fetchone()
            if operation_row is None:
                return 0
            operation = _operation_from_row(operation_row)
            if operation.cancel_reason_code is not None:
                connection.rollback()
                return 0
            args: list[object] = [retried_at, tenant_id, operation_id, operation.max_attempts]
            item_filter = ""
            if wave_item_ids is not None:
                item_filter = " AND wave_item_id = ANY(%s)"
                args.append(wave_item_ids)
            result = connection.execute(
                f"""
                UPDATE dpm_wave_simulation_items
                SET status = 'PENDING',
                    worker_id = NULL,
                    claim_token = NULL,
                    claimed_at = NULL,
                    lease_expires_at = NULL,
                    error_code = NULL,
                    error_message = NULL,
                    retryable = FALSE,
                    completed_at = NULL,
                    updated_at = %s
                WHERE tenant_id = %s
                  AND operation_id = %s
                  AND status = 'FAILED'
                  AND retryable = TRUE
                  AND attempt_count < %s
                  {item_filter}
                """,
                tuple(args),
            )
            _refresh_operation_status(
                connection=connection, operation=operation, updated_at=retried_at
            )
            connection.commit()
            return int(result.rowcount)

    def cancel_simulation_operation(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        reason_code: str,
        cancelled_at: datetime,
    ) -> DpmWaveSimulationOperation | None:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            operation_row = connection.execute(
                """
                SELECT * FROM dpm_wave_simulation_operations
                WHERE tenant_id = %s AND operation_id = %s
                FOR UPDATE
                """,
                (tenant_id, operation_id),
            ).fetchone()
            if operation_row is None:
                return None
            operation = _operation_from_row(operation_row)
            if operation.cancel_reason_code is not None or operation.status in {
                "SUCCEEDED",
                "FAILED",
                "CANCELLED",
            }:
                connection.rollback()
                return operation
            connection.execute(
                """
                UPDATE dpm_wave_simulation_operations
                SET cancel_reason_code = %s, updated_at = %s
                WHERE tenant_id = %s AND operation_id = %s
                """,
                (reason_code, cancelled_at, tenant_id, operation_id),
            )
            connection.execute(
                """
                UPDATE dpm_wave_simulation_items
                SET status = 'CANCELLED', retryable = FALSE,
                    completed_at = %s, updated_at = %s
                WHERE tenant_id = %s AND operation_id = %s
                  AND status IN ('PENDING', 'FAILED')
                """,
                (cancelled_at, cancelled_at, tenant_id, operation_id),
            )
            operation = operation.model_copy(
                update={"cancel_reason_code": reason_code, "updated_at": cancelled_at}
            )
            refreshed = _refresh_operation_status(
                connection=connection, operation=operation, updated_at=cancelled_at
            )
            connection.commit()
            return refreshed

    def _publish_simulation_item_terminal(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        completed_at: datetime,
        status: str,
        result_item: DpmRebalanceWaveItem | None,
        error_code: str | None,
        error_message: str | None,
        retryable: bool,
    ) -> bool:
        with closing(self._connect()) as connection:  # type: ignore[attr-defined]
            operation_row = connection.execute(
                """
                SELECT * FROM dpm_wave_simulation_operations
                WHERE tenant_id = %s AND operation_id = %s
                FOR UPDATE
                """,
                (claim.tenant_id, claim.operation_id),
            ).fetchone()
            if operation_row is None:
                return False
            result = connection.execute(
                """
                UPDATE dpm_wave_simulation_items
                SET status = %s,
                    result_item_json = %s,
                    error_code = %s,
                    error_message = %s,
                    retryable = %s,
                    completed_at = %s,
                    updated_at = %s
                WHERE tenant_id = %s
                  AND operation_id = %s
                  AND wave_item_id = %s
                  AND status = 'RUNNING'
                  AND claim_token = %s
                  AND claim_generation = %s
                  AND lease_expires_at >= %s
                """,
                (
                    status,
                    None
                    if result_item is None
                    else _json_dump(result_item.model_dump(mode="json")),
                    error_code,
                    error_message,
                    retryable,
                    completed_at,
                    completed_at,
                    claim.tenant_id,
                    claim.operation_id,
                    claim.wave_item_id,
                    claim.claim_token,
                    claim.claim_generation,
                    completed_at,
                ),
            )
            if result.rowcount != 1:
                connection.rollback()
                return False
            operation = _operation_from_row(operation_row)
            _refresh_operation_status(
                connection=connection, operation=operation, updated_at=completed_at
            )
            connection.commit()
            return True


def _insert_operation(*, connection: Any, operation: DpmWaveSimulationOperation) -> None:
    connection.execute(
        """
        INSERT INTO dpm_wave_simulation_operations (
            operation_id, tenant_id, wave_id, request_hash, idempotency_key_hash,
            correlation_id, actor_id, source_identity_hash, admitted_wave_version,
            methods_json, max_concurrency, max_attempts, status, cancel_reason_code,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            operation.operation_id,
            operation.tenant_id,
            operation.wave_id,
            operation.request_hash,
            operation.idempotency_key_hash,
            operation.correlation_id,
            operation.actor_id,
            operation.source_identity_hash,
            operation.admitted_wave_version,
            _json_dump(operation.methods),
            operation.max_concurrency,
            operation.max_attempts,
            operation.status,
            operation.cancel_reason_code,
            operation.created_at,
            operation.updated_at,
        ),
    )


def _insert_item(*, connection: Any, item: DpmWaveSimulationItemRecord) -> None:
    connection.execute(
        """
        INSERT INTO dpm_wave_simulation_items (
            operation_id, tenant_id, wave_id, wave_item_id, ordinal, portfolio_id,
            input_json, input_hash, source_identity_hash, status, attempt_count,
            claim_generation, worker_id, claim_token, claimed_at, lease_expires_at,
            result_item_json, error_code, error_message, retryable, completed_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        """,
        (
            item.operation_id,
            item.tenant_id,
            item.wave_id,
            item.wave_item_id,
            item.ordinal,
            item.portfolio_id,
            _json_dump(item.input_payload),
            item.input_hash,
            item.source_identity_hash,
            item.status,
            item.attempt_count,
            item.claim_generation,
            item.worker_id,
            item.claim_token,
            item.claimed_at,
            item.lease_expires_at,
            None
            if item.result_item is None
            else _json_dump(item.result_item.model_dump(mode="json")),
            item.error_code,
            item.error_message,
            item.retryable,
            item.completed_at,
            item.updated_at,
        ),
    )


def _update_wave_to_simulating(*, connection: Any, wave: DpmRebalanceWave) -> None:
    result = connection.execute(
        """
        UPDATE dpm_rebalance_waves
        SET state = %s, version = %s, wave_json = %s, retention_policy = %s
        WHERE wave_id = %s AND tenant_id = %s AND version = %s
        """,
        (
            wave.state,
            wave.version,
            dump_model_json(wave),
            wave.retention_policy,
            wave.wave_id,
            wave.tenant_id,
            wave.version - 1,
        ),
    )
    if result.rowcount != 1:
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT")
    if not wave.events:
        return
    event = wave.events[-1]
    connection.execute(
        """
        INSERT INTO dpm_rebalance_wave_events (
            event_id, wave_id, from_state, to_state, event_type, actor_id,
            reason_code, correlation_id, created_at, event_json
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


def _claim_item(
    *,
    connection: Any,
    operation: DpmWaveSimulationOperation,
    item: DpmWaveSimulationItemRecord,
    worker_id: str,
    claimed_at: datetime,
    lease_expires_at: datetime,
) -> DpmWaveSimulationItemClaim:
    recovery_exhausted = item.attempt_count >= operation.max_attempts
    attempt_count = item.attempt_count + (0 if recovery_exhausted else 1)
    claim_generation = item.claim_generation + 1
    claim_token = f"wsc_{uuid.uuid4().hex}"
    connection.execute(
        """
        UPDATE dpm_wave_simulation_items
        SET status = 'RUNNING', attempt_count = %s, claim_generation = %s,
            worker_id = %s, claim_token = %s, claimed_at = %s,
            lease_expires_at = %s, updated_at = %s
        WHERE operation_id = %s AND wave_item_id = %s AND tenant_id = %s
        """,
        (
            attempt_count,
            claim_generation,
            worker_id,
            claim_token,
            claimed_at,
            lease_expires_at,
            claimed_at,
            operation.operation_id,
            item.wave_item_id,
            operation.tenant_id,
        ),
    )
    return DpmWaveSimulationItemClaim(
        operation_id=operation.operation_id,
        tenant_id=operation.tenant_id,
        wave_id=operation.wave_id,
        wave_item_id=item.wave_item_id,
        portfolio_id=item.portfolio_id,
        input_payload=item.input_payload,
        input_hash=item.input_hash,
        source_identity_hash=item.source_identity_hash,
        worker_id=worker_id,
        claim_token=claim_token,
        claim_generation=claim_generation,
        attempt_count=attempt_count,
        lease_expires_at=lease_expires_at,
        recovery_exhausted=recovery_exhausted,
    )


def _refresh_operation_status(
    *, connection: Any, operation: DpmWaveSimulationOperation, updated_at: datetime
) -> DpmWaveSimulationOperation:
    counts = connection.execute(
        """
        SELECT
            COUNT(*) AS total_count,
            COUNT(*) FILTER (WHERE status = 'PENDING') AS pending_count,
            COUNT(*) FILTER (WHERE status = 'RUNNING') AS running_count,
            COUNT(*) FILTER (WHERE status = 'SUCCEEDED') AS succeeded_count,
            COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_count,
            COUNT(*) FILTER (WHERE status = 'CANCELLED') AS cancelled_count,
            COUNT(*) FILTER (
                WHERE status = 'FAILED'
                  AND retryable = TRUE
                  AND attempt_count < %s
            ) AS retry_waiting_count
        FROM dpm_wave_simulation_items
        WHERE tenant_id = %s AND operation_id = %s
        """,
        (operation.max_attempts, operation.tenant_id, operation.operation_id),
    ).fetchone()
    if counts is None:
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_OPERATION_NOT_FOUND")
    status = derive_wave_simulation_operation_status_from_counts(
        operation=operation,
        total_count=int(counts["total_count"]),
        pending_count=int(counts["pending_count"]),
        running_count=int(counts["running_count"]),
        succeeded_count=int(counts["succeeded_count"]),
        failed_count=int(counts["failed_count"]),
        cancelled_count=int(counts["cancelled_count"]),
        retry_waiting_count=int(counts["retry_waiting_count"]),
    )
    connection.execute(
        """
        UPDATE dpm_wave_simulation_operations
        SET status = %s, updated_at = %s
        WHERE tenant_id = %s AND operation_id = %s
        """,
        (status, updated_at, operation.tenant_id, operation.operation_id),
    )
    return operation.model_copy(update={"status": status, "updated_at": updated_at})


def _select_operation_by_idempotency(
    *, connection: Any, tenant_id: str, idempotency_key_hash: str
) -> DpmWaveSimulationOperation | None:
    row = connection.execute(
        """
        SELECT * FROM dpm_wave_simulation_operations
        WHERE tenant_id = %s AND idempotency_key_hash = %s
        """,
        (tenant_id, idempotency_key_hash),
    ).fetchone()
    return None if row is None else _operation_from_row(row)


def _select_operation_by_correlation(
    *, connection: Any, tenant_id: str, correlation_id: str
) -> DpmWaveSimulationOperation | None:
    row = connection.execute(
        """
        SELECT * FROM dpm_wave_simulation_operations
        WHERE tenant_id = %s AND correlation_id = %s
        """,
        (tenant_id, correlation_id),
    ).fetchone()
    return None if row is None else _operation_from_row(row)


def _operation_from_row(row: Any) -> DpmWaveSimulationOperation:
    return DpmWaveSimulationOperation(
        operation_id=str(row["operation_id"]),
        tenant_id=str(row["tenant_id"]),
        wave_id=str(row["wave_id"]),
        request_hash=str(row["request_hash"]),
        idempotency_key_hash=str(row["idempotency_key_hash"]),
        correlation_id=str(row["correlation_id"]),
        actor_id=str(row["actor_id"]),
        source_identity_hash=str(row["source_identity_hash"]),
        admitted_wave_version=int(row["admitted_wave_version"]),
        methods=cast(list[str], _json_load(row["methods_json"])),
        max_concurrency=int(row["max_concurrency"]),
        max_attempts=int(row["max_attempts"]),
        status=cast(WaveSimulationOperationStatus, str(row["status"])),
        cancel_reason_code=row["cancel_reason_code"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _item_from_row(row: Any) -> DpmWaveSimulationItemRecord:
    result_payload = row["result_item_json"]
    return DpmWaveSimulationItemRecord(
        operation_id=str(row["operation_id"]),
        tenant_id=str(row["tenant_id"]),
        wave_id=str(row["wave_id"]),
        wave_item_id=str(row["wave_item_id"]),
        ordinal=int(row["ordinal"]),
        portfolio_id=str(row["portfolio_id"]),
        input_payload=cast(dict[str, object], _json_load(row["input_json"])),
        input_hash=str(row["input_hash"]),
        source_identity_hash=str(row["source_identity_hash"]),
        status=cast(WaveSimulationItemStatus, str(row["status"])),
        attempt_count=int(row["attempt_count"]),
        claim_generation=int(row["claim_generation"]),
        worker_id=row["worker_id"],
        claim_token=row["claim_token"],
        claimed_at=row["claimed_at"],
        lease_expires_at=row["lease_expires_at"],
        result_item=(
            None
            if result_payload is None
            else load_model_json(DpmRebalanceWaveItem, result_payload)
        ),
        error_code=row["error_code"],
        error_message=row["error_message"],
        retryable=bool(row["retryable"]),
        completed_at=row["completed_at"],
        updated_at=row["updated_at"],
    )


def _validate_admission_items(
    *,
    operation: DpmWaveSimulationOperation,
    items: list[DpmWaveSimulationItemRecord],
    wave: DpmRebalanceWave,
) -> None:
    wave_items = {item.wave_item_id: item for item in wave.items}
    item_ids = [item.wave_item_id for item in items]
    ordinals = [item.ordinal for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_DUPLICATE_ITEM")
    if sorted(ordinals) != list(range(len(items))):
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_ITEM_ORDINAL_CONFLICT")
    for item in items:
        wave_item = wave_items.get(item.wave_item_id)
        if (
            item.operation_id != operation.operation_id
            or item.tenant_id != operation.tenant_id
            or item.wave_id != operation.wave_id
            or wave_item is None
            or wave_item.portfolio_id != item.portfolio_id
        ):
            raise DpmWaveSimulationOperationConflictError(
                "DPM_WAVE_SIMULATION_ITEM_IDENTITY_CONFLICT"
            )


def _json_dump(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)


def _json_load(value: object) -> object:
    return json.loads(value) if isinstance(value, str) else value


def _constraint_name(exc: BaseException) -> str | None:
    diagnostic = getattr(exc, "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    return None if name is None else str(name)


__all__ = ["PostgresDpmWaveSimulationMixin"]
