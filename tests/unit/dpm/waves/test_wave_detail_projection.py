from src.api.services.wave_detail_projection import wave_detail_payload, wave_items_payload
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
)


def _wave() -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi_detail",
        portfolio_id="PB_SG_DETAIL",
        state="SIMULATED",
        proof_pack_id="dpp_detail",
        diagnostics={"proof_pack_state": "READY"},
    )
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_detail",
        state="SIMULATED",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"SIMULATED": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        handoff_refs=[],
    )


def test_wave_detail_payload_includes_supportability_and_proof_pack_posture() -> None:
    wave = _wave()

    payload = wave_detail_payload(wave)

    assert payload["wave"] is wave
    assert payload["supportability"]["supportability_state"] == "ready"
    assert payload["proof_pack_posture"]["linked_item_count"] == 1
    assert payload["proof_pack_posture"]["ready_proof_pack_count"] == 1


def test_wave_items_payload_projects_items_and_aggregate_metrics() -> None:
    wave = _wave()

    payload = wave_items_payload(wave)

    assert payload == {
        "wave_id": "dwv_detail",
        "wave_state": "SIMULATED",
        "items": wave.items,
        "aggregate_metrics": wave.aggregate_metrics,
    }


def test_wave_detail_projection_exports_only_payload_builders() -> None:
    from src.api.services import wave_detail_projection

    assert wave_detail_projection.__all__ == ["wave_detail_payload", "wave_items_payload"]
