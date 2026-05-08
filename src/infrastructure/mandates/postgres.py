from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime
from typing import Any, Optional

from src.core.common.capabilities import has_psycopg
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmMandateRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_MANDATE_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_MANDATE_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_mandate_snapshot(self, twin: DpmMandateDigitalTwin) -> None:
        query = """
            INSERT INTO dpm_mandate_snapshots (
                mandate_snapshot_id,
                mandate_id,
                portfolio_id,
                mandate_version,
                as_of_date,
                source_hash,
                source_lineage_json,
                payload_json,
                created_at,
                created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (mandate_id, mandate_version) DO UPDATE SET
                portfolio_id=excluded.portfolio_id,
                as_of_date=excluded.as_of_date,
                source_hash=excluded.source_hash,
                source_lineage_json=excluded.source_lineage_json,
                payload_json=excluded.payload_json,
                created_at=excluded.created_at,
                created_by=excluded.created_by
        """
        payload_json = dump_model_json(twin)
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    _mandate_snapshot_id(twin),
                    twin.mandate_id,
                    twin.portfolio_id,
                    twin.mandate_version,
                    twin.as_of_date.isoformat(),
                    _source_hash(payload_json),
                    json.dumps(
                        [lineage.model_dump(mode="json") for lineage in twin.source_lineage],
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    payload_json,
                    datetime.now().astimezone().isoformat(),
                    "lotus-manage",
                ),
            )
            connection.commit()

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> Optional[DpmMandateDigitalTwin]:
        query = """
            SELECT payload_json
            FROM dpm_mandate_snapshots
            WHERE portfolio_id = %s
            ORDER BY as_of_date DESC, mandate_version DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (portfolio_id,)).fetchone()
        return _to_twin(row)

    def get_latest_mandate(self, *, mandate_id: str) -> Optional[DpmMandateDigitalTwin]:
        query = """
            SELECT payload_json
            FROM dpm_mandate_snapshots
            WHERE mandate_id = %s
            ORDER BY as_of_date DESC, mandate_version DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (mandate_id,)).fetchone()
        return _to_twin(row)

    def list_mandate_versions(self, *, mandate_id: str) -> list[DpmMandateDigitalTwin]:
        query = """
            SELECT payload_json
            FROM dpm_mandate_snapshots
            WHERE mandate_id = %s
            ORDER BY as_of_date DESC, mandate_version DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (mandate_id,)).fetchall()
        return [load_model_json(DpmMandateDigitalTwin, _payload(row)) for row in rows]

    def save_health_snapshot(self, snapshot: DpmMandateHealthSnapshot) -> None:
        query = """
            INSERT INTO dpm_mandate_health_snapshots (
                health_snapshot_id,
                mandate_id,
                portfolio_id,
                as_of_date,
                health_score,
                health_state,
                top_reason_code,
                source_readiness_state,
                dimension_scores_json,
                payload_json,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (health_snapshot_id) DO UPDATE SET
                health_score=excluded.health_score,
                health_state=excluded.health_state,
                top_reason_code=excluded.top_reason_code,
                source_readiness_state=excluded.source_readiness_state,
                dimension_scores_json=excluded.dimension_scores_json,
                payload_json=excluded.payload_json,
                created_at=excluded.created_at
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    snapshot.health_snapshot_id,
                    snapshot.mandate_id,
                    snapshot.portfolio_id,
                    snapshot.as_of_date.isoformat(),
                    snapshot.health_score,
                    snapshot.health_state.value,
                    snapshot.top_reasons[0].reason_code if snapshot.top_reasons else None,
                    snapshot.source_readiness_state,
                    json.dumps(
                        [score.model_dump(mode="json") for score in snapshot.dimension_scores],
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    dump_model_json(snapshot),
                    snapshot.calculated_at.isoformat(),
                ),
            )
            connection.commit()

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
    ) -> Optional[DpmMandateHealthSnapshot]:
        query = """
            SELECT payload_json
            FROM dpm_mandate_health_snapshots
            WHERE mandate_id = %s
            ORDER BY created_at DESC, health_snapshot_id DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (mandate_id,)).fetchone()
        if row is None:
            return None
        return load_model_json(DpmMandateHealthSnapshot, _payload(row))

    def save_monitoring_exception(self, exception: DpmMonitoringException) -> None:
        query = """
            INSERT INTO dpm_monitoring_exceptions (
                exception_id,
                monitoring_run_id,
                mandate_id,
                portfolio_id,
                as_of_date,
                dimension,
                severity,
                reason_code,
                state,
                measured_value_json,
                threshold_value_json,
                recommended_action,
                source_lineage_json,
                resolved_at,
                resolution_reason,
                resolved_by,
                payload_json,
                detected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (exception_id) DO UPDATE SET
                state=excluded.state,
                resolved_at=excluded.resolved_at,
                resolution_reason=excluded.resolution_reason,
                resolved_by=excluded.resolved_by,
                payload_json=excluded.payload_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    exception.exception_id,
                    exception.monitoring_run_id,
                    exception.mandate_id,
                    exception.portfolio_id,
                    exception.as_of_date.isoformat(),
                    exception.dimension.value,
                    exception.severity.value,
                    exception.reason_code,
                    exception.state,
                    _optional_json_value(exception.measured_value),
                    _optional_json_value(exception.threshold_value),
                    exception.recommended_action.value,
                    json.dumps(
                        [lineage.model_dump(mode="json") for lineage in exception.source_lineage],
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    _optional_iso(exception.resolved_at),
                    exception.resolution_reason,
                    None,
                    dump_model_json(exception),
                    exception.detected_at.isoformat(),
                ),
            )
            connection.commit()

    def save_monitoring_run(self, run: DpmMonitoringRun) -> None:
        query = """
            INSERT INTO dpm_monitoring_runs (
                monitoring_run_id,
                as_of_date,
                status,
                portfolio_manager_id,
                tenant_id,
                requested_by,
                filters_json,
                source_readiness_summary_json,
                started_at,
                completed_at,
                failure_reason,
                payload_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (monitoring_run_id) DO UPDATE SET
                status=excluded.status,
                filters_json=excluded.filters_json,
                source_readiness_summary_json=excluded.source_readiness_summary_json,
                completed_at=excluded.completed_at,
                failure_reason=excluded.failure_reason,
                payload_json=excluded.payload_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    run.monitoring_run_id,
                    run.as_of_date.isoformat(),
                    run.status,
                    run.filters.get("portfolio_manager_id"),
                    run.filters.get("tenant_id"),
                    run.filters.get("requested_by", "lotus-manage"),
                    json.dumps(run.filters, separators=(",", ":"), sort_keys=True),
                    json.dumps(
                        run.source_readiness_summary,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    run.requested_at.isoformat(),
                    _optional_iso(run.completed_at),
                    run.failure_reason,
                    dump_model_json(run),
                ),
            )
            connection.commit()

    def get_monitoring_run(
        self,
        *,
        monitoring_run_id: str,
    ) -> Optional[DpmMonitoringRun]:
        query = "SELECT payload_json FROM dpm_monitoring_runs WHERE monitoring_run_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (monitoring_run_id,)).fetchone()
        if row is None:
            return None
        return load_model_json(DpmMonitoringRun, _payload(row))

    def list_monitoring_runs(
        self,
        *,
        status: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmMonitoringRun], Optional[str]]:
        where_clauses: list[str] = []
        args: list[Any] = []
        if status is not None:
            where_clauses.append("status = %s")
            args.append(status)
        if cursor is not None:
            where_clauses.append(
                """
                (
                    started_at < (SELECT started_at FROM dpm_monitoring_runs WHERE monitoring_run_id = %s)
                    OR (
                        started_at = (SELECT started_at FROM dpm_monitoring_runs WHERE monitoring_run_id = %s)
                        AND monitoring_run_id < %s
                    )
                )
                """
            )
            args.extend([cursor, cursor, cursor])
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT payload_json, monitoring_run_id
            FROM dpm_monitoring_runs
            {where_sql}
            ORDER BY started_at DESC, monitoring_run_id DESC
            LIMIT %s
        """
        args.append(limit + 1)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        runs = [load_model_json(DpmMonitoringRun, _payload(row)) for row in rows]
        page = runs[:limit]
        next_cursor = page[-1].monitoring_run_id if len(runs) > limit else None
        return page, next_cursor

    def list_monitoring_exceptions(
        self,
        *,
        monitoring_run_id: Optional[str],
        mandate_id: Optional[str],
        portfolio_id: Optional[str],
        state: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmMonitoringException], Optional[str]]:
        where_clauses: list[str] = []
        args: list[Any] = []
        if monitoring_run_id is not None:
            where_clauses.append("monitoring_run_id = %s")
            args.append(monitoring_run_id)
        if mandate_id is not None:
            where_clauses.append("mandate_id = %s")
            args.append(mandate_id)
        if portfolio_id is not None:
            where_clauses.append("portfolio_id = %s")
            args.append(portfolio_id)
        if state is not None:
            where_clauses.append("state = %s")
            args.append(state)
        if cursor is not None:
            where_clauses.append(
                """
                (
                    detected_at < (SELECT detected_at FROM dpm_monitoring_exceptions WHERE exception_id = %s)
                    OR (
                        detected_at = (SELECT detected_at FROM dpm_monitoring_exceptions WHERE exception_id = %s)
                        AND exception_id < %s
                    )
                )
                """
            )
            args.extend([cursor, cursor, cursor])
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT payload_json, exception_id
            FROM dpm_monitoring_exceptions
            {where_sql}
            ORDER BY detected_at DESC, exception_id DESC
            LIMIT %s
        """
        args.append(limit + 1)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        exceptions = [load_model_json(DpmMonitoringException, _payload(row)) for row in rows]
        page = exceptions[:limit]
        next_cursor = page[-1].exception_id if len(exceptions) > limit else None
        return page, next_cursor

    def resolve_monitoring_exception(
        self,
        *,
        exception_id: str,
        resolved_at: datetime,
        resolution_reason: str,
    ) -> Optional[DpmMonitoringException]:
        query = "SELECT payload_json FROM dpm_monitoring_exceptions WHERE exception_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (exception_id,)).fetchone()
        if row is None:
            return None
        current = load_model_json(DpmMonitoringException, _payload(row))
        resolved = current.model_copy(
            update={
                "state": "RESOLVED",
                "resolved_at": resolved_at,
                "resolution_reason": resolution_reason,
            }
        )
        self.save_monitoring_exception(resolved)
        return resolved

    def purge_mandate_records_before(self, *, cutoff: datetime) -> int:
        removed = 0
        with closing(self._connect()) as connection:
            for table, column, predicate in [
                ("dpm_mandate_snapshots", "created_at", ""),
                ("dpm_mandate_health_snapshots", "created_at", ""),
                ("dpm_monitoring_runs", "started_at", ""),
                (
                    "dpm_monitoring_exceptions",
                    "detected_at",
                    "AND (state = 'RESOLVED' OR resolved_at IS NOT NULL)",
                ),
            ]:
                result = connection.execute(
                    f"DELETE FROM {table} WHERE {column} < %s {predicate}",
                    (cutoff.isoformat(),),
                )
                removed += int(getattr(result, "rowcount", 0) or 0)
            connection.commit()
        return removed

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _to_twin(row: Any) -> Optional[DpmMandateDigitalTwin]:
    if row is None:
        return None
    return load_model_json(DpmMandateDigitalTwin, _payload(row))


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


def _mandate_snapshot_id(twin: DpmMandateDigitalTwin) -> str:
    return f"ms_{twin.mandate_id}_{twin.mandate_version}"


def _source_hash(payload_json: str) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(payload_json.encode('utf-8')).hexdigest()}"


def _optional_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def _optional_json_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)
