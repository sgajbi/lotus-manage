import pytest

from src.api.services import wave_service
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_persistence import save_wave_or_raise, update_wave_or_raise
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveVersionConflictError,
)


class _WaveRepository:
    def __init__(
        self,
        *,
        save_conflict: Exception | None = None,
        update_conflict: bool = False,
    ) -> None:
        self.save_conflict = save_conflict
        self.update_conflict = update_conflict
        self.saved_wave: DpmRebalanceWave | None = None
        self.idempotency_key: str | None = None
        self.request_hash: str | None = None
        self.updated_wave: DpmRebalanceWave | None = None
        self.expected_version: int | None = None

    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
    ) -> None:
        if self.save_conflict is not None:
            raise self.save_conflict
        self.saved_wave = wave
        self.idempotency_key = idempotency_key
        self.request_hash = request_hash

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        if self.update_conflict:
            raise DpmWaveVersionConflictError("expected version mismatch")
        self.updated_wave = wave
        self.expected_version = expected_version


def test_save_wave_or_raise_persists_idempotent_create_request() -> None:
    wave = DpmRebalanceWave.model_construct(wave_id="dwv_save", version=1)
    repository = _WaveRepository()

    save_wave_or_raise(
        wave_repository=repository,  # type: ignore[arg-type]
        wave=wave,
        idempotency_key="idem-save",
        request_hash="sha256:request",
    )

    assert repository.saved_wave is wave
    assert repository.idempotency_key == "idem-save"
    assert repository.request_hash == "sha256:request"


@pytest.mark.parametrize(
    "conflict",
    [
        DpmWaveAlreadyExistsError("wave id already exists"),
        DpmWaveIdempotencyConflictError("idempotency key reused"),
    ],
)
def test_save_wave_or_raise_translates_create_conflicts(conflict: Exception) -> None:
    wave = DpmRebalanceWave.model_construct(wave_id="dwv_save", version=1)

    with pytest.raises(DpmWaveValidationError) as exc_info:
        save_wave_or_raise(
            wave_repository=_WaveRepository(save_conflict=conflict),  # type: ignore[arg-type]
            wave=wave,
            idempotency_key="idem-save",
            request_hash="sha256:request",
        )

    assert exc_info.value.code == "WAVE_CREATE_CONFLICT"
    assert exc_info.value.message == str(conflict)


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
            wave_repository=_WaveRepository(update_conflict=True),  # type: ignore[arg-type]
            wave=wave,
            expected_version=3,
        )

    assert exc_info.value.code == "DPM_WAVE_VERSION_CONFLICT"
    assert exc_info.value.message == "expected version mismatch"


def test_wave_service_uses_shared_update_helper_alias() -> None:
    from src.api.services import wave_persistence

    assert wave_service._save_wave_or_raise is wave_persistence.save_wave_or_raise
    assert wave_service._update_wave_or_raise is wave_persistence.update_wave_or_raise


def test_wave_persistence_exports_only_write_helpers() -> None:
    from src.api.services import wave_persistence

    assert wave_persistence.__all__ == ["save_wave_or_raise", "update_wave_or_raise"]
