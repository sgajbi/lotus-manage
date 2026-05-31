from typing import Optional

from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import RebalanceResult


def source_input_mode(source_context: Optional[DpmResolvedSourceContext]) -> str:
    return "stateful" if source_context is not None else "stateless"


def apply_source_lineage(
    *,
    result: RebalanceResult,
    source_context: Optional[DpmResolvedSourceContext],
) -> RebalanceResult:
    if source_context is None:
        result.lineage.input_mode = "stateless"
        return result

    lineage = source_context.context.source_lineage
    result.lineage.input_mode = "stateful"
    result.lineage.source_system = source_context.source_system
    result.lineage.portfolio_snapshot_id = lineage.portfolio_snapshot_id
    result.lineage.market_data_snapshot_id = lineage.market_data_snapshot_id
    result.lineage.model_portfolio_id = lineage.model_portfolio_id
    result.lineage.model_portfolio_version = lineage.model_portfolio_version
    result.lineage.shelf_version = lineage.shelf_version
    result.lineage.integration_policy_version = lineage.integration_policy_version
    result.lineage.source_lineage_bundle_id = lineage.source_lineage_bundle_id
    result.lineage.source_supportability_state = source_context.context.supportability.state
    result.lineage.stateful_context_hash = source_context.stateful_context_hash
    return result
