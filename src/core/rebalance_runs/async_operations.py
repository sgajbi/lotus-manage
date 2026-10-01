from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.rebalance_runs.models import (
    DpmAsyncOperationListItemResponse,
    DpmAsyncOperationListResponse,
    DpmAsyncOperationRecord,
)


def build_analyze_operation(
    *,
    tenant_id: str,
    operation_id: str,
    correlation_id: str,
    request_json: dict[str, Any],
    created_at: datetime,
) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
        tenant_id=tenant_id,
        operation_id=operation_id,
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=correlation_id,
        created_at=created_at,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json=request_json,
    )


def to_async_operation_list_response(
    *,
    operations: list[DpmAsyncOperationRecord],
    next_cursor: str | None,
) -> DpmAsyncOperationListResponse:
    return DpmAsyncOperationListResponse(
        items=[to_async_operation_list_item(operation) for operation in operations],
        next_cursor=next_cursor,
    )


def to_async_operation_list_item(
    operation: DpmAsyncOperationRecord,
) -> DpmAsyncOperationListItemResponse:
    return DpmAsyncOperationListItemResponse(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        correlation_id=operation.correlation_id,
        is_executable=is_operation_executable(operation),
        created_at=operation.created_at.isoformat(),
        started_at=operation.started_at.isoformat() if operation.started_at is not None else None,
        finished_at=(
            operation.finished_at.isoformat() if operation.finished_at is not None else None
        ),
        execution_attempt=operation.execution_attempt,
        execution_lease_expires_at=(
            operation.execution_lease_expires_at.isoformat()
            if operation.execution_lease_expires_at is not None
            else None
        ),
    )


def is_operation_executable(
    operation: DpmAsyncOperationRecord,
    *,
    now: datetime | None = None,
) -> bool:
    if operation.request_json is None:
        return False
    if operation.status == "PENDING":
        return True
    current = now or datetime.now(timezone.utc)
    return (
        operation.status == "RUNNING"
        and operation.execution_lease_expires_at is not None
        and operation.execution_lease_expires_at <= current
    )


__all__ = [
    "build_analyze_operation",
    "is_operation_executable",
    "to_async_operation_list_item",
    "to_async_operation_list_response",
]
