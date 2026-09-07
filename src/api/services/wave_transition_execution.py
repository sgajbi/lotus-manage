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
    tenant_id: str,
    replay_states: set[str],
    allowed_states: set[str] | None,
    error_code: str,
    action_phrase: str,
) -> PreparedWaveTransition:
    """Load and admit a wave for transition, refusing before any state change.

    This is the sharpest of the three defects in issue #677: the load used to
    resolve a wave by id alone, so a wave created under one tenant could be
    source-checked or selected against by another - and #676's tenant argument
    made the MANDATE reads on those paths look correct while the wave itself
    was never that caller's to touch. An unfenced read here leads to an
    unfenced write.

    The tenant fence is inside the load, before the idempotent-replay shortcut
    and before the state guard. Ordering matters: replaying first would return
    another tenant's wave as a successful no-op, which is a read, and a
    refusal that arrives after the transition is not a refusal.
    """

    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    if wave_state_is_idempotent(wave, replay_states=replay_states):
        return PreparedWaveTransition(wave=wave, replayed=True)
    if allowed_states is not None:
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
    tenant_id: str,
) -> None:
    """Write the transition, with the tenant in the update predicate.

    Fencing only the read would leave the write reachable by a caller that
    obtained a wave some other way, so the tenant travels to the UPDATE rather
    than being trusted from the earlier load (issue #677).
    """

    update_wave_or_raise(
        wave_repository=wave_repository,
        wave=transitioned_wave,
        expected_version=source_wave.version,
        tenant_id=tenant_id,
    )


__all__ = [
    "PreparedWaveTransition",
    "persist_transitioned_wave",
    "prepare_wave_transition",
]
