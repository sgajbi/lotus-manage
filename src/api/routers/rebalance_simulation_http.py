from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncManualExecutionDisabledError,
    DpmRebalanceAsyncOperationConflictError,
    DpmRebalanceAsyncOperationError,
    DpmRebalanceAsyncOperationNotExecutableError,
    DpmRebalanceAsyncOperationNotFoundError,
    DpmRebalanceAsyncOperationSupportUnavailableError,
    DpmRebalanceAsyncOperationsDisabledError,
    DpmRebalanceCoreContextIncompleteError,
    DpmRebalanceCoreResolverUnavailableError,
    DpmRebalanceEnvelopeError,
    DpmRebalanceEnvelopeValidationError,
    DpmRebalanceIdempotencyConflictError,
    DpmRebalanceIdempotencyStoreInconsistentError,
    DpmRebalanceIdempotencyStoreWriteFailedError,
    DpmRebalanceSimulationError,
    DpmRebalanceSupportabilityStoreUnavailableError,
    DpmRebalanceStatefulInputDisabledError,
)


def rebalance_envelope_http_exception(exc: DpmRebalanceEnvelopeError) -> HTTPException:
    if isinstance(exc, DpmRebalanceEnvelopeValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.detail)
    if isinstance(exc, DpmRebalanceStatefulInputDisabledError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, DpmRebalanceCoreResolverUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.detail)
    if isinstance(exc, DpmRebalanceCoreContextIncompleteError):
        return HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=exc.detail)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=type(exc).__name__,
    )


def rebalance_simulation_http_exception(exc: DpmRebalanceSimulationError) -> HTTPException:
    if isinstance(exc, DpmRebalanceIdempotencyConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(
        exc,
        (
            DpmRebalanceIdempotencyStoreInconsistentError,
            DpmRebalanceIdempotencyStoreWriteFailedError,
            DpmRebalanceSupportabilityStoreUnavailableError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.detail)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=type(exc).__name__,
    )


def rebalance_async_operation_http_exception(
    exc: DpmRebalanceAsyncOperationError,
) -> HTTPException:
    if isinstance(
        exc,
        (
            DpmRebalanceAsyncOperationsDisabledError,
            DpmRebalanceAsyncManualExecutionDisabledError,
            DpmRebalanceAsyncOperationNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    if isinstance(
        exc,
        (
            DpmRebalanceAsyncOperationConflictError,
            DpmRebalanceAsyncOperationNotExecutableError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, DpmRebalanceAsyncOperationSupportUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.detail)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=type(exc).__name__,
    )
