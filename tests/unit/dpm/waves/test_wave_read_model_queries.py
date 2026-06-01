from datetime import datetime, timezone

from src.api.services import wave_read_model_queries, wave_service
from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_read_model_queries import (
    wave_detail_for_id,
    wave_items_for_id,
    wave_proof_pack_posture_for_id,
    wave_report_input_for_id,
    wave_supportability_for_id,
)
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveTrigger,
)


class _WaveRepository:
    def __init__(self, wave: DpmRebalanceWave) -> None:
        self.wave = wave
        self.requested_wave_ids: list[str] = []

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        self.requested_wave_ids.append(wave_id)
        if wave_id == self.wave.wave_id:
            return self.wave
        return None


def _item() -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_read_model",
        portfolio_id="PB_SG_READ_MODEL",
        mandate_id="MANDATE_PB_SG_READ_MODEL",
        state="HANDOFF_READY",
        selected_alternative_id="alt_read_model",
        proof_pack_id="dpp_read_model",
        diagnostics={"proof_pack_state": "READY"},
    )


def _wave() -> DpmRebalanceWave:
    items = [_item()]
    return DpmRebalanceWave(
        wave_id="dwv_read_model",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-read-model",
            rationale="Build read-model payloads for a governed wave.",
        ),
        as_of_date="2026-06-01",
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr-read-model",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
        handoff_refs=[],
    )


def test_wave_read_model_queries_load_wave_before_projection() -> None:
    wave = _wave()
    repository = _WaveRepository(wave)

    supportability = wave_supportability_for_id(
        wave_id=wave.wave_id,
        wave_repository=repository,  # type: ignore[arg-type]
    )
    detail = wave_detail_for_id(
        wave_id=wave.wave_id,
        wave_repository=repository,  # type: ignore[arg-type]
    )
    items = wave_items_for_id(
        wave_id=wave.wave_id,
        wave_repository=repository,  # type: ignore[arg-type]
    )
    posture = wave_proof_pack_posture_for_id(
        wave_id=wave.wave_id,
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert repository.requested_wave_ids == [wave.wave_id] * 4
    assert supportability["supportability_state"] == "ready"
    assert detail["wave"] is wave
    assert items["items"] == wave.items
    assert posture["ready_proof_pack_count"] == 1


def test_wave_report_input_query_loads_wave_before_report_assembly() -> None:
    wave = _wave()
    repository = _WaveRepository(wave)

    report_input = wave_report_input_for_id(
        wave_id=wave.wave_id,
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert repository.requested_wave_ids == [wave.wave_id]
    assert report_input.wave_id == wave.wave_id
    assert report_input.wave_state == "HANDOFF_READY"
    assert report_input.proof_pack_posture["ready_proof_pack_count"] == 1


def test_wave_service_delegates_read_model_queries() -> None:
    assert wave_service.wave_supportability_for_id is wave_supportability_for_id
    assert wave_service.wave_detail_for_id is wave_detail_for_id
    assert wave_service.wave_items_for_id is wave_items_for_id
    assert wave_service.wave_proof_pack_posture_for_id is wave_proof_pack_posture_for_id
    assert wave_service.wave_report_input_for_id is wave_report_input_for_id


def test_wave_read_model_queries_export_public_surface() -> None:
    assert wave_read_model_queries.__all__ == [
        "wave_detail_for_id",
        "wave_items_for_id",
        "wave_proof_pack_posture_for_id",
        "wave_report_input_for_id",
        "wave_supportability_for_id",
    ]
