from src.api.services.wave_boundary_evidence import (
    client_communication_boundary,
    external_execution_boundary,
)
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def _proof_pack_ref(item: DpmRebalanceWaveItem) -> dict[str, object]:
    return {
        "wave_item_id": item.wave_item_id,
        "proof_pack_id": item.proof_pack_id,
        "item_state": item.state,
        "proof_pack_state": item.diagnostics.get("proof_pack_state"),
        "selected_alternative_id": item.selected_alternative_id,
    }


def _proof_pack_refs(wave: DpmRebalanceWave) -> list[dict[str, object]]:
    return [
        _proof_pack_ref(item)
        for item in wave.items
        if item.proof_pack_id is not None or item.diagnostics.get("proof_pack_state") is not None
    ]


def _ready_proof_pack_count(wave: DpmRebalanceWave) -> int:
    return sum(
        1
        for item in wave.items
        if item.proof_pack_id is not None and item.diagnostics.get("proof_pack_state") != "DEGRADED"
    )


def _degraded_proof_pack_count(wave: DpmRebalanceWave) -> int:
    return sum(1 for item in wave.items if item.diagnostics.get("proof_pack_state") == "DEGRADED")


def _external_execution_claimed(wave: DpmRebalanceWave) -> bool:
    return any(handoff.external_execution_claimed for handoff in wave.handoff_refs)


def proof_pack_posture_for_wave(*, wave: DpmRebalanceWave) -> dict[str, object]:
    proof_pack_refs = _proof_pack_refs(wave)
    external_execution_claimed = _external_execution_claimed(wave)
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "item_count": len(wave.items),
        "linked_item_count": sum(1 for item in wave.items if item.proof_pack_id is not None),
        "ready_proof_pack_count": _ready_proof_pack_count(wave),
        "degraded_proof_pack_count": _degraded_proof_pack_count(wave),
        "proof_pack_refs": proof_pack_refs,
        "handoff_refs": wave.handoff_refs,
        "external_execution_claimed": external_execution_claimed,
        "external_execution_boundary": external_execution_boundary(
            external_execution_claimed=external_execution_claimed
        ).model_dump(mode="json"),
        "client_communication_boundary": client_communication_boundary().model_dump(mode="json"),
    }


__all__ = ["proof_pack_posture_for_wave"]
