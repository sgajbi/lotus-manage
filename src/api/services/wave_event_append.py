from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveEvent


def append_same_state_event(
    *,
    wave: DpmRebalanceWave,
    event: DpmRebalanceWaveEvent,
) -> DpmRebalanceWave:
    if event.wave_id != wave.wave_id:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_WAVE_MISMATCH", "Wave event mismatch.")
    if event.from_state != wave.state or event.to_state != wave.state:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_STATE_MISMATCH", "Wave event state mismatch.")
    return wave.model_copy(
        update={"version": wave.version + 1, "events": [*wave.events, event]},
        deep=True,
    )


__all__ = ["append_same_state_event"]
