from __future__ import annotations

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_handoff_evidence import build_handoff_ref
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_transitions import handoff_item
from src.api.services.wave_workflow_metadata import handoff_event_metadata
from src.core.waves import DpmRebalanceWave, apply_wave_transition


def build_handoff_ready_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
) -> DpmRebalanceWave:
    handoff_items = [handoff_item(item, actor_id, reason_code, comment) for item in wave.items]
    handoff_item_ids = [
        item.wave_item_id for item in handoff_items if item.state == "HANDOFF_READY"
    ]
    if not handoff_item_ids:
        raise DpmWaveValidationError(
            "DPM_WAVE_HANDOFF_NO_ELIGIBLE_ITEMS",
            f"Wave {wave.wave_id} has no staged items for operations handoff.",
        )

    handoff_ref = build_handoff_ref(
        wave_id=wave.wave_id,
        item_ids=handoff_item_ids,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        comment=comment,
    )
    candidate = wave_with_items_and_aggregate(
        wave=wave,
        items=handoff_items,
        extra_updates={"handoff_refs": [*wave.handoff_refs, handoff_ref]},
    )
    return apply_wave_transition(
        wave=candidate,
        to_state="HANDOFF_READY",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="STAGED",
            to_state="HANDOFF_READY",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_HANDOFF_READY",
            metadata=handoff_event_metadata(
                handoff_ref=handoff_ref,
                handoff_item_count=len(handoff_item_ids),
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )


__all__ = ["build_handoff_ready_wave"]
