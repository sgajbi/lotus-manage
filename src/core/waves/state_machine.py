"""Pure RFC-0041 wave state-machine rules."""

from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveEvent, WaveState


class DpmWaveInvalidTransitionError(ValueError):
    """Raised when a wave transition is not allowed."""


ALLOWED_WAVE_TRANSITIONS: dict[WaveState, set[WaveState]] = {
    "DRAFT": {"PREVIEWED", "CANCELLED"},
    "PREVIEWED": {"CREATED", "CANCELLED"},
    "CREATED": {"SOURCE_CHECKED", "CANCELLED"},
    "SOURCE_CHECKED": {"SIMULATING", "REVIEW_REQUIRED", "BLOCKED", "CANCELLED"},
    "SIMULATING": {"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"},
    "SIMULATED": {"REVIEW_REQUIRED", "APPROVED", "CANCELLED"},
    "PARTIALLY_SIMULATED": {"REVIEW_REQUIRED", "APPROVED_WITH_EXCEPTIONS", "CANCELLED"},
    "REVIEW_REQUIRED": {"APPROVED", "APPROVED_WITH_EXCEPTIONS", "REJECTED", "CANCELLED"},
    "APPROVED": {"STAGED", "CANCELLED"},
    "APPROVED_WITH_EXCEPTIONS": {"STAGED", "CANCELLED"},
    "STAGED": {"HANDOFF_READY", "HANDOFF_BLOCKED", "CANCELLED"},
    "HANDOFF_READY": {"HANDOFF_ACKNOWLEDGED", "CLOSED"},
    "HANDOFF_BLOCKED": {"SOURCE_CHECKED", "CANCELLED"},
    "SIMULATION_FAILED": {"SOURCE_CHECKED", "CANCELLED"},
    "BLOCKED": {"SOURCE_CHECKED", "CANCELLED"},
    "REJECTED": {"CLOSED"},
    "CANCELLED": {"CLOSED"},
    "HANDOFF_ACKNOWLEDGED": {"CLOSED"},
    "CLOSED": set(),
}


def validate_wave_transition(*, from_state: WaveState, to_state: WaveState) -> None:
    allowed = ALLOWED_WAVE_TRANSITIONS[from_state]
    if to_state not in allowed:
        raise DpmWaveInvalidTransitionError(f"DPM_WAVE_INVALID_TRANSITION:{from_state}->{to_state}")


def apply_wave_transition(
    *,
    wave: DpmRebalanceWave,
    to_state: WaveState,
    event: DpmRebalanceWaveEvent,
) -> DpmRebalanceWave:
    validate_wave_transition(from_state=wave.state, to_state=to_state)
    if event.wave_id != wave.wave_id:
        raise DpmWaveInvalidTransitionError("DPM_WAVE_EVENT_WAVE_MISMATCH")
    if event.from_state != wave.state:
        raise DpmWaveInvalidTransitionError("DPM_WAVE_EVENT_FROM_STATE_MISMATCH")
    if event.to_state != to_state:
        raise DpmWaveInvalidTransitionError("DPM_WAVE_EVENT_TO_STATE_MISMATCH")
    return wave.model_copy(
        update={
            "state": to_state,
            "version": wave.version + 1,
            "events": [*wave.events, event],
        },
        deep=True,
    )
