from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.core.waves.models import DpmRebalanceWave
from src.core.waves.repository import (
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveRepository,
    DpmWaveVersionConflictError,
)


class InMemoryDpmWaveRepository(DpmWaveRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._waves: dict[str, DpmRebalanceWave] = {}
        self._idempotency_index: dict[str, tuple[str, str | None]] = {}

    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
    ) -> None:
        with self._lock:
            if idempotency_key is not None:
                existing = self._idempotency_index.get(idempotency_key)
                if existing is not None and existing != (wave.wave_id, request_hash):
                    raise DpmWaveIdempotencyConflictError("DPM_WAVE_IDEMPOTENCY_CONFLICT")
            if wave.wave_id in self._waves:
                raise DpmWaveAlreadyExistsError("DPM_WAVE_ALREADY_EXISTS")
            if idempotency_key is not None:
                self._idempotency_index[idempotency_key] = (wave.wave_id, request_hash)
            self._waves[wave.wave_id] = deepcopy(wave)

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        with self._lock:
            wave = self._waves.get(wave_id)
            return deepcopy(wave) if wave is not None else None

    def get_wave_by_idempotency(self, *, idempotency_key: str) -> DpmRebalanceWave | None:
        with self._lock:
            indexed = self._idempotency_index.get(idempotency_key)
            if indexed is None:
                return None
            wave_id, _request_hash = indexed
            wave = self._waves.get(wave_id)
            return deepcopy(wave) if wave is not None else None

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        with self._lock:
            current = self._waves.get(wave.wave_id)
            if current is None or current.version != expected_version:
                raise DpmWaveVersionConflictError("DPM_WAVE_VERSION_CONFLICT")
            self._waves[wave.wave_id] = deepcopy(wave)
