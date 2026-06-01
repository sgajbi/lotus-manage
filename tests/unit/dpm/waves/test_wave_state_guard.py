import pytest

from src.api.services import wave_service, wave_state_guard
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_state_guard import require_wave_state, wave_state_is_idempotent
from src.core.waves import DpmRebalanceWave


def _wave(*, state: str) -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_state_guard",
        state=state,
    )


def test_wave_state_is_idempotent_matches_replay_states() -> None:
    wave = _wave(state="SIMULATED")

    assert wave_state_is_idempotent(
        wave,
        replay_states={"SIMULATED", "PARTIALLY_SIMULATED"},
    )
    assert not wave_state_is_idempotent(wave, replay_states={"SOURCE_CHECKED"})


def test_require_wave_state_accepts_allowed_state() -> None:
    require_wave_state(
        _wave(state="SOURCE_CHECKED"),
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )


def test_require_wave_state_raises_governed_validation_error() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        require_wave_state(
            _wave(state="CREATED"),
            allowed_states={"SOURCE_CHECKED"},
            error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
            action_phrase="be simulated",
        )

    assert exc_info.value.code == "DPM_WAVE_SIMULATION_INVALID_STATE"
    assert exc_info.value.message == "Wave dwv_state_guard cannot be simulated from state CREATED."


def test_wave_service_preserves_state_guard_private_aliases() -> None:
    assert wave_service._wave_state_is_idempotent is wave_state_is_idempotent
    assert wave_service._require_wave_state is require_wave_state


def test_wave_state_guard_exports_public_surface() -> None:
    assert wave_state_guard.__all__ == ["require_wave_state", "wave_state_is_idempotent"]
