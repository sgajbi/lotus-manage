import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import ValidationError

from src.api.observability import record_execution_call
from src.api.services.rebalance_batch_analysis import (
    build_comparison_metric,
    resolve_base_snapshot_ids,
    to_invalid_options_error,
)
from src.api.services.rebalance_source_lineage import apply_source_lineage, source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    EngineOptions,
    RebalanceResult,
)
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    apply_policy_pack_to_engine_options,
)

RunSimulationFn = Callable[..., RebalanceResult]
RecordForSupportFn = Callable[..., object]


def execute_batch_scenarios(
    *,
    request: BatchRebalanceRequest,
    batch_id: str,
    correlation_id: Optional[str],
    policy_definition: Optional[DpmPolicyPackDefinition],
    source_context: Optional[DpmResolvedSourceContext],
    run_simulation_fn: RunSimulationFn,
    record_for_support: RecordForSupportFn,
    current_logger: logging.Logger | Any,
) -> BatchRebalanceResult:
    results = {}
    comparison_metrics = {}
    failed_scenarios = {}
    warnings = []

    for scenario_name in sorted(request.scenarios.keys()):
        scenario = request.scenarios[scenario_name]
        try:
            options = EngineOptions.model_validate(scenario.options)
        except ValidationError as exc:
            failed_scenarios[scenario_name] = to_invalid_options_error(exc)
            continue

        try:
            effective_options = apply_policy_pack_to_engine_options(
                options=options,
                policy_pack=policy_definition,
            )
            scenario_correlation_id = (
                f"{correlation_id}:{scenario_name}"
                if correlation_id
                else f"{batch_id}:{scenario_name}"
            )
            request_hash = f"{batch_id}:{scenario_name}"
            scenario_result = run_simulation_fn(
                portfolio=request.portfolio_snapshot,
                market_data=request.market_data_snapshot,
                model=request.model_portfolio,
                shelf=request.shelf_entries,
                options=effective_options,
                request_hash=request_hash,
                correlation_id=scenario_correlation_id,
            )
            scenario_result = apply_source_lineage(
                result=scenario_result,
                source_context=source_context,
            )
            record_for_support(
                result=scenario_result,
                request_hash=request_hash,
                portfolio_id=request.portfolio_snapshot.portfolio_id,
                idempotency_key=None,
            )
            results[scenario_name] = scenario_result
            comparison_metrics[scenario_name] = build_comparison_metric(
                scenario_result=scenario_result,
                base_currency=request.portfolio_snapshot.base_currency,
            )
        except (ValidationError, RuntimeError, ValueError) as exc:
            current_logger.exception("Scenario execution failed")
            failed_scenarios[scenario_name] = f"SCENARIO_EXECUTION_ERROR: {type(exc).__name__}"

    if failed_scenarios:
        warnings.append("PARTIAL_BATCH_FAILURE")
    record_execution_call(
        operation="analyze",
        input_mode=source_input_mode(source_context),
        outcome="partial_failure" if failed_scenarios else "success",
        result_status="partial_success" if failed_scenarios else "ready",
    )

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        run_at_utc=datetime.now(timezone.utc).isoformat(),
        base_snapshot_ids=resolve_base_snapshot_ids(request),
        results=results,
        comparison_metrics=comparison_metrics,
        failed_scenarios=failed_scenarios,
        warnings=warnings,
    )


__all__ = ["execute_batch_scenarios"]
