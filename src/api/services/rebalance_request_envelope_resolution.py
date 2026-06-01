from collections.abc import Callable
from typing import Any, Optional

from pydantic import ValidationError

from src.api.request_models import (
    BatchExecutionRequestEnvelope,
    RebalanceExecutionRequestEnvelope,
    RebalanceRequest,
)
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceCoreContextIncompleteError,
    DpmRebalanceEnvelopeValidationError,
)
from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmResolvedSourceContext
from src.core.models import BatchRebalanceRequest

StatefulContextResolver = Callable[..., DpmResolvedSourceContext]
RebalanceRequestBuilder = Callable[..., Any]
BatchRequestBuilder = Callable[..., BatchRebalanceRequest]


def resolve_rebalance_request_envelope(
    *,
    envelope: RebalanceExecutionRequestEnvelope,
    correlation_id: Optional[str],
    stateful_context_resolver: StatefulContextResolver,
    rebalance_request_builder: RebalanceRequestBuilder,
) -> tuple[RebalanceRequest, Optional[DpmResolvedSourceContext]]:
    if envelope.input_mode == "stateless":
        if envelope.stateless_input is None:
            raise DpmRebalanceEnvelopeValidationError("DPM_STATELESS_INPUT_REQUIRED")
        return envelope.stateless_input, None

    source_context = stateful_context_resolver(
        envelope=envelope,
        correlation_id=correlation_id,
    )
    try:
        resolved = rebalance_request_builder(
            context=source_context.context,
            options_override=envelope.options_override,
        )
    except (DpmCoreContextIncompleteError, ValidationError) as exc:
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    return RebalanceRequest.model_validate(resolved.model_dump(mode="python")), source_context


def resolve_batch_request_envelope(
    *,
    envelope: BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
    stateful_context_resolver: StatefulContextResolver,
    batch_request_builder: BatchRequestBuilder,
) -> tuple[BatchRebalanceRequest, Optional[DpmResolvedSourceContext]]:
    if envelope.input_mode == "stateless":
        if envelope.stateless_input is None:
            raise DpmRebalanceEnvelopeValidationError("DPM_STATELESS_INPUT_REQUIRED")
        return envelope.stateless_input, None

    source_context = stateful_context_resolver(
        envelope=envelope,
        correlation_id=correlation_id,
    )
    try:
        request = batch_request_builder(
            context=source_context.context,
            scenarios=envelope.scenarios,
        )
    except (DpmCoreContextIncompleteError, ValidationError) as exc:
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    return request, source_context


__all__ = [
    "BatchRequestBuilder",
    "RebalanceRequestBuilder",
    "StatefulContextResolver",
    "resolve_batch_request_envelope",
    "resolve_rebalance_request_envelope",
]
