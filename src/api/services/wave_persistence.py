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
    tenant_id: str,
) -> None:
    try:
        wave_repository.save_wave(
            wave=wave,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            tenant_id=tenant_id,
        )
    except (DpmWaveAlreadyExistsError, DpmWaveIdempotencyConflictError) as exc:
        raise DpmWaveValidationError("WAVE_CREATE_CONFLICT", str(exc)) from exc


def update_wave_or_raise(
    *,
    wave_repository: DpmWaveRepository,
    wave: DpmRebalanceWave,
    expected_version: int,
    tenant_id: str,
) -> None:
    """Persist a wave update for this tenant.

    The tenant reaches the repository so it can ride in the UPDATE predicate
    rather than being checked before it (issue #677). A wave owned by another
    tenant matches no row and surfaces as the same version conflict as a stale
    expected_version - the caller cannot tell the two apart, which is what
    stops the write path being used to probe for foreign wave ids.
    """

    try:
        wave_repository.update_wave(
            wave=wave, expected_version=expected_version, tenant_id=tenant_id
        )
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc


__all__ = ["save_wave_or_raise", "update_wave_or_raise"]
