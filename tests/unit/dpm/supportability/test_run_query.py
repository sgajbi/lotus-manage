from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.rebalance_runs.models import DpmRunRecord
from src.infrastructure.rebalance_runs.run_query import (
    _run_cursor_filter_query,
    _run_scalar_filter_query,
    build_run_filter_query,
    run_page,
)


def _run(run_id: str, created_at: datetime) -> DpmRunRecord:
    return DpmRunRecord(
        rebalance_run_id=run_id,
        correlation_id=f"corr-{run_id}",
        request_hash=f"sha256:{run_id}",
        idempotency_key=None,
        portfolio_id="pf-run-query",
        created_at=created_at,
        result_json={"rebalance_run_id": run_id, "status": "READY"},
    )


def test_build_run_filter_query_uses_backend_placeholder_and_ordered_args() -> None:
    created_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    created_to = created_from + timedelta(hours=1)

    query = build_run_filter_query(
        placeholder="%s",
        status_expression="result_json::jsonb ->> 'status'",
        created_from=created_from,
        created_to=created_to,
        status="READY",
        request_hash="sha256:req-run-query",
        portfolio_id="pf-run-query",
        cursor="rr-query-cursor",
    )

    assert query.where_sql.startswith(
        "WHERE created_at >= %s AND created_at <= %s AND portfolio_id = %s "
        "AND request_hash = %s AND result_json::jsonb ->> 'status' = %s AND"
    )
    assert "rebalance_run_id = %s" in query.where_sql
    assert "rebalance_run_id < %s" in query.where_sql
    assert query.args == (
        "2026-02-20T12:00:00+00:00",
        "2026-02-20T13:00:00+00:00",
        "pf-run-query",
        "sha256:req-run-query",
        "READY",
        "rr-query-cursor",
        "rr-query-cursor",
        "rr-query-cursor",
    )


def test_build_run_filter_query_returns_empty_filter_without_constraints() -> None:
    query = build_run_filter_query(
        placeholder="?",
        status_expression="json_extract(result_json, '$.status')",
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        cursor=None,
    )

    assert query.where_sql == ""
    assert query.args == ()


def test_run_filter_parts_preserve_scalar_and_cursor_argument_order() -> None:
    created_from = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    created_to = created_from + timedelta(hours=1)

    scalar = _run_scalar_filter_query(
        placeholder="%s",
        status_expression="result_json::jsonb ->> 'status'",
        created_from=created_from,
        created_to=created_to,
        status="READY",
        request_hash="sha256:req-run-query",
        portfolio_id="pf-run-query",
    )
    cursor = _run_cursor_filter_query(
        placeholder="%s",
        cursor="rr-query-cursor",
    )

    assert scalar.where_clauses == (
        "created_at >= %s",
        "created_at <= %s",
        "portfolio_id = %s",
        "request_hash = %s",
        "result_json::jsonb ->> 'status' = %s",
    )
    assert scalar.args == (
        "2026-02-20T12:00:00+00:00",
        "2026-02-20T13:00:00+00:00",
        "pf-run-query",
        "sha256:req-run-query",
        "READY",
    )
    assert cursor.args == ("rr-query-cursor", "rr-query-cursor", "rr-query-cursor")
    assert "rebalance_run_id < %s" in cursor.where_clauses[0]


def test_run_page_returns_next_cursor_for_overfetched_results() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    runs = [
        _run("rr-query-3", now + timedelta(minutes=2)),
        _run("rr-query-2", now + timedelta(minutes=1)),
        _run("rr-query-1", now),
    ]

    page, cursor = run_page(runs, limit=2)

    assert [run.rebalance_run_id for run in page] == ["rr-query-3", "rr-query-2"]
    assert cursor == "rr-query-2"


def test_run_page_returns_no_cursor_when_results_fit_limit() -> None:
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)

    page, cursor = run_page([_run("rr-query-1", now)], limit=2)

    assert [run.rebalance_run_id for run in page] == ["rr-query-1"]
    assert cursor is None
