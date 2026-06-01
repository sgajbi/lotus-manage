import pytest

from src.api.services import wave_service
from src.api.services.wave_errors import DpmWaveLookupError
from src.api.services.wave_lookup import get_wave_or_raise
from src.core.waves import DpmRebalanceWave


class _WaveRepository:
    def __init__(self, wave: DpmRebalanceWave | None) -> None:
        self.wave = wave
        self.requested_wave_ids: list[str] = []

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        self.requested_wave_ids.append(wave_id)
        return self.wave


def test_get_wave_or_raise_returns_loaded_wave() -> None:
    wave = DpmRebalanceWave.model_construct(wave_id="dwv_lookup", state="CREATED")
    repository = _WaveRepository(wave)

    loaded = get_wave_or_raise(
        wave_id="dwv_lookup",
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert loaded is wave
    assert repository.requested_wave_ids == ["dwv_lookup"]


def test_get_wave_or_raise_raises_governed_lookup_error_for_missing_wave() -> None:
    repository = _WaveRepository(None)

    with pytest.raises(DpmWaveLookupError) as exc_info:
        get_wave_or_raise(
            wave_id="dwv_missing",
            wave_repository=repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "DPM_WAVE_NOT_FOUND"
    assert exc_info.value.message == "Wave dwv_missing was not found."
    assert repository.requested_wave_ids == ["dwv_missing"]


def test_wave_service_preserves_private_lookup_alias() -> None:
    from src.api.services import wave_lookup

    assert wave_service._get_wave_or_raise is wave_lookup.get_wave_or_raise


def test_wave_lookup_exports_only_lookup_helper() -> None:
    from src.api.services import wave_lookup

    assert wave_lookup.__all__ == ["get_wave_or_raise"]
