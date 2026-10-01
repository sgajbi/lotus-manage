from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from threading import Lock

from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem
from src.core.waves.repository import (
    DpmWaveAlreadyExistsError,
    DpmWaveCorrelationConflictError,
    DpmWaveIdempotencyConflictError,
    DpmWaveIdempotencyRecord,
    DpmWaveRepository,
    DpmWaveVersionConflictError,
    wave_idempotency_mapping_key,
)
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemClaim,
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
    derive_wave_simulation_operation_status,
)
from src.core.waves.simulation_repository import DpmWaveSimulationOperationConflictError
from src.infrastructure.waves.simulation_publication import DpmWaveSimulationPublicationMixin


class InMemoryDpmWaveRepository(DpmWaveSimulationPublicationMixin, DpmWaveRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._waves: dict[str, DpmRebalanceWave] = {}
        self._idempotency_index: dict[str, tuple[str, str | None]] = {}
        self._correlation_index: dict[tuple[str, str], str] = {}
        self._simulation_operations: dict[str, DpmWaveSimulationOperation] = {}
        self._simulation_operation_idempotency: dict[tuple[str, str], str] = {}
        self._simulation_operation_correlations: dict[tuple[str, str], str] = {}
        self._simulation_items: dict[tuple[str, str], DpmWaveSimulationItemRecord] = {}

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
            correlation_key = (tenant_id, wave.correlation_id)
            if correlation_key in self._correlation_index:
                raise DpmWaveCorrelationConflictError("DPM_WAVE_CORRELATION_CONFLICT")
            _index_idempotency_key(
                idempotency_index=self._idempotency_index,
                idempotency_key=mapping_key,
                wave_id=wave.wave_id,
                request_hash=request_hash,
            )
            # Stamped from the argument, so a caller cannot persist a wave
            # claiming one tenant while the record says another.
            _store_wave(waves=self._waves, wave=wave.model_copy(update={"tenant_id": tenant_id}))
            self._correlation_index[correlation_key] = wave.wave_id

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
        record = self.get_wave_idempotency_record(
            idempotency_key=idempotency_key, tenant_id=tenant_id
        )
        return None if record is None else record.wave

    def get_wave_idempotency_record(
        self, *, idempotency_key: str, tenant_id: str
    ) -> DpmWaveIdempotencyRecord | None:
        mapping_key = wave_idempotency_mapping_key(
            tenant_id=tenant_id, idempotency_key=idempotency_key
        )
        with self._lock:
            indexed = self._idempotency_index.get(mapping_key)
            if indexed is None:
                return None
            wave_id, request_hash = indexed
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
            return DpmWaveIdempotencyRecord(wave=deepcopy(wave), request_hash=request_hash)

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

    def admit_simulation_operation(
        self,
        *,
        operation: DpmWaveSimulationOperation,
        items: list[DpmWaveSimulationItemRecord],
        simulating_wave: DpmRebalanceWave,
    ) -> tuple[DpmWaveSimulationOperation, bool]:
        with self._lock:
            index_key = (operation.tenant_id, operation.idempotency_key_hash)
            existing_id = self._simulation_operation_idempotency.get(index_key)
            if existing_id is not None:
                existing = self._simulation_operations[existing_id]
                if existing.request_hash != operation.request_hash:
                    raise DpmWaveSimulationOperationConflictError(
                        "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT"
                    )
                return deepcopy(existing), True
            correlation_key = (operation.tenant_id, operation.correlation_id)
            if correlation_key in self._simulation_operation_correlations:
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_CORRELATION_CONFLICT"
                )
            wave = self._waves.get(operation.wave_id)
            if wave is None or wave.tenant_id != operation.tenant_id:
                raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_WAVE_NOT_FOUND")
            if wave.version != operation.admitted_wave_version:
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT"
                )
            _validate_simulation_admission_items(operation=operation, items=items, wave=wave)
            if (
                simulating_wave.wave_id != wave.wave_id
                or simulating_wave.tenant_id != operation.tenant_id
                or simulating_wave.state != "SIMULATING"
                or simulating_wave.version != wave.version + 1
            ):
                raise DpmWaveSimulationOperationConflictError(
                    "DPM_WAVE_SIMULATION_TRANSITION_CONFLICT"
                )
            self._simulation_operations[operation.operation_id] = deepcopy(operation)
            self._simulation_operation_idempotency[index_key] = operation.operation_id
            self._simulation_operation_correlations[correlation_key] = operation.operation_id
            for item in items:
                self._simulation_items[(operation.operation_id, item.wave_item_id)] = deepcopy(item)
            self._waves[wave.wave_id] = deepcopy(simulating_wave)
            return deepcopy(operation), False

    def get_simulation_operation(
        self, *, tenant_id: str, operation_id: str
    ) -> DpmWaveSimulationOperation | None:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return None
            return deepcopy(operation)

    def get_simulation_operation_by_idempotency(
        self, *, tenant_id: str, idempotency_key_hash: str
    ) -> DpmWaveSimulationOperation | None:
        with self._lock:
            operation_id = self._simulation_operation_idempotency.get(
                (tenant_id, idempotency_key_hash)
            )
            if operation_id is None:
                return None
            return deepcopy(self._simulation_operations[operation_id])

    def list_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        limit: int,
        offset: int,
    ) -> DpmWaveSimulationItemPage:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return DpmWaveSimulationItemPage(items=[], total_count=0, next_offset=None)
            items = sorted(
                (
                    item
                    for (stored_operation_id, _), item in self._simulation_items.items()
                    if stored_operation_id == operation_id and item.tenant_id == tenant_id
                ),
                key=lambda item: (item.ordinal, item.wave_item_id),
            )
            page = items[offset : offset + limit]
            next_offset = offset + len(page) if offset + len(page) < len(items) else None
            return DpmWaveSimulationItemPage(
                items=deepcopy(page), total_count=len(items), next_offset=next_offset
            )

    def simulation_item_counts(self, *, tenant_id: str, operation_id: str) -> dict[str, int]:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return {}
            counts = Counter(
                item.status
                for item in _simulation_items_for_operation(
                    items=self._simulation_items,
                    operation_id=operation_id,
                    tenant_id=tenant_id,
                )
            )
            return {
                status: counts.get(status, 0)
                for status in ("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED")
            }

    def claim_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        worker_id: str,
        limit: int,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> list[DpmWaveSimulationItemClaim]:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return []
            if operation.status in {"CANCEL_REQUESTED", "CANCELLED", "SUCCEEDED", "FAILED"}:
                return []
            owned_items = _simulation_items_for_operation(
                items=self._simulation_items,
                operation_id=operation_id,
                tenant_id=tenant_id,
            )
            active_count = sum(
                item.status == "RUNNING"
                and item.lease_expires_at is not None
                and item.lease_expires_at > claimed_at
                for item in owned_items
            )
            capacity = max(0, operation.max_concurrency - active_count)
            claim_limit = min(max(0, limit), capacity)
            candidates = [
                item
                for item in owned_items
                if item.status == "PENDING"
                or (
                    item.status == "RUNNING"
                    and item.lease_expires_at is not None
                    and item.lease_expires_at <= claimed_at
                )
            ]
            claims: list[DpmWaveSimulationItemClaim] = []
            for item in sorted(candidates, key=lambda row: (row.ordinal, row.wave_item_id))[
                :claim_limit
            ]:
                recovery_exhausted = item.attempt_count >= operation.max_attempts
                attempt_count = item.attempt_count + (0 if recovery_exhausted else 1)
                claim_generation = item.claim_generation + 1
                claim_token = f"wsc_{uuid.uuid4().hex}"
                updated = item.model_copy(
                    update={
                        "status": "RUNNING",
                        "attempt_count": attempt_count,
                        "claim_generation": claim_generation,
                        "worker_id": worker_id,
                        "claim_token": claim_token,
                        "claimed_at": claimed_at,
                        "lease_expires_at": lease_expires_at,
                        "updated_at": claimed_at,
                    }
                )
                self._simulation_items[(operation_id, item.wave_item_id)] = updated
                claims.append(
                    DpmWaveSimulationItemClaim(
                        operation_id=operation_id,
                        tenant_id=tenant_id,
                        wave_id=item.wave_id,
                        wave_item_id=item.wave_item_id,
                        portfolio_id=item.portfolio_id,
                        input_payload=deepcopy(item.input_payload),
                        input_hash=item.input_hash,
                        source_identity_hash=item.source_identity_hash,
                        worker_id=worker_id,
                        claim_token=claim_token,
                        claim_generation=claim_generation,
                        attempt_count=attempt_count,
                        lease_expires_at=lease_expires_at,
                        recovery_exhausted=recovery_exhausted,
                    )
                )
            self._refresh_simulation_operation_status(
                operation_id=operation_id, updated_at=claimed_at
            )
            return claims

    def retry_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        wave_item_ids: list[str] | None,
        retried_at: datetime,
    ) -> int:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if (
                operation is None
                or operation.tenant_id != tenant_id
                or operation.cancel_reason_code
            ):
                return 0
            requested = None if wave_item_ids is None else set(wave_item_ids)
            retried = 0
            for item in _simulation_items_for_operation(
                items=self._simulation_items,
                operation_id=operation_id,
                tenant_id=tenant_id,
            ):
                if requested is not None and item.wave_item_id not in requested:
                    continue
                if not item.retryable or item.status != "FAILED":
                    continue
                if item.attempt_count >= operation.max_attempts:
                    continue
                self._simulation_items[(operation_id, item.wave_item_id)] = item.model_copy(
                    update={
                        "status": "PENDING",
                        "worker_id": None,
                        "claim_token": None,
                        "claimed_at": None,
                        "lease_expires_at": None,
                        "error_code": None,
                        "error_message": None,
                        "retryable": False,
                        "completed_at": None,
                        "updated_at": retried_at,
                    }
                )
                retried += 1
            self._refresh_simulation_operation_status(
                operation_id=operation_id, updated_at=retried_at
            )
            return retried

    def cancel_simulation_operation(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        reason_code: str,
        cancelled_at: datetime,
    ) -> DpmWaveSimulationOperation | None:
        with self._lock:
            operation = self._simulation_operations.get(operation_id)
            if operation is None or operation.tenant_id != tenant_id:
                return None
            if operation.cancel_reason_code is not None or operation.status in {
                "SUCCEEDED",
                "FAILED",
                "CANCELLED",
            }:
                return deepcopy(operation)
            operation = operation.model_copy(
                update={"cancel_reason_code": reason_code, "updated_at": cancelled_at}
            )
            self._simulation_operations[operation_id] = operation
            for item in _simulation_items_for_operation(
                items=self._simulation_items,
                operation_id=operation_id,
                tenant_id=tenant_id,
            ):
                if item.status in {"PENDING", "FAILED"}:
                    self._simulation_items[(operation_id, item.wave_item_id)] = item.model_copy(
                        update={
                            "status": "CANCELLED",
                            "retryable": False,
                            "completed_at": cancelled_at,
                            "updated_at": cancelled_at,
                        }
                    )
            return deepcopy(
                self._refresh_simulation_operation_status(
                    operation_id=operation_id, updated_at=cancelled_at
                )
            )

    def _publish_simulation_item_terminal(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        completed_at: datetime,
        status: str,
        result_item: DpmRebalanceWaveItem | None,
        error_code: str | None,
        error_message: str | None,
        retryable: bool,
    ) -> bool:
        with self._lock:
            item = self._simulation_items.get((claim.operation_id, claim.wave_item_id))
            if (
                item is None
                or item.tenant_id != claim.tenant_id
                or item.status != "RUNNING"
                or item.claim_token != claim.claim_token
                or item.claim_generation != claim.claim_generation
                or item.lease_expires_at is None
                or completed_at > item.lease_expires_at
            ):
                return False
            self._simulation_items[(claim.operation_id, claim.wave_item_id)] = item.model_copy(
                update={
                    "status": status,
                    "result_item": result_item,
                    "error_code": error_code,
                    "error_message": error_message,
                    "retryable": retryable,
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                }
            )
            self._refresh_simulation_operation_status(
                operation_id=claim.operation_id, updated_at=completed_at
            )
            return True

    def _refresh_simulation_operation_status(
        self, *, operation_id: str, updated_at: datetime
    ) -> DpmWaveSimulationOperation:
        operation = self._simulation_operations[operation_id]
        items = _simulation_items_for_operation(
            items=self._simulation_items,
            operation_id=operation_id,
            tenant_id=operation.tenant_id,
        )
        status = derive_wave_simulation_operation_status(operation=operation, items=items)
        updated = operation.model_copy(update={"status": status, "updated_at": updated_at})
        self._simulation_operations[operation_id] = updated
        return updated


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


def _validate_simulation_admission_items(
    *,
    operation: DpmWaveSimulationOperation,
    items: list[DpmWaveSimulationItemRecord],
    wave: DpmRebalanceWave,
) -> None:
    wave_items = {item.wave_item_id: item for item in wave.items}
    item_ids = [item.wave_item_id for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_DUPLICATE_ITEM")
    ordinals = [item.ordinal for item in items]
    if sorted(ordinals) != list(range(len(items))):
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_ITEM_ORDINAL_CONFLICT")
    for item in items:
        wave_item = wave_items.get(item.wave_item_id)
        if (
            item.operation_id != operation.operation_id
            or item.tenant_id != operation.tenant_id
            or item.wave_id != operation.wave_id
            or wave_item is None
            or wave_item.portfolio_id != item.portfolio_id
        ):
            raise DpmWaveSimulationOperationConflictError(
                "DPM_WAVE_SIMULATION_ITEM_IDENTITY_CONFLICT"
            )


def _simulation_items_for_operation(
    *,
    items: dict[tuple[str, str], DpmWaveSimulationItemRecord],
    operation_id: str,
    tenant_id: str,
) -> list[DpmWaveSimulationItemRecord]:
    return [
        item
        for (stored_operation_id, _), item in items.items()
        if stored_operation_id == operation_id and item.tenant_id == tenant_id
    ]
