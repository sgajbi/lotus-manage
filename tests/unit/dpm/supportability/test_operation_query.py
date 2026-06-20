from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.rebalance_runs.models import DpmAsyncOperationRecord
from src.infrastructure.rebalance_runs.operation_query import (
    _operation_filter_predicates,
    _operation_where_sql,
    _optional_datetime_predicate,
    build_operation_filter_query,
    operation_page,
)


def _operation(
    operation_id: str,
    created_at: datetime,
) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=f"corr-{operation_id}",
        created_at=created_at,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )


def test_build_operation_filter_query_uses_backend_placeholder_and_ordered_args() -> None:
    created_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    created_to = created_from + timedelta(hours=1)

    query = build_operation_filter_query(
        placeholder="%s",
        created_from=created_from,
        created_to=created_to,
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr-dop-001",
    )

    assert query.where_sql == (
        "WHERE created_at >= %s AND created_at <= %s AND operation_type = %s "
        "AND status = %s AND correlation_id = %s"
    )
    assert query.args == (
        "2026-02-20T12:00:00+00:00",
        "2026-02-20T13:00:00+00:00",
        "ANALYZE_SCENARIOS",
        "PENDING",
        "corr-dop-001",
    )


def test_build_operation_filter_query_returns_empty_filter_without_constraints() -> None:
    query = build_operation_filter_query(
        placeholder="?",
        created_from=None,
        created_to=None,
        operation_type=None,
        status=None,
        correlation_id=None,
    )

    assert query.where_sql == ""
    assert query.args == ()


def test_operation_filter_predicate_helpers_convert_dates_and_render_where_sql() -> None:
    created_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    predicate = _optional_datetime_predicate("created_at >= ?", created_from)
    predicates = _operation_filter_predicates(
        placeholder="?",
        created_from=created_from,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
    )

    assert predicate is not None
    assert predicate.value == "2026-02-20T12:00:00+00:00"
    assert [item.clause for item in predicates] == [
        "created_at >= ?",
        "operation_type = ?",
    ]
    assert _operation_where_sql(predicates) == "WHERE created_at >= ? AND operation_type = ?"
    assert _operation_where_sql([]) == ""


def test_operation_page_returns_next_cursor_for_truncated_results() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operations = [
        _operation("dop-003", now + timedelta(minutes=2)),
        _operation("dop-002", now + timedelta(minutes=1)),
        _operation("dop-001", now),
    ]

    page, cursor = operation_page(operations, limit=2, cursor=None)

    assert [operation.operation_id for operation in page] == ["dop-003", "dop-002"]
    assert cursor == "dop-002"


def test_operation_page_starts_after_cursor_and_rejects_unknown_cursor() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operations = [
        _operation("dop-003", now + timedelta(minutes=2)),
        _operation("dop-002", now + timedelta(minutes=1)),
        _operation("dop-001", now),
    ]

    page, cursor = operation_page(operations, limit=2, cursor="dop-003")
    missing_page, missing_cursor = operation_page(operations, limit=2, cursor="dop-missing")

    assert [operation.operation_id for operation in page] == ["dop-002", "dop-001"]
    assert cursor is None
    assert missing_page == []
    assert missing_cursor is None
