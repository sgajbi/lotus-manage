from src.api.services.wave_errors import DpmWaveLookupError
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def get_wave_or_raise(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    wave = wave_repository.get_wave(wave_id=wave_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    return wave


__all__ = ["get_wave_or_raise"]
