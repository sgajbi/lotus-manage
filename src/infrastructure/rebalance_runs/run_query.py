from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.rebalance_runs.models import DpmRunRecord


@dataclass(frozen=True)
class RunFilterQuery:
    where_sql: str
    args: tuple[str, ...]


def build_run_filter_query(
    *,
    placeholder: str,
    status_expression: str,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    status: Optional[str],
    request_hash: Optional[str],
    portfolio_id: Optional[str],
    cursor: Optional[str],
) -> RunFilterQuery:
    scalar_filters = _run_scalar_filter_query(
        placeholder=placeholder,
        status_expression=status_expression,
        created_from=created_from,
        created_to=created_to,
        status=status,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
    )
    cursor_filter = _run_cursor_filter_query(
        placeholder=placeholder,
        cursor=cursor,
    )
    where_clauses = [*scalar_filters.where_clauses, *cursor_filter.where_clauses]
    args = [*scalar_filters.args, *cursor_filter.args]
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return RunFilterQuery(where_sql=where_sql, args=tuple(args))


@dataclass(frozen=True)
class _RunFilterParts:
    where_clauses: tuple[str, ...]
    args: tuple[str, ...]


def _run_scalar_filter_query(
    *,
    placeholder: str,
    status_expression: str,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    status: Optional[str],
    request_hash: Optional[str],
    portfolio_id: Optional[str],
) -> _RunFilterParts:
    where_clauses: list[str] = []
    args: list[str] = []
    for clause, value in (
        (f"created_at >= {placeholder}", created_from.isoformat() if created_from else None),
        (f"created_at <= {placeholder}", created_to.isoformat() if created_to else None),
        (f"portfolio_id = {placeholder}", portfolio_id),
        (f"request_hash = {placeholder}", request_hash),
        (f"{status_expression} = {placeholder}", status),
    ):
        if value is not None:
            where_clauses.append(clause)
            args.append(value)
    return _RunFilterParts(where_clauses=tuple(where_clauses), args=tuple(args))


def _run_cursor_filter_query(
    *,
    placeholder: str,
    cursor: Optional[str],
) -> _RunFilterParts:
    if cursor is not None:
        return _RunFilterParts(
            where_clauses=(
                f"""
            (
                created_at < (SELECT created_at FROM dpm_runs WHERE rebalance_run_id = {placeholder})
                OR (
                    created_at = (SELECT created_at FROM dpm_runs WHERE rebalance_run_id = {placeholder})
                    AND rebalance_run_id < {placeholder}
                )
            )
            """,
            ),
            args=(cursor, cursor, cursor),
        )
    return _RunFilterParts(where_clauses=(), args=())


def run_page(
    runs: Sequence[DpmRunRecord],
    *,
    limit: int,
) -> tuple[list[DpmRunRecord], Optional[str]]:
    run_list = list(runs)
    page = run_list[:limit]
    next_cursor = page[-1].rebalance_run_id if len(run_list) > limit else None
    return page, next_cursor
