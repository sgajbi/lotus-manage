from __future__ import annotations

from collections.abc import Collection

from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import DpmRebalanceWave


def wave_state_is_idempotent(
    wave: DpmRebalanceWave,
    *,
    replay_states: Collection[str],
) -> bool:
    return wave.state in replay_states


def require_wave_state(
    wave: DpmRebalanceWave,
    *,
    allowed_states: Collection[str],
    error_code: str,
    action_phrase: str,
) -> None:
    if wave.state in allowed_states:
        return
    raise DpmWaveValidationError(
        error_code,
        f"Wave {wave.wave_id} cannot {action_phrase} from state {wave.state}.",
    )


__all__ = ["require_wave_state", "wave_state_is_idempotent"]
