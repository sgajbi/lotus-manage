from datetime import datetime, timezone
from types import ModuleType

import src.infrastructure.dpm_runs.postgres as postgres_module
from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.dpm_runs.postgres import (
    PostgresDpmRunRepository,
    _import_psycopg,
    _json_dump,
)


class _FakeCursor:
    def __init__(self, row=None, rows=None, rowcount=0):
        self._row = row
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self):
        self.runs = {}
        self.artifacts = {}
        self.idempotency = {}
        self.idempotency_history = []
        self.operations = {}
        self.workflow_decisions = {}
        self.lineage_edges = []
        self.schema_migrations = {}
        self.commits = 0

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql == "SELECT pg_advisory_lock(%s::bigint)":
            return _FakeCursor(None)
        if sql == "SELECT pg_advisory_unlock(%s::bigint)":
            return _FakeCursor(None)
        if sql.startswith("CREATE TABLE"):
            return _FakeCursor(None)
        if "FROM schema_migrations" in sql:
            namespace = args[0]
            rows = [
                {"version": version, "checksum": checksum}
                for (stored_namespace, version), checksum in self.schema_migrations.items()
                if stored_namespace == namespace
            ]
            rows = sorted(rows, key=lambda row: row["version"])
            return _FakeCursor(rows=rows)
        if "INSERT INTO schema_migrations" in sql:
            self.schema_migrations[(args[1], args[0])] = args[2]
            return _FakeCursor(None)
        if "INSERT INTO dpm_runs" in sql:
            row = {
                "rebalance_run_id": args[0],
                "correlation_id": args[1],
                "request_hash": args[2],
                "idempotency_key": args[3],
                "portfolio_id": args[4],
                "created_at": args[5],
                "result_json": args[6],
            }
            self.runs[args[0]] = row
            return _FakeCursor(None)
        if "FROM dpm_runs WHERE rebalance_run_id = %s" in sql:
            return _FakeCursor(self.runs.get(args[0]))
        if "FROM dpm_runs WHERE correlation_id = %s" in sql:
            row = next(
                (run for run in self.runs.values() if run["correlation_id"] == args[0]),
                None,
            )
            return _FakeCursor(row)
        if "FROM dpm_runs WHERE request_hash = %s" in sql and "LIMIT 1" in sql:
            rows = [run for run in self.runs.values() if run["request_hash"] == args[0]]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["rebalance_run_id"]),
                reverse=True,
            )
            return _FakeCursor(rows[0] if rows else None)
        if "FROM dpm_runs" in sql and "ORDER BY created_at DESC" in sql:
            rows = list(self.runs.values())
            arg_index = 0
            if "created_at >= %s" in sql:
                created_from = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] >= created_from]
            if "created_at <= %s" in sql:
                created_to = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] <= created_to]
            if "portfolio_id = %s" in sql:
                portfolio_id = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["portfolio_id"] == portfolio_id]
            if "request_hash = %s" in sql:
                request_hash = args[arg_index]
                rows = [row for row in rows if row["request_hash"] == request_hash]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["rebalance_run_id"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows)
        if "INSERT INTO dpm_run_artifacts" in sql:
            self.artifacts[args[0]] = {"artifact_json": args[1]}
            return _FakeCursor(None)
        if "SELECT artifact_json FROM dpm_run_artifacts" in sql:
            return _FakeCursor(self.artifacts.get(args[0]))
        if "INSERT INTO dpm_run_idempotency (" in sql:
            row = {
                "idempotency_key": args[0],
                "request_hash": args[1],
                "rebalance_run_id": args[2],
                "created_at": args[3],
            }
            self.idempotency[args[0]] = row
            return _FakeCursor()
        if "FROM dpm_run_idempotency WHERE idempotency_key = %s" in sql:
            return _FakeCursor(self.idempotency.get(args[0]))
        if "INSERT INTO dpm_run_idempotency_history (" in sql:
            self.idempotency_history.append(
                {
                    "idempotency_key": args[0],
                    "rebalance_run_id": args[1],
                    "correlation_id": args[2],
                    "request_hash": args[3],
                    "created_at": args[4],
                }
            )
            return _FakeCursor()
        if (
            "SELECT idempotency_key, rebalance_run_id, correlation_id, request_hash, created_at "
            "FROM dpm_run_idempotency_history" in sql
        ):
            rows = [row for row in self.idempotency_history if row["idempotency_key"] == args[0]]
            rows = sorted(rows, key=lambda row: row["created_at"])
            return _FakeCursor(rows=rows)
        if "INSERT INTO dpm_async_operations (" in sql:
            row = {
                "operation_id": args[0],
                "operation_type": args[1],
                "status": args[2],
                "correlation_id": args[3],
                "created_at": args[4],
                "started_at": args[5],
                "finished_at": args[6],
                "result_json": args[7],
                "error_json": args[8],
                "request_json": args[9],
            }
            self.operations[args[0]] = row
            return _FakeCursor()
        if "FROM dpm_async_operations WHERE operation_id = %s" in sql:
            return _FakeCursor(self.operations.get(args[0]))
        if "FROM dpm_async_operations WHERE correlation_id = %s" in sql:
            row = next(
                (
                    operation
                    for operation in self.operations.values()
                    if operation["correlation_id"] == args[0]
                ),
                None,
            )
            return _FakeCursor(row)
        if "FROM dpm_async_operations" in sql and "ORDER BY created_at DESC" in sql:
            rows = list(self.operations.values())
            arg_index = 0
            if "created_at >= %s" in sql:
                created_from = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] >= created_from]
            if "created_at <= %s" in sql:
                created_to = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] <= created_to]
            if "operation_type = %s" in sql:
                operation_type = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["operation_type"] == operation_type]
            if "status = %s" in sql:
                status = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["status"] == status]
            if "correlation_id = %s" in sql:
                correlation_id = args[arg_index]
                rows = [row for row in rows if row["correlation_id"] == correlation_id]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["operation_id"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows)
        if "DELETE FROM dpm_async_operations" in sql:
            cutoff = args[0]
            to_remove = []
            for operation_id, row in self.operations.items():
                anchor = row["finished_at"] or row["created_at"]
                if anchor < cutoff:
                    to_remove.append(operation_id)
            for operation_id in to_remove:
                self.operations.pop(operation_id, None)
            return _FakeCursor(rowcount=len(to_remove))
        if "INSERT INTO dpm_workflow_decisions (" in sql:
            row = {
                "decision_id": args[0],
                "run_id": args[1],
                "action": args[2],
                "reason_code": args[3],
                "comment": args[4],
                "actor_id": args[5],
                "decided_at": args[6],
                "correlation_id": args[7],
            }
            self.workflow_decisions[args[0]] = row
            return _FakeCursor()
        if "FROM dpm_workflow_decisions" in sql and "ORDER BY decided_at ASC" in sql:
            rows = [row for row in self.workflow_decisions.values() if row["run_id"] == args[0]]
            rows = sorted(rows, key=lambda row: row["decided_at"])
            return _FakeCursor(rows=rows)
        if "FROM dpm_workflow_decisions" in sql and "ORDER BY decided_at DESC" in sql:
            rows = list(self.workflow_decisions.values())
            arg_index = 0
            if "run_id = %s" in sql:
                run_id = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["run_id"] == run_id]
            if "action = %s" in sql:
                action = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["action"] == action]
            if "actor_id = %s" in sql:
                actor_id = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["actor_id"] == actor_id]
            if "reason_code = %s" in sql:
                reason_code = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["reason_code"] == reason_code]
            if "decided_at >= %s" in sql:
                decided_from = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["decided_at"] >= decided_from]
            if "decided_at <= %s" in sql:
                decided_to = args[arg_index]
                rows = [row for row in rows if row["decided_at"] <= decided_to]
            rows = sorted(
                rows,
                key=lambda row: (row["decided_at"], row["decision_id"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows)
        if "INSERT INTO dpm_lineage_edges (" in sql:
            self.lineage_edges.append(
                {
                    "source_entity_id": args[0],
                    "edge_type": args[1],
                    "target_entity_id": args[2],
                    "created_at": args[3],
                    "metadata_json": args[4],
                }
            )
            return _FakeCursor()
        if "FROM dpm_lineage_edges" in sql and "ORDER BY created_at ASC" in sql:
            entity_id = args[0]
            rows = [
                row
                for row in self.lineage_edges
                if row["source_entity_id"] == entity_id or row["target_entity_id"] == entity_id
            ]
            rows = sorted(rows, key=lambda row: row["created_at"])
            return _FakeCursor(rows=rows)
        if "SELECT COUNT(*) AS run_count" in sql:
            created = [row["created_at"] for row in self.runs.values()]
            row = {
                "run_count": len(self.runs),
                "oldest_run_created_at": min(created) if created else None,
                "newest_run_created_at": max(created) if created else None,
            }
            return _FakeCursor(row=row)
        if "SELECT COUNT(*) AS operation_count" in sql:
            created = [row["created_at"] for row in self.operations.values()]
            row = {
                "operation_count": len(self.operations),
                "oldest_operation_created_at": min(created) if created else None,
                "newest_operation_created_at": max(created) if created else None,
            }
            return _FakeCursor(row=row)
        if "SELECT status, COUNT(*) AS status_count" in sql:
            counts = {}
            for operation in self.operations.values():
                counts[operation["status"]] = counts.get(operation["status"], 0) + 1
            rows = [{"status": key, "status_count": value} for key, value in counts.items()]
            return _FakeCursor(rows=rows)
        if "SELECT result_json FROM dpm_runs" in sql:
            rows = [{"result_json": row["result_json"]} for row in self.runs.values()]
            return _FakeCursor(rows=rows)
        if "SELECT COUNT(*) AS workflow_decision_count" in sql:
            return _FakeCursor(row={"workflow_decision_count": len(self.workflow_decisions)})
        if "SELECT action, COUNT(*) AS action_count" in sql:
            counts = {}
            for decision in self.workflow_decisions.values():
                counts[decision["action"]] = counts.get(decision["action"], 0) + 1
            rows = [{"action": key, "action_count": value} for key, value in counts.items()]
            return _FakeCursor(rows=rows)
        if "SELECT reason_code, COUNT(*) AS reason_code_count" in sql:
            counts = {}
            for decision in self.workflow_decisions.values():
                counts[decision["reason_code"]] = counts.get(decision["reason_code"], 0) + 1
            rows = [
                {"reason_code": key, "reason_code_count": value} for key, value in counts.items()
            ]
            return _FakeCursor(rows=rows)
        if "SELECT COUNT(*) AS lineage_edge_count FROM dpm_lineage_edges" in sql:
            return _FakeCursor(row={"lineage_edge_count": len(self.lineage_edges)})
        if (
            "SELECT rebalance_run_id, correlation_id, idempotency_key" in sql
            and "created_at <" in sql
        ):
            cutoff = args[0]
            rows = [
                {
                    "rebalance_run_id": row["rebalance_run_id"],
                    "correlation_id": row["correlation_id"],
                    "idempotency_key": row["idempotency_key"],
                }
                for row in self.runs.values()
                if row["created_at"] < cutoff
            ]
            return _FakeCursor(rows=rows)
        if "DELETE FROM dpm_runs WHERE rebalance_run_id IN (" in sql:
            for run_id in args:
                self.runs.pop(run_id, None)
            return _FakeCursor()
        if "DELETE FROM dpm_workflow_decisions WHERE run_id IN (" in sql:
            run_ids = set(args)
            self.workflow_decisions = {
                key: value
                for key, value in self.workflow_decisions.items()
                if value["run_id"] not in run_ids
            }
            return _FakeCursor()
        if "DELETE FROM dpm_run_artifacts WHERE rebalance_run_id IN (" in sql:
            for run_id in args:
                self.artifacts.pop(run_id, None)
            return _FakeCursor()
        if "DELETE FROM dpm_run_idempotency WHERE rebalance_run_id IN (" in sql:
            run_ids = set(args)
            self.idempotency = {
                key: value
                for key, value in self.idempotency.items()
                if value["rebalance_run_id"] not in run_ids
            }
            return _FakeCursor()
        if "DELETE FROM dpm_run_idempotency_history" in sql and "rebalance_run_id IN (" in sql:
            run_ids = set(args)
            self.idempotency_history = [
                row for row in self.idempotency_history if row["rebalance_run_id"] not in run_ids
            ]
            return _FakeCursor()
        if "DELETE FROM dpm_lineage_edges" in sql and "source_entity_id IN (" in sql:
            half = len(args) // 2
            source_entities = set(args[:half])
            target_entities = set(args[half:])
            self.lineage_edges = [
                row
                for row in self.lineage_edges
                if row["source_entity_id"] not in source_entities
                and row["target_entity_id"] not in target_entities
            ]
            return _FakeCursor()
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None

    def close(self):
        return None


def _build_repository(monkeypatch):
    fake_connection = _FakeConnection()
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        PostgresDpmRunRepository,
        "_connect",
        lambda self: fake_connection,
    )
    repository = PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    return repository, fake_connection


def test_postgres_repository_requires_dsn():
    try:
        PostgresDpmRunRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing DSN")


def test_postgres_repository_requires_driver(monkeypatch):
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)
    try:
        PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing psycopg driver")


def test_postgres_repository_save_and_get_run(monkeypatch):
    repository, connection = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = DpmRunRecord(
        rebalance_run_id="rr_pg_1",
        correlation_id="corr_pg_1",
        request_hash="sha256:req-pg-1",
        idempotency_key="idem_pg_1",
        portfolio_id="pf_pg_1",
        created_at=now,
        result_json={"rebalance_run_id": "rr_pg_1", "status": "READY"},
    )
    repository.save_run(run)
    stored = repository.get_run(rebalance_run_id="rr_pg_1")
    assert stored is not None
    assert stored.rebalance_run_id == "rr_pg_1"
    assert stored.result_json["status"] == "READY"
    assert repository.get_run(rebalance_run_id="rr_pg_missing") is None
    assert connection.commits >= 2

    by_correlation = repository.get_run_by_correlation(correlation_id="corr_pg_1")
    assert by_correlation is not None
    assert by_correlation.rebalance_run_id == "rr_pg_1"
    assert repository.get_run_by_correlation(correlation_id="corr_pg_missing") is None

    by_request_hash = repository.get_run_by_request_hash(request_hash="sha256:req-pg-1")
    assert by_request_hash is not None
    assert by_request_hash.rebalance_run_id == "rr_pg_1"
    assert repository.get_run_by_request_hash(request_hash="sha256:req-pg-missing") is None


def test_postgres_repository_save_and_get_artifact(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    artifact = {"artifact_id": "dra_pg_1", "evidence": {"hashes": {"artifact_hash": "sha256:1"}}}
    repository.save_run_artifact(rebalance_run_id="rr_pg_1", artifact_json=artifact)
    stored = repository.get_run_artifact(rebalance_run_id="rr_pg_1")
    assert stored == artifact
    assert repository.get_run_artifact(rebalance_run_id="rr_pg_missing") is None


def test_postgres_repository_save_and_get_idempotency_mapping(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    record = DpmRunIdempotencyRecord(
        idempotency_key="idem_pg_1",
        request_hash="sha256:req-pg-1",
        rebalance_run_id="rr_pg_1",
        created_at=now,
    )
    repository.save_idempotency_mapping(record)
    stored = repository.get_idempotency_mapping(idempotency_key="idem_pg_1")
    assert stored is not None
    assert stored.rebalance_run_id == "rr_pg_1"
    assert repository.get_idempotency_mapping(idempotency_key="idem_pg_missing") is None


def test_postgres_repository_append_and_list_idempotency_history(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    one = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_pg_history",
        rebalance_run_id="rr_pg_1",
        correlation_id="corr_pg_1",
        request_hash="sha256:req-pg-1",
        created_at=now,
    )
    two = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_pg_history",
        rebalance_run_id="rr_pg_2",
        correlation_id="corr_pg_2",
        request_hash="sha256:req-pg-2",
        created_at=now.replace(minute=1),
    )
    repository.append_idempotency_history(one)
    repository.append_idempotency_history(two)
    history = repository.list_idempotency_history(idempotency_key="idem_pg_history")
    assert [row.rebalance_run_id for row in history] == ["rr_pg_1", "rr_pg_2"]
    assert repository.list_idempotency_history(idempotency_key="idem_pg_history_missing") == []


def test_postgres_repository_create_update_get_operation(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operation = DpmAsyncOperationRecord(
        operation_id="dop_pg_1",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr_op_pg_1",
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    repository.create_operation(operation)
    stored = repository.get_operation(operation_id="dop_pg_1")
    assert stored is not None
    assert stored.status == "PENDING"

    operation.status = "SUCCEEDED"
    operation.started_at = now.replace(second=1)
    operation.finished_at = now.replace(second=2)
    operation.result_json = {"ok": True}
    operation.request_json = None
    repository.update_operation(operation)
    by_correlation = repository.get_operation_by_correlation(correlation_id="corr_op_pg_1")
    assert by_correlation is not None
    assert by_correlation.status == "SUCCEEDED"
    assert by_correlation.result_json == {"ok": True}
    assert repository.get_operation(operation_id="dop_pg_missing") is None
    assert repository.get_operation_by_correlation(correlation_id="corr_op_pg_missing") is None


def test_postgres_repository_list_operations_and_purge(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_1",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id="corr_op_pg_1",
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_op_pg_2",
            created_at=now.replace(minute=1),
            started_at=now.replace(minute=1, second=1),
            finished_at=now.replace(minute=1, second=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )
    rows, next_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=None,
    )
    assert [row.operation_id for row in rows] == ["dop_pg_2"]
    assert next_cursor == "dop_pg_2"

    rows_two, cursor_two = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=next_cursor,
    )
    assert [row.operation_id for row in rows_two] == ["dop_pg_1"]
    assert cursor_two is None

    filtered, _ = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status="SUCCEEDED",
        correlation_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.operation_id for row in filtered] == ["dop_pg_2"]

    removed = repository.purge_expired_operations(ttl_seconds=1, now=now.replace(minute=2))
    assert removed == 2


def test_postgres_repository_list_operations_filters_and_invalid_cursor(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_filter_1",
            operation_type="ANALYZE_SCENARIOS",
            status="FAILED",
            correlation_id="corr_op_pg_filter_1",
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json={"code": "E1"},
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_filter_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_op_pg_filter_2",
            created_at=now.replace(minute=1),
            started_at=now.replace(minute=1, second=1),
            finished_at=now.replace(minute=1, second=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )

    filtered, _ = repository.list_operations(
        created_from=now.replace(second=30),
        created_to=now.replace(minute=1, second=30),
        operation_type="ANALYZE_SCENARIOS",
        status="SUCCEEDED",
        correlation_id="corr_op_pg_filter_2",
        limit=10,
        cursor=None,
    )
    assert [row.operation_id for row in filtered] == ["dop_pg_filter_2"]

    invalid_cursor_rows, invalid_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status=None,
        correlation_id=None,
        limit=10,
        cursor="dop_pg_missing_cursor",
    )
    assert invalid_cursor_rows == []
    assert invalid_cursor is None


def test_postgres_repository_workflow_decisions(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    one = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_pg_1",
        run_id="rr_pg_1",
        action="REQUEST_CHANGES",
        reason_code="NEEDS_DETAIL",
        comment="Need more rationale",
        actor_id="reviewer_1",
        decided_at=now,
        correlation_id="corr_dwd_pg_1",
    )
    two = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_pg_2",
        run_id="rr_pg_1",
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_2",
        decided_at=now.replace(minute=1),
        correlation_id="corr_dwd_pg_2",
    )
    repository.append_workflow_decision(one)
    repository.append_workflow_decision(two)
    listed = repository.list_workflow_decisions(rebalance_run_id="rr_pg_1")
    assert [row.decision_id for row in listed] == ["dwd_pg_1", "dwd_pg_2"]

    filtered, _ = repository.list_workflow_decisions_filtered(
        rebalance_run_id="rr_pg_1",
        action="APPROVE",
        actor_id="reviewer_2",
        reason_code="REVIEW_APPROVED",
        decided_from=now.replace(second=30),
        decided_to=now.replace(minute=1, second=30),
        limit=10,
        cursor=None,
    )
    assert [row.decision_id for row in filtered] == ["dwd_pg_2"]

    page, next_cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=1,
        cursor=None,
    )
    assert [row.decision_id for row in page] == ["dwd_pg_2"]
    assert next_cursor == "dwd_pg_2"

    invalid_rows, invalid_cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=10,
        cursor="dwd_missing",
    )
    assert invalid_rows == []
    assert invalid_cursor is None


def test_postgres_repository_lineage_edges(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    edge = DpmLineageEdgeRecord(
        source_entity_id="corr_pg_1",
        edge_type="CORRELATION_TO_RUN",
        target_entity_id="rr_pg_1",
        created_at=now,
        metadata_json={"request_hash": "sha256:req-pg-1"},
    )
    repository.append_lineage_edge(edge)
    by_source = repository.list_lineage_edges(entity_id="corr_pg_1")
    assert len(by_source) == 1
    assert by_source[0].target_entity_id == "rr_pg_1"
    by_target = repository.list_lineage_edges(entity_id="rr_pg_1")
    assert len(by_target) == 1
    assert by_target[0].source_entity_id == "corr_pg_1"


def test_postgres_repository_supportability_summary(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_pg_summary_1",
            correlation_id="corr_pg_summary_1",
            request_hash="sha256:req-pg-summary-1",
            idempotency_key="idem_pg_summary_1",
            portfolio_id="pf_pg_summary",
            created_at=now,
            result_json={"rebalance_run_id": "rr_pg_summary_1", "status": "READY"},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_summary_1",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_dop_pg_summary_1",
            created_at=now.replace(minute=1),
            started_at=now.replace(minute=1, second=1),
            finished_at=now.replace(minute=1, second=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id="dwd_pg_summary_1",
            run_id="rr_pg_summary_1",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_pg_summary_1",
            decided_at=now.replace(minute=2),
            correlation_id="corr_dwd_pg_summary_1",
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id="corr_pg_summary_1",
            edge_type="CORRELATION_TO_RUN",
            target_entity_id="rr_pg_summary_1",
            created_at=now.replace(minute=3),
            metadata_json={},
        )
    )
    summary = repository.get_supportability_summary()
    assert summary.run_count == 1
    assert summary.operation_count == 1
    assert summary.operation_status_counts == {"SUCCEEDED": 1}
    assert summary.run_status_counts == {"READY": 1}
    assert summary.workflow_decision_count == 1
    assert summary.workflow_action_counts == {"APPROVE": 1}
    assert summary.workflow_reason_code_counts == {"REVIEW_APPROVED": 1}
    assert summary.lineage_edge_count == 1


def test_postgres_repository_purge_expired_runs(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    old_time = now.replace(day=15)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_pg_old",
            correlation_id="corr_pg_old",
            request_hash="sha256:req-pg-old",
            idempotency_key="idem_pg_old",
            portfolio_id="pf_pg",
            created_at=old_time,
            result_json={"rebalance_run_id": "rr_pg_old", "status": "READY"},
        )
    )
    repository.save_run_artifact(rebalance_run_id="rr_pg_old", artifact_json={"artifact_id": "dra"})
    repository.save_idempotency_mapping(
        DpmRunIdempotencyRecord(
            idempotency_key="idem_pg_old",
            request_hash="sha256:req-pg-old",
            rebalance_run_id="rr_pg_old",
            created_at=old_time,
        )
    )
    repository.append_idempotency_history(
        DpmRunIdempotencyHistoryRecord(
            idempotency_key="idem_pg_old",
            rebalance_run_id="rr_pg_old",
            correlation_id="corr_pg_old",
            request_hash="sha256:req-pg-old",
            created_at=old_time,
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id="dwd_pg_old",
            run_id="rr_pg_old",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_pg_old",
            decided_at=old_time,
            correlation_id="corr_dwd_pg_old",
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id="idem_pg_old",
            edge_type="IDEMPOTENCY_TO_RUN",
            target_entity_id="rr_pg_old",
            created_at=old_time,
            metadata_json={},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_pg_new",
            correlation_id="corr_pg_new",
            request_hash="sha256:req-pg-new",
            idempotency_key=None,
            portfolio_id="pf_pg",
            created_at=now,
            result_json={"rebalance_run_id": "rr_pg_new", "status": "READY"},
        )
    )
    removed = repository.purge_expired_runs(retention_days=2, now=now)
    assert removed == 1
    assert repository.get_run(rebalance_run_id="rr_pg_old") is None
    assert repository.get_run(rebalance_run_id="rr_pg_new") is not None

    removed_disabled = repository.purge_expired_runs(retention_days=0, now=now)
    assert removed_disabled == 0


def test_postgres_repository_list_runs_filters_and_cursor(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_pg_list_1",
            correlation_id="corr_pg_list_1",
            request_hash="sha256:req-pg-list-1",
            idempotency_key=None,
            portfolio_id="pf_pg_list",
            created_at=now,
            result_json={"rebalance_run_id": "rr_pg_list_1", "status": "READY"},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_pg_list_2",
            correlation_id="corr_pg_list_2",
            request_hash="sha256:req-pg-list-2",
            idempotency_key=None,
            portfolio_id="pf_pg_list",
            created_at=now.replace(minute=1),
            result_json={"rebalance_run_id": "rr_pg_list_2", "status": "BLOCKED"},
        )
    )
    rows, next_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in rows] == ["rr_pg_list_2"]
    assert next_cursor == "rr_pg_list_2"

    page_two, cursor_two = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=next_cursor,
    )
    assert [row.rebalance_run_id for row in page_two] == ["rr_pg_list_1"]
    assert cursor_two is None

    status_filtered, _ = repository.list_runs(
        created_from=None,
        created_to=None,
        status="READY",
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in status_filtered] == ["rr_pg_list_1"]

    hash_filtered, _ = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash="sha256:req-pg-list-1",
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in hash_filtered] == ["rr_pg_list_1"]

    portfolio_filtered, _ = repository.list_runs(
        created_from=now.replace(second=30),
        created_to=now.replace(minute=1, second=30),
        status=None,
        request_hash=None,
        portfolio_id="pf_pg_list",
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in portfolio_filtered] == ["rr_pg_list_2"]

    invalid_rows, invalid_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor="rr_pg_missing_cursor",
    )
    assert invalid_rows == []
    assert invalid_cursor is None


def test_postgres_repository_reports_unimplemented_for_other_methods(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    try:
        repository.unimplemented_operation  # type: ignore[attr-defined]
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError("Expected RuntimeError for unimplemented method access")


def test_postgres_json_dump_is_canonical():
    dumped = _json_dump({"b": 2, "a": 1})
    assert dumped == '{"a":1,"b":2}'


def test_postgres_connect_uses_imported_driver(monkeypatch):
    class _FakePsycopg:
        @staticmethod
        def connect(dsn, row_factory):
            return {"dsn": dsn, "row_factory": row_factory}

    monkeypatch.setattr(postgres_module, "_import_psycopg", lambda: (_FakePsycopg, "rf"))
    repository = object.__new__(PostgresDpmRunRepository)
    repository._dsn = "postgresql://user:pass@localhost:5432/dpm"
    connection = repository._connect()
    assert connection == {
        "dsn": "postgresql://user:pass@localhost:5432/dpm",
        "row_factory": "rf",
    }


def test_import_psycopg_helper(monkeypatch):
    fake_psycopg = ModuleType("psycopg")
    fake_rows = ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    fake_psycopg.rows = fake_rows

    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(__import__("sys").modules, "psycopg.rows", fake_rows)

    psycopg_module, dict_row = _import_psycopg()
    assert psycopg_module is fake_psycopg
    assert dict_row is fake_rows.dict_row
