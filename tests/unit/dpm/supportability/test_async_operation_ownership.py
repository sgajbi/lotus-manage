import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core.rebalance_runs.models import DpmAsyncOperationRecord
from src.core.rebalance_runs.repository import DpmRunRepositoryConflictError
from src.core.rebalance_runs.async_operations import is_operation_executable
from src.infrastructure.rebalance_runs.in_memory import InMemoryDpmRunRepository
from src.infrastructure.rebalance_runs.sqlite import SqliteDpmRunRepository


@pytest.fixture(params=["memory", "sqlite"])
def repository(request):
    if request.param == "memory":
        yield InMemoryDpmRunRepository()
        return
    with tempfile.TemporaryDirectory() as temporary_directory:
        yield SqliteDpmRunRepository(
            database_path=str(Path(temporary_directory) / "async-ownership.sqlite")
        )


def _pending(*, tenant_id: str, operation_id: str, correlation_id: str, created_at: datetime):
    return DpmAsyncOperationRecord(
        tenant_id=tenant_id,
        operation_id=operation_id,
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=correlation_id,
        created_at=created_at,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )


def test_tenant_scoped_correlation_and_reads_are_non_disclosing(repository) -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        _pending(
            tenant_id="tenant-a",
            operation_id="dop-a",
            correlation_id="shared-correlation",
            created_at=now,
        )
    )
    repository.create_operation(
        _pending(
            tenant_id="tenant-b",
            operation_id="dop-b",
            correlation_id="shared-correlation",
            created_at=now,
        )
    )

    assert repository.get_operation_for_tenant(tenant_id="tenant-a", operation_id="dop-b") is None
    assert (
        repository.get_operation_by_correlation_for_tenant(
            tenant_id="tenant-a", correlation_id="shared-correlation"
        ).operation_id
        == "dop-a"
    )
    rows, next_cursor = repository.list_operations_for_tenant(
        tenant_id="tenant-a",
        created_from=now - timedelta(seconds=1),
        created_to=now + timedelta(seconds=1),
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="shared-correlation",
        limit=10,
        cursor=None,
    )
    assert [row.operation_id for row in rows] == ["dop-a"]
    assert next_cursor is None


def test_missing_request_is_never_executable() -> None:
    operation = _pending(
        tenant_id="tenant-a",
        operation_id="dop-quarantined",
        correlation_id="corr-quarantined",
        created_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
    )
    operation.request_json = None

    assert is_operation_executable(operation) is False


def test_expired_lease_is_reclaimed_and_stale_owner_cannot_publish(repository) -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        _pending(
            tenant_id="tenant-a",
            operation_id="dop-lease",
            correlation_id="corr-lease",
            created_at=now - timedelta(days=2),
        )
    )
    first = repository.claim_operation_execution(
        tenant_id="tenant-a",
        operation_id="dop-lease",
        execution_token="opaque-first",
        claimed_at=now,
        lease_expires_at=now + timedelta(seconds=10),
    )
    assert first is not None
    assert first.execution_attempt == 1
    assert is_operation_executable(first, now=now + timedelta(seconds=5)) is False
    assert is_operation_executable(first, now=now + timedelta(seconds=10)) is True
    assert (
        repository.claim_operation_execution(
            tenant_id="tenant-a",
            operation_id="dop-lease",
            execution_token="opaque-competing",
            claimed_at=now + timedelta(seconds=5),
            lease_expires_at=now + timedelta(seconds=15),
        )
        is None
    )

    # General retention must not erase the recovery record while it is RUNNING.
    assert repository.purge_expired_operations(ttl_seconds=1, now=now + timedelta(seconds=20)) == 0
    second = repository.claim_operation_execution(
        tenant_id="tenant-a",
        operation_id="dop-lease",
        execution_token="opaque-second",
        claimed_at=now + timedelta(seconds=20),
        lease_expires_at=now + timedelta(seconds=30),
    )
    assert second is not None
    assert second.execution_attempt == 2
    assert (
        repository.publish_operation_success(
            tenant_id="tenant-a",
            operation_id="dop-lease",
            execution_token="opaque-first",
            result_json={"turnover": "20000.00"},
            finished_at=now + timedelta(seconds=21),
        )
        is False
    )
    assert (
        repository.publish_operation_success(
            tenant_id="tenant-a",
            operation_id="dop-lease",
            execution_token="opaque-second",
            result_json={"turnover": "20000.00"},
            finished_at=now + timedelta(seconds=22),
        )
        is True
    )

    stored = repository.get_operation_for_tenant(tenant_id="tenant-a", operation_id="dop-lease")
    assert stored is not None
    assert stored.status == "SUCCEEDED"
    assert stored.execution_attempt == 2
    assert stored.result_json == {"turnover": "20000.00"}


def test_current_owner_can_publish_failure_once(repository) -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        _pending(
            tenant_id="tenant-a",
            operation_id="dop-failure",
            correlation_id="corr-failure",
            created_at=now,
        )
    )
    claim = repository.claim_operation_execution(
        tenant_id="tenant-a",
        operation_id="dop-failure",
        execution_token="opaque-failure-owner",
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )
    assert claim is not None

    assert repository.publish_operation_failure(
        tenant_id="tenant-a",
        operation_id="dop-failure",
        execution_token="opaque-failure-owner",
        error_json={"code": "UPSTREAM_TIMEOUT", "message": "timed out"},
        finished_at=now + timedelta(seconds=1),
    )
    assert not repository.publish_operation_failure(
        tenant_id="tenant-a",
        operation_id="dop-failure",
        execution_token="opaque-failure-owner",
        error_json={"code": "REWRITE", "message": "must be fenced"},
        finished_at=now + timedelta(seconds=2),
    )
    stored = repository.get_operation_for_tenant(tenant_id="tenant-a", operation_id="dop-failure")
    assert stored is not None
    assert stored.status == "FAILED"
    assert stored.error_json == {"code": "UPSTREAM_TIMEOUT", "message": "timed out"}


def test_sqlite_upgrade_preserves_legacy_rows_as_quarantined(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE dpm_async_operations (
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
            INSERT INTO dpm_async_operations (
                operation_id, operation_type, status, correlation_id, created_at, request_json
            ) VALUES (
                'dop-legacy', 'ANALYZE_SCENARIOS', 'PENDING', 'corr-legacy',
                '2026-09-01T00:00:00+00:00', '{"legacy":true}'
            );
            """
        )

    repository = SqliteDpmRunRepository(database_path=str(database_path))
    legacy = repository.get_operation(operation_id="dop-legacy")
    assert legacy is not None
    assert legacy.tenant_id is None
    assert legacy.execution_attempt == 0
    assert (
        repository.get_operation_for_tenant(tenant_id="tenant-a", operation_id="dop-legacy") is None
    )

    # The obsolete global correlation constraint is gone after the rebuild.
    repository.create_operation(
        _pending(
            tenant_id="tenant-a",
            operation_id="dop-current-a",
            correlation_id="corr-shared-current",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    )
    repository.create_operation(
        _pending(
            tenant_id="tenant-b",
            operation_id="dop-current-b",
            correlation_id="corr-shared-current",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    )

    # Reopening a current-schema database is idempotent and preserves its indexes/data.
    reopened = SqliteDpmRunRepository(database_path=str(database_path))
    assert (
        reopened.get_operation_for_tenant(tenant_id="tenant-a", operation_id="dop-current-a")
        is not None
    )
    conflicting = _pending(
        tenant_id="tenant-a",
        operation_id="dop-current-a-conflict",
        correlation_id="corr-before-conflict",
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    reopened.create_operation(conflicting)
    conflicting.correlation_id = "corr-shared-current"
    with pytest.raises(
        DpmRunRepositoryConflictError,
        match="DPM_ASYNC_OPERATION_CORRELATION_CONFLICT",
    ):
        reopened.update_operation(conflicting)
