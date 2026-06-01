from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveRepository,
    DpmWaveVersionConflictError,
)


def save_wave_or_raise(
    *,
    wave_repository: DpmWaveRepository,
    wave: DpmRebalanceWave,
    idempotency_key: str | None,
    request_hash: str | None,
) -> None:
    try:
        wave_repository.save_wave(
            wave=wave,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except (DpmWaveAlreadyExistsError, DpmWaveIdempotencyConflictError) as exc:
        raise DpmWaveValidationError("WAVE_CREATE_CONFLICT", str(exc)) from exc


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


__all__ = ["save_wave_or_raise", "update_wave_or_raise"]
