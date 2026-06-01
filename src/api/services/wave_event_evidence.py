import hashlib
import json
import uuid

from src.core.waves import DpmRebalanceWaveEvent, WaveState


def build_wave_event(
    *,
    wave_id: str,
    from_state: WaveState,
    to_state: WaveState,
    actor_id: str,
    correlation_id: str,
    reason_code: str,
    metadata: dict[str, object],
    event_type: str = "STATE_TRANSITION",
) -> DpmRebalanceWaveEvent:
    return DpmRebalanceWaveEvent(
        event_id=f"dwe_{uuid.uuid4().hex[:12]}",
        wave_id=wave_id,
        from_state=from_state,
        to_state=to_state,
        event_type=event_type,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        metadata=metadata,
    )


def request_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def idempotency_key_hash(idempotency_key: str) -> str:
    return hashlib.sha256(idempotency_key.encode()).hexdigest()


__all__ = ["build_wave_event", "idempotency_key_hash", "request_hash"]
