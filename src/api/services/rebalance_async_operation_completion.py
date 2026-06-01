import logging
from typing import Any

from src.api.observability import record_async_operation
from src.core.models import BatchRebalanceResult
from src.core.rebalance_runs import DpmRunSupportService


def complete_analyze_async_operation(
    *,
    service: DpmRunSupportService,
    operation_id: str,
    result: BatchRebalanceResult,
    execution_mode: str,
) -> None:
    service.complete_operation_success(
        operation_id=operation_id,
        result_json=result.model_dump(mode="json"),
    )
    record_async_operation(
        event="execute",
        execution_mode=execution_mode,
        outcome="succeeded",
    )


def fail_analyze_async_operation(
    *,
    service: DpmRunSupportService,
    operation_id: str,
    execution_mode: str,
    exc: Exception,
    current_logger: logging.Logger | Any,
) -> None:
    current_logger.exception("Asynchronous batch analysis failed")
    service.complete_operation_failure(
        operation_id=operation_id,
        code=type(exc).__name__,
        message=str(exc),
    )
    record_async_operation(
        event="execute",
        execution_mode=execution_mode,
        outcome="failed",
    )


__all__ = [
    "complete_analyze_async_operation",
    "fail_analyze_async_operation",
]
