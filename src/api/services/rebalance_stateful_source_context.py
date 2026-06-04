from collections.abc import Callable
from typing import Any, Optional, Protocol

from pydantic import ValidationError

from src.api.observability import (
    DPM_CORE_RESOLVER_OPERATION,
    record_core_resolver_call,
)
from src.api.request_models import BatchExecutionRequestEnvelope, RebalanceExecutionRequestEnvelope
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceCoreContextIncompleteError,
    DpmRebalanceCoreResolverUnavailableError,
    DpmRebalanceEnvelopeValidationError,
    DpmRebalanceStatefulInputDisabledError,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmResolvedSourceContext
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)


class CoreResolver(Protocol):
    def resolve_execution_context(
        self,
        *,
        stateful_input: Any,
        correlation_id: Optional[str],
    ) -> Any: ...


CoreResolverFactory = Callable[[], CoreResolver]


def resolve_stateful_source_context(
    *,
    envelope: RebalanceExecutionRequestEnvelope | BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
    stateful_enabled: bool,
    resolver_factory: CoreResolverFactory,
) -> DpmResolvedSourceContext:
    if envelope.stateful_input is None:
        raise DpmRebalanceEnvelopeValidationError("DPM_STATEFUL_INPUT_REQUIRED")
    if not stateful_enabled:
        raise DpmRebalanceStatefulInputDisabledError("DPM_STATEFUL_INPUT_DISABLED")

    try:
        resolver = resolver_factory()
        context = resolver.resolve_execution_context(
            stateful_input=envelope.stateful_input,
            correlation_id=correlation_id,
        )
    except CoreResolverUnavailableError as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="unavailable",
            supportability_state="unavailable",
            reason="resolver_unavailable",
        )
        raise DpmRebalanceCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE") from exc
    except ValidationError as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="incomplete",
            supportability_state="unknown",
            reason="invalid_response",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    except (DpmCoreContextIncompleteError, CoreResolverError) as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="incomplete",
            supportability_state="unknown",
            reason="context_incomplete",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    record_core_resolver_call(
        operation=DPM_CORE_RESOLVER_OPERATION,
        outcome="success",
        supportability_state=context.supportability.state.lower(),
        reason="degraded" if context.supportability.state == "DEGRADED" else "ready",
    )

    stateful_context_hash = hash_canonical_payload(context.model_dump(mode="json"))
    return DpmResolvedSourceContext(
        stateful_context_hash=stateful_context_hash,
        context=context,
    )


__all__ = ["CoreResolverFactory", "resolve_stateful_source_context"]
