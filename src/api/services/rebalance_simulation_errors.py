from __future__ import annotations


class DpmRebalanceEnvelopeError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DpmRebalanceEnvelopeValidationError(DpmRebalanceEnvelopeError):
    pass


class DpmRebalanceStatefulInputDisabledError(DpmRebalanceEnvelopeError):
    pass


class DpmRebalanceCoreResolverUnavailableError(DpmRebalanceEnvelopeError):
    pass


class DpmRebalanceCoreContextIncompleteError(DpmRebalanceEnvelopeError):
    pass


class DpmRebalanceSimulationError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DpmRebalanceIdempotencyConflictError(DpmRebalanceSimulationError):
    pass


class DpmRebalanceIdempotencyStoreInconsistentError(DpmRebalanceSimulationError):
    pass


class DpmRebalanceIdempotencyStoreWriteFailedError(DpmRebalanceSimulationError):
    pass


class DpmRebalanceSupportabilityStoreUnavailableError(DpmRebalanceSimulationError):
    pass


class DpmRebalanceAsyncOperationError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DpmRebalanceAsyncOperationsDisabledError(DpmRebalanceAsyncOperationError):
    pass


class DpmRebalanceAsyncOperationConflictError(DpmRebalanceAsyncOperationError):
    pass


class DpmRebalanceAsyncManualExecutionDisabledError(DpmRebalanceAsyncOperationError):
    pass


class DpmRebalanceAsyncOperationNotExecutableError(DpmRebalanceAsyncOperationError):
    pass


class DpmRebalanceAsyncOperationNotFoundError(DpmRebalanceAsyncOperationError):
    pass


class DpmRebalanceAsyncOperationSupportUnavailableError(DpmRebalanceAsyncOperationError):
    pass
