import logging
from collections.abc import Callable
from typing import Any, Optional

from src.api.observability import record_execution_call
from src.api.request_models import RebalanceRequest
from src.api.services.rebalance_idempotency_replay import resolve_idempotency_replay
from src.api.services.rebalance_source_lineage import apply_source_lineage, source_input_mode
from src.api.services.rebalance_supportability_write import record_simulation_supportability
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import RebalanceResult
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    apply_policy_pack_to_engine_options,
)
from src.core.rebalance_runs import DpmRunSupportService

RunSimulationFn = Callable[..., RebalanceResult]
RecordForSupportFn = Callable[..., object]
SupportServiceFactory = Callable[[], DpmRunSupportService]


def execution_outcome_for_status(status_value: str) -> str:
    return "blocked" if status_value == "BLOCKED" else "success"


def execution_status_label(status_value: str) -> str:
    return status_value.lower()


def execute_simulation_request(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    request_hash: str,
    correlation_id: str,
    policy_pack_definition: Optional[DpmPolicyPackDefinition],
    replay_enabled: bool,
    source_context: Optional[DpmResolvedSourceContext],
    support_service_factory: SupportServiceFactory,
    run_simulation_fn: RunSimulationFn,
    record_for_support: RecordForSupportFn,
    current_logger: logging.Logger | Any,
) -> RebalanceResult:
    effective_options = apply_policy_pack_to_engine_options(
        options=request.options,
        policy_pack=policy_pack_definition,
    )

    if replay_enabled:
        replay_result = resolve_idempotency_replay(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            source_context=source_context,
            support_service_factory=support_service_factory,
        )
        if replay_result is not None:
            return replay_result

    result = run_simulation_fn(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=effective_options,
        request_hash=request_hash,
        correlation_id=correlation_id,
    )
    result = apply_source_lineage(result=result, source_context=source_context)

    record_simulation_supportability(
        result=result,
        request_hash=request_hash,
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        idempotency_key=idempotency_key,
        replay_enabled=replay_enabled,
        source_context=source_context,
        record_for_support=record_for_support,
        current_logger=current_logger,
    )

    if result.status == "BLOCKED":
        current_logger.warning("Run blocked by DPM engine safety rules")

    record_execution_call(
        operation="simulate",
        input_mode=source_input_mode(source_context),
        outcome=execution_outcome_for_status(result.status),
        result_status=execution_status_label(result.status),
    )
    return result


__all__ = [
    "RecordForSupportFn",
    "RunSimulationFn",
    "SupportServiceFactory",
    "execute_simulation_request",
    "execution_outcome_for_status",
    "execution_status_label",
]
