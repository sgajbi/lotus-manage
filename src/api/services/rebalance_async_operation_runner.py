import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.api.services.rebalance_async_operation_completion import (
    complete_analyze_async_operation,
    fail_analyze_async_operation,
)
from src.api.services.rebalance_async_operation_payload import (
    resolve_analyze_async_execution_payload,
)
from src.core.models import BatchRebalanceResult
from src.core.rebalance_runs import DpmRunNotFoundError, DpmRunSupportService

ExecuteBatchAnalysisFn = Callable[..., BatchRebalanceResult]


def run_analyze_async_operation_from_store(
    *,
    operation_id: str,
    service: DpmRunSupportService,
    execution_mode: str,
    execute_batch_fn: ExecuteBatchAnalysisFn,
    current_logger: logging.Logger | Any,
) -> None:
    request_json, operation_correlation_id = service.prepare_analyze_operation_execution(
        operation_id=operation_id
    )
    try:
        payload = resolve_analyze_async_execution_payload(request_json)
        result = execute_batch_fn(
            request=payload.request,
            correlation_id=operation_correlation_id,
            request_policy_pack_id=payload.request_policy_pack_id,
            tenant_default_policy_pack_id=payload.tenant_default_policy_pack_id,
            tenant_id=payload.tenant_id,
            source_context=payload.source_context,
        )
        complete_analyze_async_operation(
            service=service,
            operation_id=operation_id,
            result=result,
            execution_mode=execution_mode,
        )
    except (DpmRunNotFoundError, ValidationError, RuntimeError, ValueError) as exc:
        fail_analyze_async_operation(
            service=service,
            operation_id=operation_id,
            execution_mode=execution_mode,
            exc=exc,
            current_logger=current_logger,
        )


__all__ = [
    "ExecuteBatchAnalysisFn",
    "run_analyze_async_operation_from_store",
]
