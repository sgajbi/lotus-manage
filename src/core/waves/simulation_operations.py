"""Durable, fenced execution records for asynchronous wave simulation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from src.core.waves.models import DpmRebalanceWaveItem
from src.core.risk_authority.context import RiskAuthorityContext

WaveSimulationOperationStatus = Literal[
    "PENDING",
    "RUNNING",
    "PARTIALLY_COMPLETED",
    "SUCCEEDED",
    "FAILED",
    "CANCEL_REQUESTED",
    "CANCELLED",
]

WaveSimulationItemStatus = Literal[
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
]


class DpmWaveSimulationOperation(BaseModel):
    """Immutable admission plus mutable lifecycle for one wave simulation."""

    operation_id: str
    tenant_id: str
    wave_id: str
    request_hash: str
    idempotency_key_hash: str
    correlation_id: str
    actor_id: str
    risk_authority_context: RiskAuthorityContext | None = Field(default=None, frozen=True)
    risk_authority_context_hash: str | None = Field(default=None, frozen=True)
    source_identity_hash: str
    admitted_wave_version: int = Field(ge=1)
    methods: list[str] = Field(default_factory=list)
    max_concurrency: int = Field(ge=1, le=64)
    max_attempts: int = Field(ge=1, le=10)
    status: WaveSimulationOperationStatus = "PENDING"
    cancel_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_risk_authority_custody(self) -> Self:
        context = self.risk_authority_context
        if context is None:
            if self.risk_authority_context_hash is not None:
                raise ValueError("Missing retained Risk authority context")
            return self
        if (
            context.fingerprint() != self.risk_authority_context_hash
            or context.actor_id != self.actor_id
            or context.tenant_id != self.tenant_id
            or context.correlation_id != self.correlation_id
        ):
            raise ValueError("Retained Risk authority context conflicts with operation custody")
        return self


class DpmWaveSimulationItemRecord(BaseModel):
    """Durable work identity, checkpoint, and fenced ownership for one item."""

    operation_id: str
    tenant_id: str
    wave_id: str
    wave_item_id: str
    ordinal: int = Field(ge=0)
    portfolio_id: str
    input_payload: dict[str, object]
    input_hash: str
    source_identity_hash: str
    status: WaveSimulationItemStatus = "PENDING"
    attempt_count: int = Field(default=0, ge=0)
    claim_generation: int = Field(default=0, ge=0)
    worker_id: str | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    result_item: DpmRebalanceWaveItem | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    completed_at: datetime | None = None
    updated_at: datetime


class DpmWaveSimulationItemClaim(BaseModel):
    """Opaque fenced claim handed to a worker outside the claim transaction."""

    operation_id: str
    tenant_id: str
    wave_id: str
    wave_item_id: str
    portfolio_id: str
    input_payload: dict[str, object]
    input_hash: str
    source_identity_hash: str
    worker_id: str
    claim_token: str
    claim_generation: int = Field(ge=1)
    attempt_count: int = Field(ge=1)
    lease_expires_at: datetime
    recovery_exhausted: bool = False


class DpmWaveSimulationItemPage(BaseModel):
    items: list[DpmWaveSimulationItemRecord]
    total_count: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)


def wave_simulation_item_is_retryable(
    *, operation: DpmWaveSimulationOperation, item: DpmWaveSimulationItemRecord
) -> bool:
    """A failed disposition is outstanding only while its immutable attempt budget permits retry."""
    return (
        item.status == "FAILED" and item.retryable and item.attempt_count < operation.max_attempts
    )


def derive_wave_simulation_operation_status(
    *,
    operation: DpmWaveSimulationOperation,
    items: list[DpmWaveSimulationItemRecord],
) -> WaveSimulationOperationStatus:
    """Derive lifecycle status from durable item checkpoints."""

    statuses = [item.status for item in items]
    return derive_wave_simulation_operation_status_from_counts(
        operation=operation,
        total_count=len(statuses),
        pending_count=statuses.count("PENDING"),
        running_count=statuses.count("RUNNING"),
        succeeded_count=statuses.count("SUCCEEDED"),
        failed_count=statuses.count("FAILED"),
        cancelled_count=statuses.count("CANCELLED"),
        retry_waiting_count=sum(
            wave_simulation_item_is_retryable(operation=operation, item=item) for item in items
        ),
    )


def derive_wave_simulation_operation_status_from_counts(
    *,
    operation: DpmWaveSimulationOperation,
    total_count: int,
    pending_count: int,
    running_count: int,
    succeeded_count: int,
    failed_count: int,
    cancelled_count: int,
    retry_waiting_count: int,
) -> WaveSimulationOperationStatus:
    """Derive lifecycle status from bounded aggregate counts."""

    if operation.cancel_reason_code is not None:
        return "CANCEL_REQUESTED" if running_count else "CANCELLED"
    if running_count:
        return "RUNNING"
    if pending_count or retry_waiting_count:
        return "PARTIALLY_COMPLETED" if succeeded_count or failed_count else "PENDING"
    if succeeded_count == total_count:
        return "SUCCEEDED"
    if failed_count == total_count:
        return "FAILED"
    if succeeded_count or failed_count:
        return "PARTIALLY_COMPLETED"
    return "CANCELLED" if cancelled_count == total_count else "PENDING"


__all__ = [
    "DpmWaveSimulationItemClaim",
    "DpmWaveSimulationItemPage",
    "DpmWaveSimulationItemRecord",
    "DpmWaveSimulationOperation",
    "WaveSimulationItemStatus",
    "WaveSimulationOperationStatus",
    "derive_wave_simulation_operation_status",
    "derive_wave_simulation_operation_status_from_counts",
    "wave_simulation_item_is_retryable",
]
