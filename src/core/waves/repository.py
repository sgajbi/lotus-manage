"""Persistence contracts for RFC-0041 rebalance waves."""

from typing import Protocol

from src.core.common.derived_identity import derived_identity
from src.core.waves.models import DpmRebalanceWave


class DpmWaveNotFoundError(Exception):
    """Raised when a wave does not exist."""


class DpmWaveVersionConflictError(Exception):
    """Raised when a wave update uses a stale expected version."""


class DpmWaveIdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused for a different wave request."""


class DpmWaveAlreadyExistsError(Exception):
    """Raised when a new wave save collides with an existing wave id."""


def wave_idempotency_mapping_key(*, tenant_id: str, idempotency_key: str) -> str:
    """Derive the stored mapping key for a caller-chosen idempotency key.

    The caller's key is not stored directly because it is the mapping's primary
    key: two tenants presenting the same caller-chosen key could not both hold a
    mapping, and refusing the second would disclose that another tenant holds it
    (issue #648). Deriving from the tenant makes the two mappings independent.
    """

    return derived_identity("wik", tenant_id, idempotency_key)


class DpmWaveRepository(Protocol):
    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
        tenant_id: str,
    ) -> None:
        """Persist a new wave and optional tenant-scoped idempotency mapping.

        `tenant_id` is required rather than defaulted so mypy enumerates every
        call site; a mapping written without one is reachable by no tenant.
        """

    def get_wave(self, *, wave_id: str, tenant_id: str) -> DpmRebalanceWave | None:
        """Return this tenant's wave by id, or None when it is not theirs.

        `tenant_id` is required rather than defaulted so mypy enumerates every
        call site (issue #677). Before the fence this returned any wave to any
        caller, and the transition path reads through here - so an unfenced
        read led directly to an unfenced write.

        A wave belonging to another tenant, or to none, returns None rather
        than raising: a distinguishable refusal would disclose that the id
        exists and belongs to someone.
        """

    def get_wave_by_idempotency(
        self,
        *,
        idempotency_key: str,
        tenant_id: str,
    ) -> DpmRebalanceWave | None:
        """Return this tenant's wave for a caller-chosen key, if any.

        `tenant_id` is required, not optional, because a replay decision made
        on the caller-chosen key alone serves whichever wave claimed that key
        first - including one created by another tenant (issue #648). Required
        rather than defaulted so mypy enumerates every call site.

        A mapping belonging to a different tenant, or to no tenant, does not
        match: this returns None and the caller creates its own wave. That is
        deliberately not a conflict, because a conflict would disclose that
        some other tenant holds that key.
        """

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
        """Return a bounded page of THIS TENANT's waves matching the filters.

        Placed first and required, so a caller cannot get a cross-tenant page
        by omitting it (issue #677). The optional filters narrow within one
        tenant; they never widen across tenants.
        """

    def update_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        expected_version: int,
        tenant_id: str,
    ) -> None:
        """Persist a wave update for this tenant using optimistic concurrency.

        The tenant is part of the update predicate, not merely checked before
        it: a check-then-write leaves a window, and this is the write half of
        the transition path (issue #677). A wave belonging to another tenant
        matches no row and raises the same version-conflict error as a stale
        expected_version - deliberately indistinguishable, so a caller cannot
        probe for another tenant's wave ids.
        """
