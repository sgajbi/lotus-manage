from __future__ import annotations

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_transitions import approve_item
from src.api.services.wave_workflow_metadata import approval_event_metadata
from src.core.waves import DpmRebalanceWave, WaveState, apply_wave_transition


def build_approved_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
) -> DpmRebalanceWave:
    approved_items = [approve_item(item, actor_id, reason_code, comment) for item in wave.items]
    approved_count = sum(1 for item in approved_items if item.state == "APPROVED")
    if approved_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_APPROVAL_NO_ELIGIBLE_ITEMS",
            f"Wave {wave.wave_id} has no selected or proof-pack-ready items to approve.",
        )

    to_state: WaveState = (
        "APPROVED" if approved_count == len(approved_items) else "APPROVED_WITH_EXCEPTIONS"
    )
    candidate = wave_with_items_and_aggregate(wave=wave, items=approved_items)
    return apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_APPROVED",
            metadata=approval_event_metadata(
                approved_item_count=approved_count,
                total_item_count=len(approved_items),
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )


__all__ = ["build_approved_wave"]
