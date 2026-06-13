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
    stateful_input = _stateful_source_input(
        envelope=envelope,
        stateful_enabled=stateful_enabled,
    )
    context = _resolve_core_execution_context(
        stateful_input=stateful_input,
        correlation_id=correlation_id,
        resolver_factory=resolver_factory,
    )
    _record_core_resolver_success(context=context)

    stateful_context_hash = hash_canonical_payload(context.model_dump(mode="json"))
    return DpmResolvedSourceContext(
        stateful_context_hash=stateful_context_hash,
        context=context,
    )


def _stateful_source_input(
    *,
    envelope: RebalanceExecutionRequestEnvelope | BatchExecutionRequestEnvelope,
    stateful_enabled: bool,
) -> Any:
    if envelope.stateful_input is None:
        raise DpmRebalanceEnvelopeValidationError("DPM_STATEFUL_INPUT_REQUIRED")
    if not stateful_enabled:
        raise DpmRebalanceStatefulInputDisabledError("DPM_STATEFUL_INPUT_DISABLED")
    return envelope.stateful_input


def _resolve_core_execution_context(
    *,
    stateful_input: Any,
    correlation_id: Optional[str],
    resolver_factory: CoreResolverFactory,
) -> Any:
    try:
        resolver = resolver_factory()
        return resolver.resolve_execution_context(
            stateful_input=stateful_input,
            correlation_id=correlation_id,
        )
    except CoreResolverUnavailableError as exc:
        _record_core_resolver_failure(
            outcome="unavailable",
            supportability_state="unavailable",
            reason="resolver_unavailable",
        )
        raise DpmRebalanceCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE") from exc
    except ValidationError as exc:
        _record_core_resolver_failure(
            outcome="incomplete",
            supportability_state="unknown",
            reason="invalid_response",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    except (DpmCoreContextIncompleteError, CoreResolverError) as exc:
        _record_core_resolver_failure(
            outcome="incomplete",
            supportability_state="unknown",
            reason="context_incomplete",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc


def _record_core_resolver_failure(
    *,
    outcome: str,
    supportability_state: str,
    reason: str,
) -> None:
    record_core_resolver_call(
        operation=DPM_CORE_RESOLVER_OPERATION,
        outcome=outcome,
        supportability_state=supportability_state,
        reason=reason,
    )


def _record_core_resolver_success(*, context: Any) -> None:
    record_core_resolver_call(
        operation=DPM_CORE_RESOLVER_OPERATION,
        outcome="success",
        supportability_state=_core_resolver_supportability_state(context=context),
        reason=_core_resolver_success_reason(context=context),
    )


def _core_resolver_supportability_state(*, context: Any) -> str:
    return str(context.supportability.state).lower()


def _core_resolver_success_reason(*, context: Any) -> str:
    return "degraded" if context.supportability.state == "DEGRADED" else "ready"


__all__ = ["CoreResolverFactory", "resolve_stateful_source_context"]
