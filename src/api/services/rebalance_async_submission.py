from typing import Optional

from src.api.observability import record_async_operation, record_execution_call
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncOperationConflictError,
)
from src.api.services.rebalance_source_lineage import source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.rebalance_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationConflictError,
    DpmRunSupportService,
)


def submit_analyze_async_request(
    *,
    service: DpmRunSupportService,
    correlation_id: Optional[str],
    request_json: dict[str, object],
    source_context: Optional[DpmResolvedSourceContext],
    execution_mode_label: str,
) -> DpmAsyncAcceptedResponse:
    try:
        accepted = service.submit_analyze_async(
            correlation_id=correlation_id,
            request_json=request_json,
        )
    except DpmAsyncOperationConflictError as exc:
        record_async_operation(
            event="submit",
            execution_mode=execution_mode_label,
            outcome="conflict",
        )
        record_execution_call(
            operation="analyze_async",
            input_mode=source_input_mode(source_context),
            outcome="conflict",
            result_status="failed",
        )
        raise DpmRebalanceAsyncOperationConflictError(str(exc)) from exc

    record_async_operation(
        event="submit",
        execution_mode=execution_mode_label,
        outcome="accepted",
    )
    record_execution_call(
        operation="analyze_async",
        input_mode=source_input_mode(source_context),
        outcome="accepted",
        result_status="accepted",
    )
    return accepted


__all__ = ["submit_analyze_async_request"]
