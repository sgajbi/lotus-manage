from src.api.services.wave_simulation import build_simulated_wave
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveAggregateMetrics


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_simulate",
        state="SOURCE_CHECKED",
        version=3,
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_simulate",
                portfolio_id="PB_SG_SIMULATE",
                state="SOURCE_READY",
            )
        ],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"SOURCE_READY": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[],
    )


def test_build_simulated_wave_records_blocked_result_when_item_input_is_missing() -> None:
    simulated = build_simulated_wave(
        wave=_wave(),
        actor_id="pm_001",
        correlation_id="corr_simulate",
        item_inputs={},
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
    )

    assert simulated.state == "SIMULATION_FAILED"
    assert simulated.items[0].state == "SIMULATION_BLOCKED"
    assert simulated.items[0].reason_codes == ["CONSTRUCTION_INPUT_MISSING"]
    assert simulated.aggregate_metrics.blocked_item_count == 1
    assert [event.reason_code for event in simulated.events] == [
        "WAVE_SIMULATION_STARTED",
        "WAVE_SIMULATION_COMPLETED",
    ]
    assert simulated.events[-1].metadata["state_counts"] == {"SIMULATION_BLOCKED": 1}
    assert simulated.events[-1].metadata["blocked_item_count"] == 1


def test_wave_simulation_exports_only_simulation_builder() -> None:
    from src.api.services import wave_simulation

    assert wave_simulation.__all__ == ["build_simulated_wave"]
