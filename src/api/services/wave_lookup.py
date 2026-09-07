from src.api.services.wave_errors import DpmWaveLookupError
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def get_wave_or_raise(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
) -> DpmRebalanceWave:
    """Load one of THIS TENANT's waves, refusing before any caller acts on it.

    The refusal for another tenant's wave is deliberately the same
    DPM_WAVE_NOT_FOUND as for an absent one (issue #677). A distinguishable
    error would confirm the id exists and belongs to somebody, which is the
    cross-tenant information the fence exists to withhold.
    """

    wave = wave_repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    return wave


__all__ = ["get_wave_or_raise"]
