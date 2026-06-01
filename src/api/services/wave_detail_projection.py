from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_supportability_payload import wave_supportability_payload
from src.core.waves import DpmRebalanceWave


def wave_detail_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    return {
        "wave": wave,
        "supportability": wave_supportability_payload(wave),
        "proof_pack_posture": proof_pack_posture_for_wave(wave=wave),
    }


def wave_items_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "items": wave.items,
        "aggregate_metrics": wave.aggregate_metrics,
    }


__all__ = ["wave_detail_payload", "wave_items_payload"]
