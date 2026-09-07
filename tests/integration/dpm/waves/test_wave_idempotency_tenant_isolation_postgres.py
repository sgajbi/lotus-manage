"""Wave idempotency isolation, proven against PostgreSQL (#648).

Idempotency keys are caller-chosen, so two tenants can present the same one.
The create path looked a wave up by that key alone and returned whatever it
found, so the second tenant received the FIRST tenant's wave - another client's
portfolios, returned as its own and indistinguishable from a legitimate replay.

Adding the tenant to the request hash did not close it: the hash was written on
save and never compared on the lookup path, so the tenant it carried never
entered the replay decision.

Run against a real engine because the mapping is a table whose primary key is
the stored idempotency key. Whether two tenants can hold one caller-chosen key
is a property of that constraint, not of Python, and the in-memory store can be
made to agree with either answer.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveAggregateMetrics,
    DpmRebalanceWaveItem,
    DpmWaveTrigger,
)
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()

pytestmark = pytest.mark.skipif(
    not _DSN,
    reason="DPM_POSTGRES_INTEGRATION_DSN is required for the wave idempotency isolation proof",
)

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


@pytest.fixture
def repository() -> PostgresDpmWaveRepository:
    return PostgresDpmWaveRepository(dsn=_DSN)


def _wave(*, wave_id: str, portfolio_id: str) -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="CREATED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="wave-idempotency-isolation",
            rationale="Prove two tenants cannot share one caller-chosen key.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm-ops",
        # Unique per wave: correlation_id carries a global unique index, so two
        # waves cannot share one. That index is itself unscoped by tenant and is
        # tracked with the other wave-aggregate tenancy work.
        correlation_id=f"corr-{wave_id}",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id=f"dwi_{uuid.uuid4().hex[:8]}",
                portfolio_id=portfolio_id,
                state="CANDIDATE",
            )
        ],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"CANDIDATE": 1},
            ready_item_count=0,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def test_two_tenants_may_hold_the_same_caller_chosen_idempotency_key(
    repository: PostgresDpmWaveRepository,
) -> None:
    """Both tenants store a mapping, and each reads back only its own wave."""

    shared_key = f"idem-shared-{uuid.uuid4().hex[:10]}"
    wave_a = _wave(wave_id=f"dwv_{uuid.uuid4().hex[:10]}", portfolio_id="PB_TENANT_A_001")
    wave_b = _wave(wave_id=f"dwv_{uuid.uuid4().hex[:10]}", portfolio_id="PB_TENANT_B_001")

    repository.save_wave(
        wave=wave_a, idempotency_key=shared_key, request_hash="hash-a", tenant_id=TENANT_A
    )
    # Before the fix this was impossible: the stored key was the caller's own,
    # and it is this table's PRIMARY KEY.
    repository.save_wave(
        wave=wave_b, idempotency_key=shared_key, request_hash="hash-b", tenant_id=TENANT_B
    )

    replay_a = repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id=TENANT_A)
    replay_b = repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id=TENANT_B)

    assert replay_a is not None and replay_a.wave_id == wave_a.wave_id
    assert replay_b is not None and replay_b.wave_id == wave_b.wave_id
    # The disclosure being closed: neither tenant reaches the other's wave.
    assert replay_a.wave_id != wave_b.wave_id
    assert replay_b.wave_id != wave_a.wave_id
    assert replay_a.items[0].portfolio_id == "PB_TENANT_A_001"
    assert replay_b.items[0].portfolio_id == "PB_TENANT_B_001"


def test_a_tenant_with_no_mapping_reads_nothing_for_a_key_another_tenant_holds(
    repository: PostgresDpmWaveRepository,
) -> None:
    """The failure mode is silence, not a conflict.

    A conflict would disclose that some other tenant holds that key, which is
    itself cross-tenant information. The second tenant simply finds nothing and
    creates its own wave.
    """

    shared_key = f"idem-onesided-{uuid.uuid4().hex[:10]}"
    wave_a = _wave(wave_id=f"dwv_{uuid.uuid4().hex[:10]}", portfolio_id="PB_TENANT_A_002")
    repository.save_wave(
        wave=wave_a, idempotency_key=shared_key, request_hash="hash-a", tenant_id=TENANT_A
    )

    assert (
        repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id=TENANT_B) is None
    )
    # And an unattributed lookup reaches neither, including under a tenant
    # literally named "default" - no row is defaulted into.
    assert (
        repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id="default") is None
    )
    assert repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id="") is None
    # Convergence half: the owning tenant still replays, so isolation did not
    # simply break idempotency.
    owned = repository.get_wave_by_idempotency(idempotency_key=shared_key, tenant_id=TENANT_A)
    assert owned is not None and owned.wave_id == wave_a.wave_id
