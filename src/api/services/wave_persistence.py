from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import DpmRebalanceWave, DpmWaveRepository, DpmWaveVersionConflictError


def update_wave_or_raise(
    *,
    wave_repository: DpmWaveRepository,
    wave: DpmRebalanceWave,
    expected_version: int,
) -> None:
    try:
        wave_repository.update_wave(wave=wave, expected_version=expected_version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc


__all__ = ["update_wave_or_raise"]
