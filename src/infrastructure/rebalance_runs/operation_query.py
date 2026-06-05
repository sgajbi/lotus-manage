from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.rebalance_runs.models import DpmAsyncOperationRecord


@dataclass(frozen=True)
class OperationFilterQuery:
    where_sql: str
    args: tuple[str, ...]


def build_operation_filter_query(
    *,
    placeholder: str,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    operation_type: Optional[str],
    status: Optional[str],
    correlation_id: Optional[str],
) -> OperationFilterQuery:
    where_clauses: list[str] = []
    args: list[str] = []
    for clause, value in [
        (f"created_at >= {placeholder}", created_from.isoformat() if created_from else None),
        (f"created_at <= {placeholder}", created_to.isoformat() if created_to else None),
        (f"operation_type = {placeholder}", operation_type),
        (f"status = {placeholder}", status),
        (f"correlation_id = {placeholder}", correlation_id),
    ]:
        if value is not None:
            where_clauses.append(clause)
            args.append(value)
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return OperationFilterQuery(where_sql=where_sql, args=tuple(args))


def operation_page(
    operations: Sequence[DpmAsyncOperationRecord],
    *,
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmAsyncOperationRecord], Optional[str]]:
    page_source = list(operations)
    if cursor is not None:
        cursor_index = next(
            (
                index
                for index, operation in enumerate(page_source)
                if operation.operation_id == cursor
            ),
            None,
        )
        if cursor_index is None:
            return [], None
        page_source = page_source[cursor_index + 1 :]
    page = page_source[:limit]
    next_cursor = page[-1].operation_id if len(page_source) > limit else None
    return page, next_cursor
