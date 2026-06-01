from datetime import datetime, timezone

import pytest

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_stage_transition import build_staged_wave
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
        wave_id="dwv_stage",
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-stage",
            rationale="Stage approved wave items.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_stage",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )


def test_build_staged_wave_stages_approved_items_and_event_metadata() -> None:
    staged = build_staged_wave(
        wave=_wave(state="APPROVED", items=[_item(wave_item_id="dwi_1", state="APPROVED")]),
        actor_id="ops_stage",
        reason_code="READY_FOR_HANDOFF",
        comment="Ready for operations.",
        correlation_id="corr_stage",
    )

    assert staged.state == "STAGED"
    assert staged.version == 2
    assert staged.items[0].state == "STAGED"
    assert staged.items[0].diagnostics["stage_actor_id"] == "ops_stage"
    assert staged.items[0].diagnostics["external_execution_claimed"] is False
    assert staged.aggregate_metrics.state_counts == {"STAGED": 1}
    assert staged.events[-1].reason_code == "WAVE_STAGED"
    assert staged.events[-1].metadata == {
        "staged_item_count": 1,
        "stage_reason_code": "READY_FOR_HANDOFF",
        "comment": "Ready for operations.",
    }


def test_build_staged_wave_preserves_unapproved_exception_items() -> None:
    staged = build_staged_wave(
        wave=_wave(
            state="APPROVED_WITH_EXCEPTIONS",
            items=[
                _item(wave_item_id="dwi_1", state="APPROVED"),
                _item(wave_item_id="dwi_2", state="SIMULATED"),
            ],
        ),
        actor_id="ops_stage",
        reason_code="PARTIAL_STAGE",
        comment=None,
        correlation_id="corr_stage",
    )

    assert staged.state == "STAGED"
    assert [item.state for item in staged.items] == ["STAGED", "SIMULATED"]
    assert staged.aggregate_metrics.state_counts == {"STAGED": 1, "SIMULATED": 1}
    assert staged.events[-1].metadata == {
        "staged_item_count": 1,
        "stage_reason_code": "PARTIAL_STAGE",
    }


def test_build_staged_wave_rejects_no_eligible_items() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_staged_wave(
            wave=_wave(
                state="APPROVED_WITH_EXCEPTIONS",
                items=[_item(wave_item_id="dwi_1", state="SIMULATED")],
            ),
            actor_id="ops_stage",
            reason_code="READY_FOR_HANDOFF",
            comment=None,
            correlation_id="corr_stage",
        )

    assert exc_info.value.code == "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS"


def test_wave_stage_transition_exports_only_stage_helper() -> None:
    from src.api.services import wave_stage_transition

    assert wave_stage_transition.__all__ == ["build_staged_wave"]
