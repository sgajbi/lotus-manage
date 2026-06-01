from __future__ import annotations

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_transitions import stage_item
from src.api.services.wave_workflow_metadata import stage_event_metadata
from src.core.waves import DpmRebalanceWave, apply_wave_transition


def build_staged_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
) -> DpmRebalanceWave:
    staged_items = [stage_item(item, actor_id, reason_code, comment) for item in wave.items]
    staged_count = sum(1 for item in staged_items if item.state == "STAGED")
    if staged_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS",
            f"Wave {wave.wave_id} has no approved items to stage.",
        )

    candidate = wave_with_items_and_aggregate(wave=wave, items=staged_items)
    return apply_wave_transition(
        wave=candidate,
        to_state="STAGED",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state="STAGED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_STAGED",
            metadata=stage_event_metadata(
                staged_item_count=staged_count,
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )


__all__ = ["build_staged_wave"]
