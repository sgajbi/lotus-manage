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


@dataclass(frozen=True)
class _OperationPredicate:
    clause: str
    value: str


def build_operation_filter_query(
    *,
    placeholder: str,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    operation_type: Optional[str],
    status: Optional[str],
    correlation_id: Optional[str],
) -> OperationFilterQuery:
    predicates = _operation_filter_predicates(
        placeholder=placeholder,
        created_from=created_from,
        created_to=created_to,
        operation_type=operation_type,
        status=status,
        correlation_id=correlation_id,
    )
    return OperationFilterQuery(
        where_sql=_operation_where_sql(predicates),
        args=tuple(predicate.value for predicate in predicates),
    )


def _operation_filter_predicates(
    *,
    placeholder: str,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    operation_type: Optional[str],
    status: Optional[str],
    correlation_id: Optional[str],
) -> list[_OperationPredicate]:
    return [
        predicate
        for predicate in [
            _optional_datetime_predicate(
                f"created_at >= {placeholder}",
                created_from,
            ),
            _optional_datetime_predicate(
                f"created_at <= {placeholder}",
                created_to,
            ),
            _optional_text_predicate(f"operation_type = {placeholder}", operation_type),
            _optional_text_predicate(f"status = {placeholder}", status),
            _optional_text_predicate(f"correlation_id = {placeholder}", correlation_id),
        ]
        if predicate is not None
    ]


def _optional_datetime_predicate(
    clause: str, value: Optional[datetime]
) -> _OperationPredicate | None:
    if value is None:
        return None
    return _OperationPredicate(clause=clause, value=value.isoformat())


def _optional_text_predicate(clause: str, value: Optional[str]) -> _OperationPredicate | None:
    if value is None:
        return None
    return _OperationPredicate(clause=clause, value=value)


def _operation_where_sql(predicates: list[_OperationPredicate]) -> str:
    if not predicates:
        return ""
    return f"WHERE {' AND '.join(predicate.clause for predicate in predicates)}"


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
