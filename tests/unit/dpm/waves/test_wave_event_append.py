import pytest

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_event_append import append_same_state_event
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveEvent


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_append",
        state="SIMULATED",
        version=3,
        events=[],
    )


def _event() -> DpmRebalanceWaveEvent:
    return DpmRebalanceWaveEvent.model_construct(
        event_id="dwe_append",
        wave_id="dwv_append",
        from_state="SIMULATED",
        to_state="SIMULATED",
        event_type="ITEM_SELECTION",
        actor_id="pm_001",
        reason_code="WAVE_ITEM_ALTERNATIVE_SELECTED",
        correlation_id="corr_append",
        metadata={},
    )


def test_append_same_state_event_increments_version_and_appends_event() -> None:
    wave = _wave()
    event = _event()

    updated = append_same_state_event(wave=wave, event=event)

    assert updated.version == 4
    assert updated.events == [event]
    assert wave.version == 3
    assert wave.events == []


def test_append_same_state_event_rejects_wave_identity_mismatch() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        append_same_state_event(
            wave=_wave(),
            event=_event().model_copy(update={"wave_id": "dwv_other"}),
        )

    assert exc_info.value.code == "DPM_WAVE_EVENT_WAVE_MISMATCH"
    assert exc_info.value.message == "Wave event mismatch."


def test_append_same_state_event_rejects_state_mismatch() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        append_same_state_event(
            wave=_wave(),
            event=_event().model_copy(update={"to_state": "APPROVED"}),
        )

    assert exc_info.value.code == "DPM_WAVE_EVENT_STATE_MISMATCH"
    assert exc_info.value.message == "Wave event state mismatch."


def test_wave_event_append_exports_only_append_helper() -> None:
    from src.api.services import wave_event_append

    assert wave_event_append.__all__ == ["append_same_state_event"]
