from __future__ import annotations

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_transitions import cancel_item
from src.api.services.wave_workflow_metadata import cancel_event_metadata
from src.core.waves import DpmRebalanceWave, DpmWaveInvalidTransitionError, apply_wave_transition


def build_cancelled_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
) -> DpmRebalanceWave:
    cancelled_items = [cancel_item(item, actor_id, reason_code, comment) for item in wave.items]
    candidate = wave_with_items_and_aggregate(wave=wave, items=cancelled_items)
    try:
        return apply_wave_transition(
            wave=candidate,
            to_state="CANCELLED",
            event=build_wave_event(
                wave_id=wave.wave_id,
                from_state=wave.state,
                to_state="CANCELLED",
                actor_id=actor_id,
                correlation_id=correlation_id,
                reason_code="WAVE_CANCELLED",
                metadata=cancel_event_metadata(
                    cancelled_item_count=len(cancelled_items),
                    reason_code=reason_code,
                    comment=comment,
                ),
            ),
        )
    except DpmWaveInvalidTransitionError as exc:
        raise DpmWaveValidationError(
            "DPM_WAVE_CANCEL_INVALID_STATE",
            f"Wave {wave.wave_id} cannot be cancelled from state {wave.state}.",
        ) from exc


__all__ = ["build_cancelled_wave"]
