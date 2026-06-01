from datetime import datetime, timezone

import pytest

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_report_input import build_report_input_for_wave
from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
    DpmWaveTrigger,
)


def _item() -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_report",
        portfolio_id="PB_SG_REPORT",
        mandate_id="MANDATE_PB_SG_REPORT",
        state="HANDOFF_READY",
        selected_alternative_id="alt_report",
        proof_pack_id="dpp_report",
        diagnostics={"proof_pack_state": "READY"},
    )


def _wave(*, handoff_refs: list[DpmWaveHandoffRef] | None = None) -> DpmRebalanceWave:
    items = [_item()]
    return DpmRebalanceWave(
        wave_id="dwv_report_input",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-report",
            rationale="Build report input for a governed wave.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr-report",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
        handoff_refs=handoff_refs or [],
    )


def test_build_report_input_for_wave_assembles_supportability_and_proof_pack_posture() -> None:
    report_input = build_report_input_for_wave(
        wave=_wave(),
        wave_repository=object(),  # type: ignore[arg-type]
    )

    assert report_input.wave_id == "dwv_report_input"
    assert report_input.wave_state == "HANDOFF_READY"
    assert report_input.supportability["supportability_state"] == "ready"
    assert report_input.proof_pack_posture["ready_proof_pack_count"] == 1
    assert report_input.external_execution_claimed is False
    assert (
        report_input.external_execution_boundary.boundary_id
        == "DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY"
    )
    assert report_input.portfolio_memory_context is None


def test_build_report_input_for_wave_maps_external_execution_boundary_error() -> None:
    unsafe_handoff = DpmWaveHandoffRef(
        handoff_ref_id="dwh_unsafe",
        wave_id="dwv_report_input",
        item_ids=["dwi_report"],
        actor_id="ops_001",
        reason_code="UNSAFE_EXTERNAL_EXECUTION_CLAIM",
        correlation_id="corr-report",
        external_execution_claimed=True,
        content_hash="sha256:unsafe",
    )

    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_report_input_for_wave(
            wave=_wave(handoff_refs=[unsafe_handoff]),
            wave_repository=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY"
    assert "cannot propagate external execution claims" in exc_info.value.message


def test_wave_report_input_exports_only_report_input_builder() -> None:
    from src.api.services import wave_report_input

    assert wave_report_input.__all__ == ["build_report_input_for_wave"]
