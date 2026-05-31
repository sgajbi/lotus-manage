import logging
from collections.abc import Callable
from typing import Any, Optional

from src.api.observability import record_execution_call
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceIdempotencyStoreWriteFailedError,
)
from src.api.services.rebalance_source_lineage import source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import RebalanceResult


def record_simulation_supportability(
    *,
    result: RebalanceResult,
    request_hash: str,
    portfolio_id: str,
    idempotency_key: str,
    replay_enabled: bool,
    source_context: Optional[DpmResolvedSourceContext],
    record_for_support: Callable[..., object],
    current_logger: logging.Logger | Any,
) -> None:
    try:
        record_for_support(
            result=result,
            request_hash=request_hash,
            portfolio_id=portfolio_id,
            idempotency_key=idempotency_key,
        )
    except (RuntimeError, ValueError) as exc:
        if replay_enabled:
            record_execution_call(
                operation="simulate",
                input_mode=source_input_mode(source_context),
                outcome="error",
                result_status="failed",
            )
            raise DpmRebalanceIdempotencyStoreWriteFailedError(
                "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"
            ) from exc
        current_logger.exception("Supportability persistence failed")


__all__ = ["record_simulation_supportability"]
