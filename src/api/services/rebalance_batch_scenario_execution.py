from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from src.api.services.rebalance_batch_analysis import build_comparison_metric
from src.api.services.rebalance_source_lineage import apply_source_lineage
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import (
    BatchRebalanceRequest,
    BatchScenarioMetric,
    EngineOptions,
    RebalanceResult,
    SimulationScenario,
)
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    apply_policy_pack_to_engine_options,
)
from src.core.rebalance_runs import DpmAsyncExecutionClaim

RunSimulationFn = Callable[..., RebalanceResult]
RecordForSupportFn = Callable[..., object]


@dataclass(frozen=True)
class BatchScenarioExecutionIds:
    request_hash: str
    correlation_id: str


def build_batch_scenario_execution_ids(
    *,
    batch_id: str,
    scenario_name: str,
    correlation_id: Optional[str],
    execution_attempt: Optional[int] = None,
) -> BatchScenarioExecutionIds:
    scenario_suffix = f"{batch_id}:{scenario_name}"
    scenario_correlation = (
        f"{correlation_id}:attempt-{execution_attempt}:{scenario_name}"
        if correlation_id and execution_attempt is not None
        else f"{correlation_id}:{scenario_name}"
        if correlation_id
        else scenario_suffix
    )
    return BatchScenarioExecutionIds(
        request_hash=scenario_suffix,
        correlation_id=scenario_correlation,
    )


def validate_batch_scenario_options(scenario: SimulationScenario) -> EngineOptions:
    return EngineOptions.model_validate(scenario.options)


def execute_valid_batch_scenario(
    *,
    request: BatchRebalanceRequest,
    scenario_name: str,
    options: EngineOptions,
    batch_id: str,
    correlation_id: Optional[str],
    operation_claim: Optional[DpmAsyncExecutionClaim] = None,
    policy_definition: Optional[DpmPolicyPackDefinition],
    source_context: Optional[DpmResolvedSourceContext],
    run_simulation_fn: RunSimulationFn,
    record_for_support: RecordForSupportFn,
) -> tuple[RebalanceResult, BatchScenarioMetric]:
    effective_options = apply_policy_pack_to_engine_options(
        options=options,
        policy_pack=policy_definition,
    )
    execution_ids = build_batch_scenario_execution_ids(
        batch_id=batch_id,
        scenario_name=scenario_name,
        correlation_id=correlation_id,
        execution_attempt=operation_claim.execution_attempt if operation_claim else None,
    )
    scenario_result = run_simulation_fn(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=effective_options,
        request_hash=execution_ids.request_hash,
        correlation_id=execution_ids.correlation_id,
    )
    scenario_result = apply_source_lineage(
        result=scenario_result,
        source_context=source_context,
    )
    membership = (
        {"operation_claim": operation_claim, "scenario_key": scenario_name}
        if operation_claim is not None
        else {}
    )
    record_for_support(
        result=scenario_result,
        request_hash=execution_ids.request_hash,
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        idempotency_key=None,
        **membership,
    )
    return (
        scenario_result,
        build_comparison_metric(
            scenario_result=scenario_result,
            base_currency=request.portfolio_snapshot.base_currency,
        ),
    )


__all__ = [
    "BatchScenarioExecutionIds",
    "execute_valid_batch_scenario",
    "build_batch_scenario_execution_ids",
    "validate_batch_scenario_options",
]
