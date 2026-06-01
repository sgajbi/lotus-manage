from datetime import datetime, timezone

import pytest

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_approval_transition import build_approved_wave
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
        wave_id="dwv_approval",
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-approval",
            rationale="Approve selected wave items.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_approval",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )


def test_build_approved_wave_approves_all_eligible_items() -> None:
    approved = build_approved_wave(
        wave=_wave(state="SIMULATED", items=[_item(wave_item_id="dwi_1", state="SELECTED")]),
        actor_id="pm_approval",
        reason_code="APPROVED_BY_PM",
        comment="Approved.",
        correlation_id="corr_approval",
    )

    assert approved.state == "APPROVED"
    assert approved.version == 2
    assert approved.items[0].state == "APPROVED"
    assert approved.items[0].diagnostics["approval_actor_id"] == "pm_approval"
    assert approved.aggregate_metrics.state_counts == {"APPROVED": 1}
    assert approved.events[-1].reason_code == "WAVE_APPROVED"
    assert approved.events[-1].metadata == {
        "approved_item_count": 1,
        "exception_item_count": 0,
        "approval_reason_code": "APPROVED_BY_PM",
        "comment": "Approved.",
    }


def test_build_approved_wave_uses_exception_state_for_partially_approved_items() -> None:
    approved = build_approved_wave(
        wave=_wave(
            state="PARTIALLY_SIMULATED",
            items=[
                _item(wave_item_id="dwi_1", state="PROOF_PACK_READY"),
                _item(wave_item_id="dwi_2", state="SIMULATED"),
            ],
        ),
        actor_id="pm_approval",
        reason_code="APPROVED_WITH_EXCEPTION",
        comment=None,
        correlation_id="corr_approval",
    )

    assert approved.state == "APPROVED_WITH_EXCEPTIONS"
    assert [item.state for item in approved.items] == ["APPROVED", "SIMULATED"]
    assert approved.aggregate_metrics.state_counts == {"APPROVED": 1, "SIMULATED": 1}
    assert approved.events[-1].metadata == {
        "approved_item_count": 1,
        "exception_item_count": 1,
        "approval_reason_code": "APPROVED_WITH_EXCEPTION",
    }


def test_build_approved_wave_rejects_no_eligible_items() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_approved_wave(
            wave=_wave(state="SIMULATED", items=[_item(wave_item_id="dwi_1", state="SIMULATED")]),
            actor_id="pm_approval",
            reason_code="APPROVED_BY_PM",
            comment=None,
            correlation_id="corr_approval",
        )

    assert exc_info.value.code == "DPM_WAVE_APPROVAL_NO_ELIGIBLE_ITEMS"


def test_wave_approval_transition_exports_only_approval_helper() -> None:
    from src.api.services import wave_approval_transition

    assert wave_approval_transition.__all__ == ["build_approved_wave"]
