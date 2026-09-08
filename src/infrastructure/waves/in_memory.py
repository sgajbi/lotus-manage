from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Iterable

from src.core.waves.models import DpmRebalanceWave
from src.core.waves.repository import (
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveRepository,
    DpmWaveVersionConflictError,
    wave_idempotency_mapping_key,
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
        tenant_id: str,
    ) -> None:
        # The caller's key is namespaced by tenant before it is stored, so two
        # tenants presenting one key hold two independent mappings instead of
        # colliding on this index (issue #648).
        mapping_key = (
            None
            if idempotency_key is None
            else wave_idempotency_mapping_key(tenant_id=tenant_id, idempotency_key=idempotency_key)
        )
        with self._lock:
            _raise_if_idempotency_conflict(
                idempotency_index=self._idempotency_index,
                idempotency_key=mapping_key,
                wave_id=wave.wave_id,
                request_hash=request_hash,
            )
            _raise_if_wave_exists(waves=self._waves, wave_id=wave.wave_id)
            _index_idempotency_key(
                idempotency_index=self._idempotency_index,
                idempotency_key=mapping_key,
                wave_id=wave.wave_id,
                request_hash=request_hash,
            )
            # Stamped from the argument, so a caller cannot persist a wave
            # claiming one tenant while the record says another.
            _store_wave(waves=self._waves, wave=wave.model_copy(update={"tenant_id": tenant_id}))

    def get_wave(self, *, wave_id: str, tenant_id: str) -> DpmRebalanceWave | None:
        with self._lock:
            wave = self._waves.get(wave_id)
            # None rather than a distinguishable refusal: telling a caller that
            # the id exists but is someone else's is itself cross-tenant
            # information (issue #677). A wave with no tenant - persisted before
            # the fence - matches no caller and is quarantined, not public.
            if wave is None or wave.tenant_id != tenant_id:
                return None
            return deepcopy(wave)

    def get_wave_by_idempotency(
        self, *, idempotency_key: str, tenant_id: str
    ) -> DpmRebalanceWave | None:
        # Previously this looked up the caller's raw key, so a caller presenting
        # another tenant's caller-chosen key was served that tenant's wave
        # (issue #648). Deriving the mapping key means another tenant's mapping
        # is simply not found, rather than found and refused - a refusal would
        # disclose that some other tenant holds that key.
        mapping_key = wave_idempotency_mapping_key(
            tenant_id=tenant_id, idempotency_key=idempotency_key
        )
        with self._lock:
            indexed = self._idempotency_index.get(mapping_key)
            if indexed is None:
                return None
            wave_id, _request_hash = indexed
            wave = self._waves.get(wave_id)
            # The mapping's tenant is not the aggregate's tenant. Migration
            # 0027 added the wave column nullable with no backfill, so between
            # 0026 and 0027 a wave can carry NO tenant while its tenant-derived
            # mapping survives. Checking only the mapping returned that
            # quarantined wave as a successful replay - the one path that
            # bypassed the fence every direct read enforces, and it would have
            # handed the caller an aggregate nobody owns.
            #
            # Caller, mapping and aggregate must agree. A disagreement returns
            # None rather than raising: a distinct error would disclose that
            # the key resolves to something, and the quarantined row is left
            # exactly as it is - not stamped, not resurrected.
            if wave is None or wave.tenant_id != tenant_id:
                return None
            return deepcopy(wave)

    def list_waves(
        self,
        *,
        tenant_id: str,
        state: str | None = None,
        trigger_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmRebalanceWave]:
        with self._lock:
            # Tenant applied BEFORE paging, not after: filtering a page would
            # let another tenant's waves consume the limit and silently shorten
            # this caller's results (issue #677).
            owned = [wave for wave in self._waves.values() if wave.tenant_id == tenant_id]
            waves = _filtered_waves(
                waves=owned,
                state=state,
                trigger_type=trigger_type,
                as_of_date=as_of_date,
            )
            return _copied_wave_page(waves=waves, limit=limit, offset=offset)

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int, tenant_id: str) -> None:
        with self._lock:
            current = self._waves.get(wave.wave_id)
            # The tenant is part of the same guarded comparison as the version,
            # so there is no window between checking ownership and writing. A
            # foreign wave raises the SAME error as a stale version, on purpose:
            # a distinct error would let a caller probe for wave ids it does not
            # own (issue #677).
            if (
                current is None
                or current.version != expected_version
                or current.tenant_id != tenant_id
            ):
                raise DpmWaveVersionConflictError("DPM_WAVE_VERSION_CONFLICT")
            self._waves[wave.wave_id] = deepcopy(wave.model_copy(update={"tenant_id": tenant_id}))


def _raise_if_idempotency_conflict(
    *,
    idempotency_index: dict[str, tuple[str, str | None]],
    idempotency_key: str | None,
    wave_id: str,
    request_hash: str | None,
) -> None:
    if idempotency_key is None:
        return
    existing = idempotency_index.get(idempotency_key)
    if existing is not None and existing != (wave_id, request_hash):
        raise DpmWaveIdempotencyConflictError("DPM_WAVE_IDEMPOTENCY_CONFLICT")


def _raise_if_wave_exists(
    *,
    waves: dict[str, DpmRebalanceWave],
    wave_id: str,
) -> None:
    if wave_id in waves:
        raise DpmWaveAlreadyExistsError("DPM_WAVE_ALREADY_EXISTS")


def _index_idempotency_key(
    *,
    idempotency_index: dict[str, tuple[str, str | None]],
    idempotency_key: str | None,
    wave_id: str,
    request_hash: str | None,
) -> None:
    if idempotency_key is not None:
        idempotency_index[idempotency_key] = (wave_id, request_hash)


def _store_wave(
    *,
    waves: dict[str, DpmRebalanceWave],
    wave: DpmRebalanceWave,
) -> None:
    waves[wave.wave_id] = deepcopy(wave)


def _filtered_waves(
    *,
    waves: Iterable[DpmRebalanceWave],
    state: str | None,
    trigger_type: str | None,
    as_of_date: str | None,
) -> list[DpmRebalanceWave]:
    matched_waves = [
        wave
        for wave in waves
        if _wave_matches_filters(
            wave=wave,
            state=state,
            trigger_type=trigger_type,
            as_of_date=as_of_date,
        )
    ]
    return sorted(matched_waves, key=_wave_sort_key, reverse=True)


def _wave_matches_filters(
    *,
    wave: DpmRebalanceWave,
    state: str | None,
    trigger_type: str | None,
    as_of_date: str | None,
) -> bool:
    return (
        _wave_state_matches(wave=wave, state=state)
        and _wave_trigger_type_matches(wave=wave, trigger_type=trigger_type)
        and _wave_as_of_date_matches(wave=wave, as_of_date=as_of_date)
    )


def _wave_state_matches(*, wave: DpmRebalanceWave, state: str | None) -> bool:
    return state is None or wave.state == state


def _wave_trigger_type_matches(
    *,
    wave: DpmRebalanceWave,
    trigger_type: str | None,
) -> bool:
    return trigger_type is None or wave.trigger.trigger_type == trigger_type


def _wave_as_of_date_matches(*, wave: DpmRebalanceWave, as_of_date: str | None) -> bool:
    return as_of_date is None or wave.as_of_date == as_of_date


def _wave_sort_key(wave: DpmRebalanceWave) -> tuple[object, str]:
    return wave.created_at, wave.wave_id


def _copied_wave_page(
    *,
    waves: list[DpmRebalanceWave],
    limit: int,
    offset: int,
) -> list[DpmRebalanceWave]:
    return deepcopy(waves[offset : offset + limit])
