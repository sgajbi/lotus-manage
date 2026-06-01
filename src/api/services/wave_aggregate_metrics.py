from collections import Counter

from src.core.waves import DpmRebalanceWaveItem, DpmWaveAggregateMetrics, WaveState
from src.core.waves.source_analytics import aggregate_wave_source_analytics


def aggregate_wave_items(items: list[DpmRebalanceWaveItem]) -> DpmWaveAggregateMetrics:
    state_counts = Counter(item.state for item in items)
    state_count_map = {str(state): count for state, count in state_counts.items()}
    return DpmWaveAggregateMetrics(
        item_count=len(items),
        state_counts=state_count_map,
        ready_item_count=state_counts.get("SOURCE_READY", 0)
        + state_counts.get("SIMULATED", 0)
        + state_counts.get("SELECTED", 0)
        + state_counts.get("PROOF_PACK_READY", 0)
        + state_counts.get("APPROVED", 0)
        + state_counts.get("STAGED", 0)
        + state_counts.get("HANDOFF_READY", 0),
        blocked_item_count=state_counts.get("SOURCE_BLOCKED", 0)
        + state_counts.get("SIMULATION_BLOCKED", 0),
        review_required_item_count=state_counts.get("REVIEW_REQUIRED", 0),
        source_degraded_item_count=state_counts.get("SOURCE_DEGRADED", 0),
        source_analytics=aggregate_wave_source_analytics(items),
    )


def simulation_result_state(items: list[DpmRebalanceWaveItem]) -> WaveState:
    simulated = sum(1 for item in items if item.state == "SIMULATED")
    if simulated and simulated < len(items):
        return "PARTIALLY_SIMULATED"
    if simulated:
        return "SIMULATED"
    return "SIMULATION_FAILED"


__all__ = ["aggregate_wave_items", "simulation_result_state"]
