import hashlib
import json
import uuid

from src.core.waves import DpmWaveHandoffRef


def build_handoff_ref(
    *,
    wave_id: str,
    item_ids: list[str],
    actor_id: str,
    reason_code: str,
    correlation_id: str,
    comment: str | None,
) -> DpmWaveHandoffRef:
    handoff_ref_id = f"dwh_{uuid.uuid4().hex[:12]}"
    metadata: dict[str, object] = {
        "handoff_contract": "RFC-0041_INTERNAL_OPERATIONS_HANDOFF_V1",
        "handoff_boundary": "NO_EXTERNAL_EXECUTION",
        "item_count": len(item_ids),
    }
    if comment:
        metadata["comment"] = comment
    content_hash = handoff_content_hash(
        {
            "handoff_ref_id": handoff_ref_id,
            "wave_id": wave_id,
            "item_ids": item_ids,
            "actor_id": actor_id,
            "reason_code": reason_code,
            "correlation_id": correlation_id,
            "external_execution_claimed": False,
            "metadata": metadata,
        }
    )
    return DpmWaveHandoffRef(
        handoff_ref_id=handoff_ref_id,
        wave_id=wave_id,
        item_ids=item_ids,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        external_execution_claimed=False,
        content_hash=content_hash,
        metadata=metadata,
    )


def handoff_content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


__all__ = ["build_handoff_ref", "handoff_content_hash"]
