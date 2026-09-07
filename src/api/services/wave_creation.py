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
    tenant_id: str,
) -> str:
    """Hash the create request, tenant included (issue #648).

    Idempotency keys are caller-chosen, so two tenants can present the same
    one. Without the tenant in the hash, the second tenant's request matches
    the first's stored hash and is served as a REPLAY - it receives the other
    tenant's wave. With it, the hashes differ and the reuse surfaces as an
    idempotency conflict instead.

    This closes the cross-tenant replay. It is not full wave isolation: the
    wave aggregate has no tenant of its own, so a conflict still reveals that
    some other tenant used that key, and a wave can still be read or
    transitioned by wave id alone. That needs a tenant on the wave itself and
    is tracked separately.
    """

    return request_hash(
        {
            "tenant_id": tenant_id,
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
