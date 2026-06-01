import pytest

from src.api.services import wave_transition_execution
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_transition_execution import (
    PreparedWaveTransition,
    persist_transitioned_wave,
    prepare_wave_transition,
)
from src.core.waves import DpmRebalanceWave


class _WaveRepository:
    def __init__(self, wave: DpmRebalanceWave) -> None:
        self.wave = wave
        self.updated_wave: DpmRebalanceWave | None = None
        self.expected_version: int | None = None

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        if wave_id == self.wave.wave_id:
            return self.wave
        return None

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        self.updated_wave = wave
        self.expected_version = expected_version


def _wave(*, state: str = "SOURCE_CHECKED", version: int = 3) -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_transition_execution",
        state=state,
        version=version,
    )


def test_prepare_wave_transition_returns_replayed_wave_without_state_guard() -> None:
    wave = _wave(state="SIMULATED")

    prepared = prepare_wave_transition(
        wave_id=wave.wave_id,
        wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
        replay_states={"SIMULATED"},
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )

    assert prepared == PreparedWaveTransition(wave=wave, replayed=True)


def test_prepare_wave_transition_requires_allowed_state_for_new_transition() -> None:
    wave = _wave(state="SOURCE_CHECKED")

    prepared = prepare_wave_transition(
        wave_id=wave.wave_id,
        wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
        replay_states={"SIMULATED"},
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )

    assert prepared == PreparedWaveTransition(wave=wave, replayed=False)


def test_prepare_wave_transition_supports_non_replayable_allowed_transition() -> None:
    wave = _wave(state="SIMULATED")

    prepared = prepare_wave_transition(
        wave_id=wave.wave_id,
        wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
        replay_states=set(),
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED"},
        error_code="DPM_WAVE_SELECTION_INVALID_STATE",
        action_phrase="record alternative selection",
    )

    assert prepared == PreparedWaveTransition(wave=wave, replayed=False)


def test_prepare_wave_transition_with_empty_replay_states_requires_allowed_state() -> None:
    wave = _wave(state="APPROVED")

    with pytest.raises(DpmWaveValidationError) as exc_info:
        prepare_wave_transition(
            wave_id=wave.wave_id,
            wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
            replay_states=set(),
            allowed_states={"SIMULATED", "PARTIALLY_SIMULATED"},
            error_code="DPM_WAVE_SELECTION_INVALID_STATE",
            action_phrase="record alternative selection",
        )

    assert exc_info.value.code == "DPM_WAVE_SELECTION_INVALID_STATE"


def test_prepare_wave_transition_supports_explicitly_unguarded_transition() -> None:
    wave = _wave(state="CREATED")

    prepared = prepare_wave_transition(
        wave_id=wave.wave_id,
        wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
        replay_states={"CANCELLED"},
        allowed_states=None,
        error_code="DPM_WAVE_CANCEL_INVALID_STATE",
        action_phrase="be cancelled",
    )

    assert prepared == PreparedWaveTransition(wave=wave, replayed=False)


def test_prepare_wave_transition_preserves_state_validation_error() -> None:
    wave = _wave(state="CREATED")

    with pytest.raises(DpmWaveValidationError) as exc_info:
        prepare_wave_transition(
            wave_id=wave.wave_id,
            wave_repository=_WaveRepository(wave),  # type: ignore[arg-type]
            replay_states={"SIMULATED"},
            allowed_states={"SOURCE_CHECKED"},
            error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
            action_phrase="be simulated",
        )

    assert exc_info.value.code == "DPM_WAVE_SIMULATION_INVALID_STATE"


def test_persist_transitioned_wave_uses_source_wave_version_for_optimistic_update() -> None:
    source_wave = _wave(version=7)
    transitioned_wave = _wave(state="SIMULATED", version=8)
    repository = _WaveRepository(source_wave)

    persist_transitioned_wave(
        wave_repository=repository,  # type: ignore[arg-type]
        source_wave=source_wave,
        transitioned_wave=transitioned_wave,
    )

    assert repository.updated_wave is transitioned_wave
    assert repository.expected_version == 7


def test_wave_transition_execution_exports_public_surface() -> None:
    assert wave_transition_execution.__all__ == [
        "PreparedWaveTransition",
        "persist_transitioned_wave",
        "prepare_wave_transition",
    ]
