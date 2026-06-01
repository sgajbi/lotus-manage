from __future__ import annotations

from dataclasses import dataclass

from src.api.services.wave_lookup import get_wave_or_raise
from src.api.services.wave_persistence import update_wave_or_raise
from src.api.services.wave_state_guard import require_wave_state, wave_state_is_idempotent
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


@dataclass(frozen=True)
class PreparedWaveTransition:
    wave: DpmRebalanceWave
    replayed: bool


def prepare_wave_transition(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    replay_states: set[str],
    allowed_states: set[str],
    error_code: str,
    action_phrase: str,
) -> PreparedWaveTransition:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave_state_is_idempotent(wave, replay_states=replay_states):
        return PreparedWaveTransition(wave=wave, replayed=True)
    require_wave_state(
        wave,
        allowed_states=allowed_states,
        error_code=error_code,
        action_phrase=action_phrase,
    )
    return PreparedWaveTransition(wave=wave, replayed=False)


def persist_transitioned_wave(
    *,
    wave_repository: DpmWaveRepository,
    source_wave: DpmRebalanceWave,
    transitioned_wave: DpmRebalanceWave,
) -> None:
    update_wave_or_raise(
        wave_repository=wave_repository,
        wave=transitioned_wave,
        expected_version=source_wave.version,
    )


__all__ = [
    "PreparedWaveTransition",
    "persist_transitioned_wave",
    "prepare_wave_transition",
]
