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
) -> BatchScenarioExecutionIds:
    scenario_suffix = f"{batch_id}:{scenario_name}"
    return BatchScenarioExecutionIds(
        request_hash=scenario_suffix,
        correlation_id=(f"{correlation_id}:{scenario_name}" if correlation_id else scenario_suffix),
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
    record_for_support(
        result=scenario_result,
        request_hash=execution_ids.request_hash,
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        idempotency_key=None,
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
