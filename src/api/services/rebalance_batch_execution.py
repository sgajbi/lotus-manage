import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import ValidationError

from src.api.observability import record_execution_call
from src.api.services.rebalance_batch_analysis import (
    resolve_base_snapshot_ids,
    to_invalid_options_error,
)
from src.api.services.rebalance_batch_scenario_execution import (
    RecordForSupportFn,
    RunSimulationFn,
    execute_valid_batch_scenario,
    validate_batch_scenario_options,
)
from src.api.services.rebalance_source_lineage import source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
)
from src.core.rebalance.policy_packs import DpmPolicyPackDefinition


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
            options = validate_batch_scenario_options(scenario)
        except ValidationError as exc:
            failed_scenarios[scenario_name] = to_invalid_options_error(exc)
            continue

        try:
            scenario_result, scenario_metric = execute_valid_batch_scenario(
                request=request,
                scenario_name=scenario_name,
                options=options,
                batch_id=batch_id,
                correlation_id=correlation_id,
                policy_definition=policy_definition,
                source_context=source_context,
                run_simulation_fn=run_simulation_fn,
                record_for_support=record_for_support,
            )
            results[scenario_name] = scenario_result
            comparison_metrics[scenario_name] = scenario_metric
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
