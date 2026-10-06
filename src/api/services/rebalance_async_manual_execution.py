from collections.abc import Callable

from src.observability.metrics import record_async_operation
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncOperationConflictError,
    DpmRebalanceAsyncOperationNotExecutableError,
    DpmRebalanceAsyncOperationNotFoundError,
)
from src.core.rebalance_runs import (
    DpmAsyncOperationConflictError,
    DpmAsyncOperationStatusResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)

AnalyzeAsyncRunner = Callable[..., None]


def execute_analyze_async_operation_now(
    *,
    operation_id: str,
    tenant_id: str,
    service: DpmRunSupportService,
    runner: AnalyzeAsyncRunner,
) -> DpmAsyncOperationStatusResponse:
    try:
        runner(
            operation_id=operation_id,
            tenant_id=tenant_id,
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
    except DpmAsyncOperationConflictError as exc:
        record_async_operation(
            event="execute",
            execution_mode="manual",
            outcome="conflict",
        )
        raise DpmRebalanceAsyncOperationConflictError(str(exc)) from exc
    return service.get_async_operation(tenant_id=tenant_id, operation_id=operation_id)


__all__ = ["AnalyzeAsyncRunner", "execute_analyze_async_operation_now"]
