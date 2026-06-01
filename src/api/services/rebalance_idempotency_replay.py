from collections.abc import Callable
from typing import Optional

from src.api.observability import record_execution_call
from src.api.services.rebalance_run_support_service import (
    DpmRunSupportServiceUnavailableError,
)
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceIdempotencyConflictError,
    DpmRebalanceIdempotencyStoreInconsistentError,
    DpmRebalanceSupportabilityStoreUnavailableError,
)
from src.api.services.rebalance_source_lineage import source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import RebalanceResult
from src.core.rebalance_runs import DpmRunNotFoundError, DpmRunSupportService


def _execution_status_label(status_value: str) -> str:
    return status_value.lower()


def resolve_idempotency_replay(
    *,
    idempotency_key: str,
    request_hash: str,
    source_context: Optional[DpmResolvedSourceContext],
    support_service_factory: Callable[[], DpmRunSupportService],
) -> RebalanceResult | None:
    try:
        support_service = support_service_factory()
    except DpmRunSupportServiceUnavailableError as exc:
        raise DpmRebalanceSupportabilityStoreUnavailableError(exc.detail) from exc

    try:
        existing = support_service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except DpmRunNotFoundError:
        return None

    if existing.request_hash != request_hash:
        record_execution_call(
            operation="simulate",
            input_mode=source_input_mode(source_context),
            outcome="conflict",
            result_status="failed",
        )
        raise DpmRebalanceIdempotencyConflictError(
            "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
        )

    try:
        replay_run = support_service.get_run(rebalance_run_id=existing.rebalance_run_id)
    except DpmRunNotFoundError as exc:
        record_execution_call(
            operation="simulate",
            input_mode=source_input_mode(source_context),
            outcome="error",
            result_status="failed",
        )
        raise DpmRebalanceIdempotencyStoreInconsistentError(
            "DPM_IDEMPOTENCY_STORE_INCONSISTENT"
        ) from exc

    replay_result = RebalanceResult.model_validate(replay_run.result)
    record_execution_call(
        operation="simulate",
        input_mode=source_input_mode(source_context),
        outcome="replayed",
        result_status=_execution_status_label(replay_result.status),
    )
    return replay_result


__all__ = ["resolve_idempotency_replay"]
