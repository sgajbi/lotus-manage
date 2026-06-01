import pytest

from src.api.services import wave_service
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_persistence import update_wave_or_raise
from src.core.waves import DpmRebalanceWave, DpmWaveVersionConflictError


class _WaveRepository:
    def __init__(self, *, conflict: bool = False) -> None:
        self.conflict = conflict
        self.updated_wave: DpmRebalanceWave | None = None
        self.expected_version: int | None = None

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        if self.conflict:
            raise DpmWaveVersionConflictError("expected version mismatch")
        self.updated_wave = wave
        self.expected_version = expected_version


def test_update_wave_or_raise_persists_with_expected_version() -> None:
    wave = DpmRebalanceWave.model_construct(wave_id="dwv_update", version=4)
    repository = _WaveRepository()

    update_wave_or_raise(
        wave_repository=repository,  # type: ignore[arg-type]
        wave=wave,
        expected_version=3,
    )

    assert repository.updated_wave is wave
    assert repository.expected_version == 3


def test_update_wave_or_raise_translates_version_conflict() -> None:
    wave = DpmRebalanceWave.model_construct(wave_id="dwv_update", version=4)

    with pytest.raises(DpmWaveValidationError) as exc_info:
        update_wave_or_raise(
            wave_repository=_WaveRepository(conflict=True),  # type: ignore[arg-type]
            wave=wave,
            expected_version=3,
        )

    assert exc_info.value.code == "DPM_WAVE_VERSION_CONFLICT"
    assert exc_info.value.message == "expected version mismatch"


def test_wave_service_uses_shared_update_helper_alias() -> None:
    from src.api.services import wave_persistence

    assert wave_service._update_wave_or_raise is wave_persistence.update_wave_or_raise


def test_wave_persistence_exports_only_update_helper() -> None:
    from src.api.services import wave_persistence

    assert wave_persistence.__all__ == ["update_wave_or_raise"]
