from src.api.services.wave_aggregate_metrics import (
    aggregate_wave_items,
    simulation_result_state,
)
from src.core.waves import DpmRebalanceWaveItem


def _item(state: str) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{state.lower()}",
        portfolio_id=f"PB_SG_{state}",
        state=state,
    )


def test_aggregate_wave_items_counts_ready_blocked_review_and_degraded_states() -> None:
    metrics = aggregate_wave_items(
        [
            _item("SOURCE_READY"),
            _item("SIMULATED"),
            _item("SELECTED"),
            _item("PROOF_PACK_READY"),
            _item("APPROVED"),
            _item("STAGED"),
            _item("HANDOFF_READY"),
            _item("SOURCE_BLOCKED"),
            _item("SIMULATION_BLOCKED"),
            _item("REVIEW_REQUIRED"),
            _item("SOURCE_DEGRADED"),
        ]
    )

    assert metrics.item_count == 11
    assert metrics.ready_item_count == 7
    assert metrics.blocked_item_count == 2
    assert metrics.review_required_item_count == 1
    assert metrics.source_degraded_item_count == 1
    assert metrics.state_counts == {
        "SOURCE_READY": 1,
        "SIMULATED": 1,
        "SELECTED": 1,
        "PROOF_PACK_READY": 1,
        "APPROVED": 1,
        "STAGED": 1,
        "HANDOFF_READY": 1,
        "SOURCE_BLOCKED": 1,
        "SIMULATION_BLOCKED": 1,
        "REVIEW_REQUIRED": 1,
        "SOURCE_DEGRADED": 1,
    }


def test_simulation_result_state_classifies_full_partial_and_failed_results() -> None:
    assert simulation_result_state([_item("SIMULATED"), _item("SIMULATED")]) == "SIMULATED"
    assert (
        simulation_result_state([_item("SIMULATED"), _item("SIMULATION_BLOCKED")])
        == "PARTIALLY_SIMULATED"
    )
    assert (
        simulation_result_state([_item("SIMULATION_BLOCKED"), _item("SOURCE_BLOCKED")])
        == "SIMULATION_FAILED"
    )


def test_wave_aggregate_metrics_exports_only_aggregate_helpers() -> None:
    from src.api.services import wave_aggregate_metrics

    assert wave_aggregate_metrics.__all__ == [
        "aggregate_wave_items",
        "simulation_result_state",
    ]
