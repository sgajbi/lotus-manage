"""Persistence contract for durable asynchronous wave simulation."""

from __future__ import annotations

from datetime import datetime
from contextlib import AbstractContextManager
from typing import Protocol

from src.core.common.derived_identity import derived_identity
from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem
from src.core.waves.repository import DpmWaveRepository
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemClaim,
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
)


class DpmWaveSimulationOperationConflictError(Exception):
    """Raised when immutable admission or lifecycle ownership conflicts."""


class DpmWaveSimulationOperationNotFoundError(Exception):
    """Raised when no tenant-owned operation is visible."""


def wave_simulation_idempotency_key(*, tenant_id: str, idempotency_key: str) -> str:
    """Namespace a caller-selected key without persisting or exposing it."""

    return derived_identity("wsi", tenant_id, idempotency_key)


class DpmWaveSimulationRepository(DpmWaveRepository, Protocol):
    def simulation_admission_guard(
        self, *, tenant_id: str, idempotency_key_hash: str
    ) -> AbstractContextManager[None]:
        """Serialize immutable source resolution and admission for one tenant/key."""

    def simulation_reconciliation_guard(
        self, *, tenant_id: str, wave_id: str
    ) -> AbstractContextManager[None]:
        """Serialize wave projection across repository instances, not financial calculations."""

    def admit_simulation_operation(
        self,
        *,
        operation: DpmWaveSimulationOperation,
        items: list[DpmWaveSimulationItemRecord],
        simulating_wave: DpmRebalanceWave,
    ) -> tuple[DpmWaveSimulationOperation, bool]:
        """Atomically persist operation/items plus SIMULATING wave, or replay."""

    def get_simulation_operation(
        self, *, tenant_id: str, operation_id: str
    ) -> DpmWaveSimulationOperation | None:
        """Return a tenant-owned operation without disclosing foreign identity."""

    def get_simulation_operation_by_idempotency(
        self, *, tenant_id: str, idempotency_key_hash: str
    ) -> DpmWaveSimulationOperation | None:
        """Return the tenant-owned operation for an already-derived key."""

    def list_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        limit: int,
        offset: int,
    ) -> DpmWaveSimulationItemPage:
        """Return stable ordinal paging scoped by tenant before pagination."""

    def simulation_item_counts(self, *, tenant_id: str, operation_id: str) -> dict[str, int]:
        """Return bounded status counts scoped by tenant."""

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
        """Claim bounded work while enforcing operation-wide concurrency."""

    def publish_simulation_item_result(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        result_item: DpmRebalanceWaveItem,
        completed_at: datetime,
    ) -> bool:
        """Publish success only for the current, unexpired fenced owner."""

    def publish_simulation_item_failure(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        error_code: str,
        error_message: str,
        retryable: bool,
        completed_at: datetime,
    ) -> bool:
        """Publish a typed failure only for the current fenced owner."""

    def retry_simulation_items(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        wave_item_ids: list[str] | None,
        retried_at: datetime,
    ) -> int:
        """Return retryable failures to pending without resetting attempts."""

    def cancel_simulation_operation(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        reason_code: str,
        cancelled_at: datetime,
    ) -> DpmWaveSimulationOperation | None:
        """Cancel unclaimed work while allowing fenced in-flight work to settle."""


__all__ = [
    "DpmWaveSimulationOperationConflictError",
    "DpmWaveSimulationOperationNotFoundError",
    "DpmWaveSimulationRepository",
    "wave_simulation_idempotency_key",
]
