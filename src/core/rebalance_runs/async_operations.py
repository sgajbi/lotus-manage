from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.rebalance_runs.models import (
    DpmAsyncOperationListItemResponse,
    DpmAsyncOperationListResponse,
    DpmAsyncOperationRecord,
)


def build_analyze_operation(
    *,
    operation_id: str,
    correlation_id: str,
    request_json: dict[str, Any],
    created_at: datetime,
) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
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
    )


def is_operation_executable(operation: DpmAsyncOperationRecord) -> bool:
    return operation.status == "PENDING" and operation.request_json is not None


def mark_operation_running_record(
    operation: DpmAsyncOperationRecord,
    *,
    started_at: datetime,
) -> None:
    operation.status = "RUNNING"
    operation.started_at = started_at


def complete_operation_success_record(
    operation: DpmAsyncOperationRecord,
    *,
    result_json: dict[str, Any],
    finished_at: datetime,
) -> None:
    operation.status = "SUCCEEDED"
    operation.result_json = result_json
    operation.error_json = None
    operation.finished_at = finished_at


def complete_operation_failure_record(
    operation: DpmAsyncOperationRecord,
    *,
    code: str,
    message: str,
    finished_at: datetime,
) -> None:
    operation.status = "FAILED"
    operation.result_json = None
    operation.error_json = {"code": code, "message": message}
    operation.finished_at = finished_at


__all__ = [
    "build_analyze_operation",
    "complete_operation_failure_record",
    "complete_operation_success_record",
    "is_operation_executable",
    "mark_operation_running_record",
    "to_async_operation_list_item",
    "to_async_operation_list_response",
]
