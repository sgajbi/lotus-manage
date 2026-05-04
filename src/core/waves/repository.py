"""Persistence contracts for RFC-0041 rebalance waves."""

from typing import Protocol

from src.core.waves.models import DpmRebalanceWave


class DpmWaveNotFoundError(Exception):
    """Raised when a wave does not exist."""


class DpmWaveVersionConflictError(Exception):
    """Raised when a wave update uses a stale expected version."""


class DpmWaveIdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused for a different wave request."""


class DpmWaveAlreadyExistsError(Exception):
    """Raised when a new wave save collides with an existing wave id."""


class DpmWaveRepository(Protocol):
    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
    ) -> None:
        """Persist a new wave and optional idempotency mapping."""

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        """Return a wave by id, or None when absent."""

    def get_wave_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmRebalanceWave | None:
        """Return the wave associated with an idempotency key."""

    def list_waves(
        self,
        *,
        state: str | None = None,
        trigger_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmRebalanceWave]:
        """Return a bounded page of waves matching optional search filters."""

    def update_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        expected_version: int,
    ) -> None:
        """Persist a wave update using optimistic concurrency."""
