import uuid

from src.api.services.wave_event_evidence import (
    build_wave_event,
    idempotency_key_hash,
    request_hash,
)
from src.core.waves import DpmRebalanceWave, apply_wave_transition


def create_wave_request_hash(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    portfolios: list[dict[str, object]],
) -> str:
    return request_hash(
        {
            "trigger_type": trigger_type,
            "trigger_id": trigger_id,
            "rationale": rationale,
            "as_of_date": as_of_date,
            "actor_id": actor_id,
            "portfolios": portfolios,
        }
    )


def create_created_wave_id() -> str:
    return f"dwv_{uuid.uuid4().hex[:12]}"


def promote_preview_to_created_wave(
    *,
    preview: DpmRebalanceWave,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
) -> DpmRebalanceWave:
    wave = preview.model_copy(update={"wave_id": wave_id}, deep=True)
    wave = wave.model_copy(
        update={
            "events": [
                event.model_copy(update={"wave_id": wave.wave_id}, deep=True)
                for event in wave.events
            ]
        },
        deep=True,
    )
    return apply_wave_transition(
        wave=wave,
        to_state="CREATED",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="PREVIEWED",
            to_state="CREATED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_CREATED",
            metadata={"idempotency_key_hash": idempotency_key_hash(idempotency_key)},
        ),
    )


__all__ = [
    "create_created_wave_id",
    "create_wave_request_hash",
    "promote_preview_to_created_wave",
]
