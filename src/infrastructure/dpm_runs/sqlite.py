import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional, cast

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmSupportabilitySummaryData,
)
from src.core.dpm_runs.repository import DpmRunRepository


class SqliteDpmRunRepository(DpmRunRepository):
    def __init__(self, *, database_path: str) -> None:
        self._lock = Lock()
        self._database_path = database_path
        self._init_db()

    def save_run(self, run: DpmRunRecord) -> None:
        query = """
            INSERT INTO dpm_runs (
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rebalance_run_id) DO UPDATE SET
                correlation_id=excluded.correlation_id,
                request_hash=excluded.request_hash,
                idempotency_key=excluded.idempotency_key,
                portfolio_id=excluded.portfolio_id,
                created_at=excluded.created_at,
                result_json=excluded.result_json
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    run.rebalance_run_id,
                    run.correlation_id,
                    run.request_hash,
                    run.idempotency_key,
                    run.portfolio_id,
                    run.created_at.isoformat(),
                    _json_dump(run.result_json),
                ),
            )
            connection.commit()

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]:
        query = """
            SELECT
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            FROM dpm_runs
            WHERE rebalance_run_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (rebalance_run_id,)).fetchone()
        return self._to_run(row)

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]:
        query = """
            SELECT
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            FROM dpm_runs
            WHERE correlation_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return self._to_run(row)

    def get_run_by_request_hash(self, *, request_hash: str) -> Optional[DpmRunRecord]:
        query = """
            SELECT
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            FROM dpm_runs
            WHERE request_hash = ?
            ORDER BY created_at DESC, rebalance_run_id DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (request_hash,)).fetchone()
        return self._to_run(row)

    def list_runs(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        status: Optional[str],
        request_hash: Optional[str],
        portfolio_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunRecord], Optional[str]]:
        where_clauses = []
        args: list[str] = []
        if created_from is not None:
            where_clauses.append("created_at >= ?")
            args.append(created_from.isoformat())
        if created_to is not None:
            where_clauses.append("created_at <= ?")
            args.append(created_to.isoformat())
        if portfolio_id is not None:
            where_clauses.append("portfolio_id = ?")
            args.append(portfolio_id)
        if request_hash is not None:
            where_clauses.append("request_hash = ?")
            args.append(request_hash)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            FROM dpm_runs
            {where_sql}
            ORDER BY created_at DESC, rebalance_run_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        run_candidates = [self._to_run(row) for row in rows]
        runs = cast(
            list[DpmRunRecord],
            [run for run in run_candidates if run is not None],
        )
        if status is not None:
            runs = [run for run in runs if str(run.result_json.get("status", "")) == status]
        if cursor is not None:
            cursor_index = next(
                (index for index, row in enumerate(runs) if row.rebalance_run_id == cursor),
                None,
            )
            if cursor_index is None:
                return [], None
            runs = runs[cursor_index + 1 :]
        page = runs[:limit]
        next_cursor = page[-1].rebalance_run_id if len(runs) > limit else None
        return page, next_cursor

    def save_run_artifact(self, *, rebalance_run_id: str, artifact_json: dict[str, Any]) -> None:
        query = """
            INSERT INTO dpm_run_artifacts (
                rebalance_run_id,
                artifact_json
            ) VALUES (?, ?)
            ON CONFLICT(rebalance_run_id) DO UPDATE SET
                artifact_json=excluded.artifact_json
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(query, (rebalance_run_id, _json_dump(artifact_json)))
            connection.commit()

    def get_run_artifact(self, *, rebalance_run_id: str) -> Optional[dict[str, Any]]:
        query = """
            SELECT artifact_json
            FROM dpm_run_artifacts
            WHERE rebalance_run_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (rebalance_run_id,)).fetchone()
        if row is None:
            return None
        return cast(dict[str, Any], json.loads(row["artifact_json"]))

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None:
        query = """
            INSERT INTO dpm_run_idempotency (
                idempotency_key,
                request_hash,
                rebalance_run_id,
                created_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                request_hash=excluded.request_hash,
                rebalance_run_id=excluded.rebalance_run_id,
                created_at=excluded.created_at
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    record.idempotency_key,
                    record.request_hash,
                    record.rebalance_run_id,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def get_idempotency_mapping(self, *, idempotency_key: str) -> Optional[DpmRunIdempotencyRecord]:
        query = """
            SELECT
                idempotency_key,
                request_hash,
                rebalance_run_id,
                created_at
            FROM dpm_run_idempotency
            WHERE idempotency_key = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        if row is None:
            return None
        return DpmRunIdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            rebalance_run_id=row["rebalance_run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None:
        query = """
            INSERT INTO dpm_run_idempotency_history (
                idempotency_key,
                rebalance_run_id,
                correlation_id,
                request_hash,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    record.idempotency_key,
                    record.rebalance_run_id,
                    record.correlation_id,
                    record.request_hash,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]:
        query = """
            SELECT
                idempotency_key,
                rebalance_run_id,
                correlation_id,
                request_hash,
                created_at
            FROM dpm_run_idempotency_history
            WHERE idempotency_key = ?
            ORDER BY created_at ASC, rowid ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (idempotency_key,)).fetchall()
        return [
            DpmRunIdempotencyHistoryRecord(
                idempotency_key=row["idempotency_key"],
                rebalance_run_id=row["rebalance_run_id"],
                correlation_id=row["correlation_id"],
                request_hash=row["request_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            WHERE operation_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (operation_id,)).fetchone()
        return self._to_operation(row)

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            WHERE correlation_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return self._to_operation(row)

    def list_operations(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        operation_type: Optional[str],
        status: Optional[str],
        correlation_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmAsyncOperationRecord], Optional[str]]:
        where_clauses = []
        args: list[str] = []
        if created_from is not None:
            where_clauses.append("created_at >= ?")
            args.append(created_from.isoformat())
        if created_to is not None:
            where_clauses.append("created_at <= ?")
            args.append(created_to.isoformat())
        if operation_type is not None:
            where_clauses.append("operation_type = ?")
            args.append(operation_type)
        if status is not None:
            where_clauses.append("status = ?")
            args.append(status)
        if correlation_id is not None:
            where_clauses.append("correlation_id = ?")
            args.append(correlation_id)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            {where_sql}
            ORDER BY created_at DESC, operation_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        operation_candidates = [self._to_operation(row) for row in rows]
        operations = cast(
            list[DpmAsyncOperationRecord],
            [operation for operation in operation_candidates if operation is not None],
        )
        if cursor is not None:
            cursor_index = next(
                (index for index, row in enumerate(operations) if row.operation_id == cursor),
                None,
            )
            if cursor_index is None:
                return [], None
            operations = operations[cursor_index + 1 :]
        page = operations[:limit]
        next_cursor = page[-1].operation_id if len(operations) > limit else None
        return page, next_cursor

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int:
        cutoff = now.astimezone(timezone.utc) - timedelta(seconds=ttl_seconds)
        query = """
            DELETE FROM dpm_async_operations
            WHERE COALESCE(finished_at, created_at) < ?
        """
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(query, (cutoff.isoformat(),))
            connection.commit()
            return cursor.rowcount

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None:
        query = """
            INSERT INTO dpm_workflow_decisions (
                decision_id,
                run_id,
                action,
                reason_code,
                comment,
                actor_id,
                decided_at,
                correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    decision.decision_id,
                    decision.run_id,
                    decision.action,
                    decision.reason_code,
                    decision.comment,
                    decision.actor_id,
                    decision.decided_at.isoformat(),
                    decision.correlation_id,
                ),
            )
            connection.commit()

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]:
        query = """
            SELECT
                decision_id,
                run_id,
                action,
                reason_code,
                comment,
                actor_id,
                decided_at,
                correlation_id
            FROM dpm_workflow_decisions
            WHERE run_id = ?
            ORDER BY decided_at ASC, rowid ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (rebalance_run_id,)).fetchall()
        return [
            DpmRunWorkflowDecisionRecord(
                decision_id=row["decision_id"],
                run_id=row["run_id"],
                action=row["action"],
                reason_code=row["reason_code"],
                comment=row["comment"],
                actor_id=row["actor_id"],
                decided_at=datetime.fromisoformat(row["decided_at"]),
                correlation_id=row["correlation_id"],
            )
            for row in rows
        ]

    def list_workflow_decisions_filtered(
        self,
        *,
        rebalance_run_id: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        reason_code: Optional[str],
        decided_from: Optional[datetime],
        decided_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunWorkflowDecisionRecord], Optional[str]]:
        where_clauses = []
        args: list[str] = []
        if rebalance_run_id is not None:
            where_clauses.append("run_id = ?")
            args.append(rebalance_run_id)
        if action is not None:
            where_clauses.append("action = ?")
            args.append(action)
        if actor_id is not None:
            where_clauses.append("actor_id = ?")
            args.append(actor_id)
        if reason_code is not None:
            where_clauses.append("reason_code = ?")
            args.append(reason_code)
        if decided_from is not None:
            where_clauses.append("decided_at >= ?")
            args.append(decided_from.isoformat())
        if decided_to is not None:
            where_clauses.append("decided_at <= ?")
            args.append(decided_to.isoformat())
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                decision_id,
                run_id,
                action,
                reason_code,
                comment,
                actor_id,
                decided_at,
                correlation_id
            FROM dpm_workflow_decisions
            {where_sql}
            ORDER BY decided_at DESC, decision_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        decisions = [
            DpmRunWorkflowDecisionRecord(
                decision_id=row["decision_id"],
                run_id=row["run_id"],
                action=row["action"],
                reason_code=row["reason_code"],
                comment=row["comment"],
                actor_id=row["actor_id"],
                decided_at=datetime.fromisoformat(row["decided_at"]),
                correlation_id=row["correlation_id"],
            )
            for row in rows
        ]
        if cursor is not None:
            cursor_index = next(
                (index for index, row in enumerate(decisions) if row.decision_id == cursor),
                None,
            )
            if cursor_index is None:
                return [], None
            decisions = decisions[cursor_index + 1 :]
        page = decisions[:limit]
        next_cursor = page[-1].decision_id if len(decisions) > limit else None
        return page, next_cursor

    def append_lineage_edge(self, edge: DpmLineageEdgeRecord) -> None:
        query = """
            INSERT INTO dpm_lineage_edges (
                source_entity_id,
                edge_type,
                target_entity_id,
                created_at,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?)
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    edge.source_entity_id,
                    edge.edge_type,
                    edge.target_entity_id,
                    edge.created_at.isoformat(),
                    _json_dump(edge.metadata_json),
                ),
            )
            connection.commit()

    def list_lineage_edges(self, *, entity_id: str) -> list[DpmLineageEdgeRecord]:
        query = """
            SELECT
                source_entity_id,
                edge_type,
                target_entity_id,
                created_at,
                metadata_json
            FROM dpm_lineage_edges
            WHERE source_entity_id = ? OR target_entity_id = ?
            ORDER BY created_at ASC, rowid ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (entity_id, entity_id)).fetchall()
        return [
            DpmLineageEdgeRecord(
                source_entity_id=row["source_entity_id"],
                edge_type=row["edge_type"],
                target_entity_id=row["target_entity_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata_json=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def get_supportability_summary(self) -> DpmSupportabilitySummaryData:
        run_query = """
            SELECT
                COUNT(*) AS run_count,
                MIN(created_at) AS oldest_run_created_at,
                MAX(created_at) AS newest_run_created_at
            FROM dpm_runs
        """
        operation_query = """
            SELECT
                COUNT(*) AS operation_count,
                MIN(created_at) AS oldest_operation_created_at,
                MAX(created_at) AS newest_operation_created_at
            FROM dpm_async_operations
        """
        operation_status_query = """
            SELECT status, COUNT(*) AS status_count
            FROM dpm_async_operations
            GROUP BY status
        """
        run_status_query = """
            SELECT result_json
            FROM dpm_runs
        """
        workflow_decision_count_query = (
            "SELECT COUNT(*) AS workflow_decision_count FROM dpm_workflow_decisions"
        )
        workflow_action_counts_query = """
            SELECT action, COUNT(*) AS action_count
            FROM dpm_workflow_decisions
            GROUP BY action
        """
        workflow_reason_code_counts_query = """
            SELECT reason_code, COUNT(*) AS reason_code_count
            FROM dpm_workflow_decisions
            GROUP BY reason_code
        """
        lineage_edge_count_query = "SELECT COUNT(*) AS lineage_edge_count FROM dpm_lineage_edges"
        with closing(self._connect()) as connection:
            run_row = connection.execute(run_query).fetchone()
            operation_row = connection.execute(operation_query).fetchone()
            status_rows = connection.execute(operation_status_query).fetchall()
            run_rows = connection.execute(run_status_query).fetchall()
            workflow_row = connection.execute(workflow_decision_count_query).fetchone()
            workflow_action_rows = connection.execute(workflow_action_counts_query).fetchall()
            workflow_reason_code_rows = connection.execute(
                workflow_reason_code_counts_query
            ).fetchall()
            lineage_row = connection.execute(lineage_edge_count_query).fetchone()

        operation_status_counts = {
            row["status"]: int(row["status_count"])
            for row in status_rows
            if row["status"] is not None
        }
        run_status_counts: dict[str, int] = {}
        for row in run_rows:
            status = str(json.loads(row["result_json"]).get("status", ""))
            if status:
                run_status_counts[status] = run_status_counts.get(status, 0) + 1
        workflow_action_counts = {
            row["action"]: int(row["action_count"])
            for row in workflow_action_rows
            if row["action"] is not None
        }
        workflow_reason_code_counts = {
            row["reason_code"]: int(row["reason_code_count"])
            for row in workflow_reason_code_rows
            if row["reason_code"] is not None
        }
        return DpmSupportabilitySummaryData(
            run_count=int(run_row["run_count"]),
            operation_count=int(operation_row["operation_count"]),
            operation_status_counts=operation_status_counts,
            run_status_counts=run_status_counts,
            workflow_decision_count=int(workflow_row["workflow_decision_count"]),
            workflow_action_counts=workflow_action_counts,
            workflow_reason_code_counts=workflow_reason_code_counts,
            lineage_edge_count=int(lineage_row["lineage_edge_count"]),
            oldest_run_created_at=_optional_datetime(run_row["oldest_run_created_at"]),
            newest_run_created_at=_optional_datetime(run_row["newest_run_created_at"]),
            oldest_operation_created_at=_optional_datetime(
                operation_row["oldest_operation_created_at"]
            ),
            newest_operation_created_at=_optional_datetime(
                operation_row["newest_operation_created_at"]
            ),
        )

    def purge_expired_runs(self, *, retention_days: int, now: datetime) -> int:
        if retention_days < 1:
            return 0
        cutoff = now.astimezone(timezone.utc) - timedelta(days=retention_days)
        select_expired = """
            SELECT rebalance_run_id, correlation_id, idempotency_key
            FROM dpm_runs
            WHERE created_at < ?
        """
        with self._lock, closing(self._connect()) as connection:
            expired_rows = connection.execute(select_expired, (cutoff.isoformat(),)).fetchall()
            if not expired_rows:
                return 0

            run_ids = [row["rebalance_run_id"] for row in expired_rows]
            correlation_ids = [row["correlation_id"] for row in expired_rows]
            idempotency_keys = [
                row["idempotency_key"] for row in expired_rows if row["idempotency_key"]
            ]

            run_id_placeholders = _placeholders(len(run_ids))
            connection.execute(
                f"DELETE FROM dpm_runs WHERE rebalance_run_id IN ({run_id_placeholders})",
                tuple(run_ids),
            )
            connection.execute(
                f"DELETE FROM dpm_workflow_decisions WHERE run_id IN ({run_id_placeholders})",
                tuple(run_ids),
            )
            connection.execute(
                f"DELETE FROM dpm_run_artifacts WHERE rebalance_run_id IN ({run_id_placeholders})",
                tuple(run_ids),
            )
            connection.execute(
                f"""
                DELETE FROM dpm_run_idempotency
                WHERE rebalance_run_id IN ({run_id_placeholders})
                """,
                tuple(run_ids),
            )
            connection.execute(
                f"""
                DELETE FROM dpm_run_idempotency_history
                WHERE rebalance_run_id IN ({run_id_placeholders})
                """,
                tuple(run_ids),
            )

            entities = run_ids + correlation_ids + idempotency_keys
            if entities:
                entity_placeholders = _placeholders(len(entities))
                connection.execute(
                    f"""
                    DELETE FROM dpm_lineage_edges
                    WHERE source_entity_id IN ({entity_placeholders})
                    OR target_entity_id IN ({entity_placeholders})
                    """,
                    tuple(entities + entities),
                )

            connection.commit()
            return len(run_ids)

    def _upsert_operation(self, operation: DpmAsyncOperationRecord) -> None:
        query = """
            INSERT INTO dpm_async_operations (
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(operation_id) DO UPDATE SET
                operation_type=excluded.operation_type,
                status=excluded.status,
                correlation_id=excluded.correlation_id,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                result_json=excluded.result_json,
                error_json=excluded.error_json,
                request_json=excluded.request_json
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    operation.operation_id,
                    operation.operation_type,
                    operation.status,
                    operation.correlation_id,
                    operation.created_at.isoformat(),
                    _optional_iso(operation.started_at),
                    _optional_iso(operation.finished_at),
                    _optional_json(operation.result_json),
                    _optional_json(operation.error_json),
                    _optional_json(operation.request_json),
                ),
            )
            connection.commit()

    def _to_run(self, row: Optional[sqlite3.Row]) -> Optional[DpmRunRecord]:
        if row is None:
            return None
        return DpmRunRecord(
            rebalance_run_id=row["rebalance_run_id"],
            correlation_id=row["correlation_id"],
            request_hash=row["request_hash"],
            idempotency_key=row["idempotency_key"],
            portfolio_id=row["portfolio_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            result_json=json.loads(row["result_json"]),
        )

    def _to_operation(self, row: Optional[sqlite3.Row]) -> Optional[DpmAsyncOperationRecord]:
        if row is None:
            return None
        return DpmAsyncOperationRecord(
            operation_id=row["operation_id"],
            operation_type=row["operation_type"],
            status=row["status"],
            correlation_id=row["correlation_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=_optional_datetime(row["started_at"]),
            finished_at=_optional_datetime(row["finished_at"]),
            result_json=_optional_load_json(row["result_json"]),
            error_json=_optional_load_json(row["error_json"]),
            request_json=_optional_load_json(row["request_json"]),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dpm_runs (
                    rebalance_run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    idempotency_key TEXT NULL,
                    portfolio_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_run_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    rebalance_run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_run_idempotency_history (
                    idempotency_key TEXT NOT NULL,
                    rebalance_run_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_run_artifacts (
                    rebalance_run_id TEXT PRIMARY KEY,
                    artifact_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_async_operations (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    finished_at TEXT NULL,
                    result_json TEXT NULL,
                    error_json TEXT NULL,
                    request_json TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_workflow_decisions (
                    decision_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    comment TEXT NULL,
                    actor_id TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    correlation_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_lineage_edges (
                    source_entity_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                """
            )
            connection.commit()


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _optional_json(value: Optional[dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return _json_dump(value)


def _optional_load_json(value: Optional[str]) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    return cast(dict[str, Any], json.loads(value))


def _optional_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _placeholders(count: int) -> str:
    return ",".join("?" for _ in range(count))
