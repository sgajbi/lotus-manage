from datetime import datetime, timezone

import pytest

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_cancel_transition import build_cancelled_wave
from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveTrigger


def _item(*, wave_item_id: str, state: str) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=wave_item_id,
        portfolio_id=f"PB_SG_{wave_item_id.upper()}",
        state=state,
        reason_codes=["INITIAL"],
        diagnostics={"existing": "value"},
    )


def _wave(*, state: str, items: list[DpmRebalanceWaveItem]) -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id="dwv_cancel",
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-cancel",
            rationale="Cancel wave before external execution.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_cancel",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )


def test_build_cancelled_wave_excludes_items_and_records_no_execution_claim() -> None:
    cancelled = build_cancelled_wave(
        wave=_wave(state="STAGED", items=[_item(wave_item_id="dwi_1", state="STAGED")]),
        actor_id="pm_cancel",
        reason_code="CLIENT_CANCELLED",
        comment="Client changed instruction.",
        correlation_id="corr_cancel",
    )

    assert cancelled.state == "CANCELLED"
    assert cancelled.version == 2
    assert cancelled.items[0].state == "EXCLUDED"
    assert cancelled.items[0].diagnostics["cancel_actor_id"] == "pm_cancel"
    assert cancelled.items[0].diagnostics["external_execution_claimed"] is False
    assert cancelled.aggregate_metrics.state_counts == {"EXCLUDED": 1}
    assert cancelled.events[-1].reason_code == "WAVE_CANCELLED"
    assert cancelled.events[-1].metadata == {
        "cancel_reason_code": "CLIENT_CANCELLED",
        "cancelled_item_count": 1,
        "external_execution_claimed": False,
        "comment": "Client changed instruction.",
    }


def test_build_cancelled_wave_preserves_handoff_ready_item_diagnostics() -> None:
    cancelled = build_cancelled_wave(
        wave=_wave(
            state="STAGED",
            items=[
                _item(wave_item_id="dwi_1", state="STAGED"),
                _item(wave_item_id="dwi_2", state="HANDOFF_READY"),
            ],
        ),
        actor_id="pm_cancel",
        reason_code="CLIENT_CANCELLED",
        comment=None,
        correlation_id="corr_cancel",
    )

    assert [item.state for item in cancelled.items] == ["EXCLUDED", "HANDOFF_READY"]
    assert cancelled.aggregate_metrics.state_counts == {"EXCLUDED": 1, "HANDOFF_READY": 1}
    assert cancelled.events[-1].metadata == {
        "cancel_reason_code": "CLIENT_CANCELLED",
        "cancelled_item_count": 2,
        "external_execution_claimed": False,
    }


def test_build_cancelled_wave_maps_invalid_transition_to_validation_error() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_cancelled_wave(
            wave=_wave(
                state="HANDOFF_READY",
                items=[_item(wave_item_id="dwi_1", state="HANDOFF_READY")],
            ),
            actor_id="pm_cancel",
            reason_code="CLIENT_CANCELLED",
            comment=None,
            correlation_id="corr_cancel",
        )

    assert exc_info.value.code == "DPM_WAVE_CANCEL_INVALID_STATE"


def test_wave_cancel_transition_exports_only_cancel_helper() -> None:
    from src.api.services import wave_cancel_transition

    assert wave_cancel_transition.__all__ == ["build_cancelled_wave"]
