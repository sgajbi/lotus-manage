from datetime import datetime, timezone

import pytest

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_handoff_transition import build_handoff_ready_wave
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveTrigger


def _item(*, wave_item_id: str, state: str) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=wave_item_id,
        portfolio_id=f"PB_SG_{wave_item_id.upper()}",
        state=state,
        reason_codes=["INITIAL"],
        diagnostics={"existing": "value"},
    )


def _wave(*, items: list[DpmRebalanceWaveItem]) -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id="dwv_handoff",
        state="STAGED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-handoff",
            rationale="Create internal operations handoff.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_handoff",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )


def test_build_handoff_ready_wave_creates_handoff_ref_and_event_metadata() -> None:
    handoff_ready = build_handoff_ready_wave(
        wave=_wave(items=[_item(wave_item_id="dwi_1", state="STAGED")]),
        actor_id="ops_handoff",
        reason_code="READY_FOR_OPERATIONS",
        comment="Handoff package ready.",
        correlation_id="corr_handoff",
    )

    assert handoff_ready.state == "HANDOFF_READY"
    assert handoff_ready.version == 2
    assert handoff_ready.items[0].state == "HANDOFF_READY"
    assert handoff_ready.items[0].diagnostics["handoff_actor_id"] == "ops_handoff"
    assert handoff_ready.items[0].diagnostics["external_execution_claimed"] is False
    assert handoff_ready.aggregate_metrics.state_counts == {"HANDOFF_READY": 1}
    assert len(handoff_ready.handoff_refs) == 1
    handoff_ref = handoff_ready.handoff_refs[0]
    assert handoff_ref.item_ids == ["dwi_1"]
    assert handoff_ref.external_execution_claimed is False
    assert handoff_ready.events[-1].reason_code == "WAVE_HANDOFF_READY"
    assert handoff_ready.events[-1].metadata == {
        "handoff_ref_id": handoff_ref.handoff_ref_id,
        "handoff_item_count": 1,
        "external_execution_claimed": False,
        "handoff_reason_code": "READY_FOR_OPERATIONS",
        "comment": "Handoff package ready.",
    }


def test_build_handoff_ready_wave_preserves_non_staged_exception_items() -> None:
    handoff_ready = build_handoff_ready_wave(
        wave=_wave(
            items=[
                _item(wave_item_id="dwi_1", state="STAGED"),
                _item(wave_item_id="dwi_2", state="SIMULATED"),
            ]
        ),
        actor_id="ops_handoff",
        reason_code="PARTIAL_HANDOFF",
        comment=None,
        correlation_id="corr_handoff",
    )

    assert [item.state for item in handoff_ready.items] == ["HANDOFF_READY", "SIMULATED"]
    assert handoff_ready.handoff_refs[0].item_ids == ["dwi_1"]
    assert handoff_ready.aggregate_metrics.state_counts == {
        "HANDOFF_READY": 1,
        "SIMULATED": 1,
    }


def test_build_handoff_ready_wave_rejects_no_eligible_items() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_handoff_ready_wave(
            wave=_wave(items=[_item(wave_item_id="dwi_1", state="APPROVED")]),
            actor_id="ops_handoff",
            reason_code="READY_FOR_OPERATIONS",
            comment=None,
            correlation_id="corr_handoff",
        )

    assert exc_info.value.code == "DPM_WAVE_HANDOFF_NO_ELIGIBLE_ITEMS"


def test_wave_handoff_transition_exports_only_handoff_helper() -> None:
    from src.api.services import wave_handoff_transition

    assert wave_handoff_transition.__all__ == ["build_handoff_ready_wave"]
