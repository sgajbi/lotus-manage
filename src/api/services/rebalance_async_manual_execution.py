from collections.abc import Callable

from src.api.observability import record_async_operation
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncOperationNotExecutableError,
    DpmRebalanceAsyncOperationNotFoundError,
)
from src.core.rebalance_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)

AnalyzeAsyncRunner = Callable[..., None]


def execute_analyze_async_operation_now(
    *,
    operation_id: str,
    service: DpmRunSupportService,
    runner: AnalyzeAsyncRunner,
) -> DpmAsyncOperationStatusResponse:
    try:
        runner(
            operation_id=operation_id,
            service=service,
            execution_mode="manual",
        )
    except DpmRunNotFoundError as exc:
        detail = str(exc)
        if detail == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE":
            record_async_operation(
                event="execute",
                execution_mode="manual",
                outcome="not_executable",
            )
            raise DpmRebalanceAsyncOperationNotExecutableError(detail) from exc
        record_async_operation(
            event="execute",
            execution_mode="manual",
            outcome="not_found",
        )
        raise DpmRebalanceAsyncOperationNotFoundError(detail) from exc
    return service.get_async_operation(operation_id=operation_id)


__all__ = ["AnalyzeAsyncRunner", "execute_analyze_async_operation_now"]
