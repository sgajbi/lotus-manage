"""Wave-aggregate tenant isolation, proven against PostgreSQL (#677).

The in-memory proofs in `tests/unit/dpm/waves/test_wave_tenant_fence.py` decide
the same questions in Python. Four properties here are not Python's to decide,
and the in-memory store can be made to agree with either answer:

1. the fence lives in a SQL predicate, so it either reached the WHERE clause or
   it did not,
2. `list_waves` filters before LIMIT/OFFSET - the engine applies them in the
   order the query states, and filtering a page instead of the set is a bug
   that presents as a short result rather than a leak,
3. a row whose `tenant_id` is NULL is matched by no equality predicate, because
   `NULL = 'anything'` is NULL rather than false. Python's `None != tenant`
   answers this by a completely different rule, so the quarantine claim is only
   really proven here,
4. `correlation_id` uniqueness is per tenant, which is a property of an index.

Requires a real engine. Set DPM_POSTGRES_INTEGRATION_DSN to a disposable
database, as the wave idempotency isolation proof does.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
    DpmWaveVersionConflictError,
)
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository

from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "wave aggregate isolation proof"


@pytest.fixture
def repository() -> PostgresDpmWaveRepository:
    return PostgresDpmWaveRepository(dsn=postgres_dsn_or_skip(_PROOF))


@pytest.fixture
def tenants() -> tuple[str, str]:
    """A fresh pair of tenants per test, against a database that is not reset.

    Fixed tenant names made every run read the rows of every run before it, so
    a listing assertion depended on residue and the same suite gave different
    answers twice in a row. Isolating by tenant rather than by cleanup also
    keeps the teardown honest: a test that deleted rows by tenant would be
    exercising the very predicate under test.
    """

    run = uuid.uuid4().hex[:12]
    return f"tenant-alpha-{run}", f"tenant-beta-{run}"


def _wave(
    *,
    wave_id: str,
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    correlation_id: str | None = None,
) -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="CREATED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="wave-aggregate-isolation",
            rationale="Prove the wave aggregate is fenced in SQL.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm-ops",
        correlation_id=correlation_id or f"corr-{wave_id}",
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


def _new_wave_id() -> str:
    return f"dwv_{uuid.uuid4().hex[:12]}"


def test_a_wave_is_readable_only_by_the_tenant_that_created_it(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    tenant_a, tenant_b = tenants

    wave_id = _new_wave_id()
    repository.save_wave(
        wave=_wave(wave_id=wave_id, portfolio_id="PB_TENANT_A_001"),
        idempotency_key=None,
        request_hash=None,
        tenant_id=tenant_a,
    )

    owned = repository.get_wave(wave_id=wave_id, tenant_id=tenant_a)

    assert owned is not None
    assert owned.items[0].portfolio_id == "PB_TENANT_A_001"
    # The wave_id is the table's PRIMARY KEY, so this row is trivially
    # addressable. Only the tenant predicate keeps the other caller out.
    assert repository.get_wave(wave_id=wave_id, tenant_id=tenant_b) is None


def test_the_tenant_filter_is_applied_before_limit_and_offset(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    """Paging first would silently return fewer of the caller's own waves.

    That is a correctness bug rather than a leak, so a test that only looked
    for another tenant's data in the result would pass while it happened.
    """

    tenant_a, tenant_b = tenants

    # A fixed date: the tenant fixture already isolates this test, and a
    # random one would only hide a residue problem it no longer has.
    as_of_date = "2026-05-03"
    for _ in range(3):
        repository.save_wave(
            wave=_wave(wave_id=_new_wave_id()).model_copy(update={"as_of_date": as_of_date}),
            idempotency_key=None,
            request_hash=None,
            tenant_id=tenant_b,
        )
    owned_id = _new_wave_id()
    repository.save_wave(
        wave=_wave(wave_id=owned_id).model_copy(update={"as_of_date": as_of_date}),
        idempotency_key=None,
        request_hash=None,
        tenant_id=tenant_a,
    )

    page = repository.list_waves(tenant_id=tenant_a, as_of_date=as_of_date, limit=2, offset=0)

    assert [wave.wave_id for wave in page] == [owned_id]


def test_another_tenant_cannot_write_a_wave_it_can_name(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    """The tenant travels into the UPDATE predicate, not a check before it.

    A caller holding the record - from an export, a log, a prior grant - still
    changes no row, and cannot distinguish that refusal from a stale version.
    """

    tenant_a, tenant_b = tenants

    wave_id = _new_wave_id()
    original = _wave(wave_id=wave_id)
    repository.save_wave(wave=original, idempotency_key=None, request_hash=None, tenant_id=tenant_a)
    stored = repository.get_wave(wave_id=wave_id, tenant_id=tenant_a)
    assert stored is not None

    tampered = stored.model_copy(update={"state": "CANCELLED", "version": stored.version + 1})
    with pytest.raises(DpmWaveVersionConflictError):
        repository.update_wave(wave=tampered, expected_version=stored.version, tenant_id=tenant_b)

    survivor = repository.get_wave(wave_id=wave_id, tenant_id=tenant_a)
    assert survivor is not None
    assert survivor.state == "CREATED"
    assert survivor.version == stored.version


def test_a_wave_persisted_before_the_fence_is_matched_by_no_tenant(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    """The quarantine claim, decided by SQL's NULL rules rather than Python's.

    `tenant_id = 'anything'` against a NULL evaluates to NULL, which WHERE
    treats as not-matched - so the row is reachable from no tenant at all,
    including one named `default`, which is the value a backfill would most
    plausibly choose. Migration 0027 adds the column nullable and backfills
    nothing precisely so these rows stay unattributed until a human attributes
    them.
    """

    tenant_a, tenant_b = tenants

    wave_id = _new_wave_id()
    repository.save_wave(
        wave=_wave(wave_id=wave_id), idempotency_key=None, request_hash=None, tenant_id=tenant_a
    )
    with repository._connect() as connection:  # noqa: SLF001
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE dpm_rebalance_waves SET tenant_id = NULL WHERE wave_id = %s",
                (wave_id,),
            )
        connection.commit()

    for tenant in (tenant_a, tenant_b, "default", ""):
        assert repository.get_wave(wave_id=wave_id, tenant_id=tenant) is None, tenant
        listed = repository.list_waves(tenant_id=tenant, limit=100, offset=0)
        assert all(wave.wave_id != wave_id for wave in listed), tenant


def test_two_tenants_may_choose_the_same_correlation_id(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    """correlation_id arrives on the caller's own header.

    While its unique index was global, a value one tenant had already used made
    another tenant's create fail - a denial caused by data that caller cannot
    see, and an existence oracle for a value it chose itself. Before migration
    0027 scoped that index, the second save here raised a unique violation.
    """

    tenant_a, tenant_b = tenants

    shared_correlation_id = f"corr-shared-{uuid.uuid4().hex[:10]}"
    wave_a = _wave(
        wave_id=_new_wave_id(),
        portfolio_id="PB_TENANT_A_001",
        correlation_id=shared_correlation_id,
    )
    wave_b = _wave(
        wave_id=_new_wave_id(),
        portfolio_id="PB_TENANT_B_001",
        correlation_id=shared_correlation_id,
    )

    repository.save_wave(wave=wave_a, idempotency_key=None, request_hash=None, tenant_id=tenant_a)
    repository.save_wave(wave=wave_b, idempotency_key=None, request_hash=None, tenant_id=tenant_b)

    stored_a = repository.get_wave(wave_id=wave_a.wave_id, tenant_id=tenant_a)
    stored_b = repository.get_wave(wave_id=wave_b.wave_id, tenant_id=tenant_b)
    assert stored_a is not None and stored_a.items[0].portfolio_id == "PB_TENANT_A_001"
    assert stored_b is not None and stored_b.items[0].portfolio_id == "PB_TENANT_B_001"


def test_one_tenant_still_cannot_reuse_its_own_correlation_id(
    repository: PostgresDpmWaveRepository,
    tenants: tuple[str, str],
) -> None:
    """Scoping the index must not have dropped the guarantee it carried.

    Without this, deleting the unique index entirely would pass every other
    test in this file.
    """

    tenant_a, tenant_b = tenants

    correlation_id = f"corr-reused-{uuid.uuid4().hex[:10]}"
    repository.save_wave(
        wave=_wave(wave_id=_new_wave_id(), correlation_id=correlation_id),
        idempotency_key=None,
        request_hash=None,
        tenant_id=tenant_a,
    )

    with pytest.raises(Exception) as duplicate:
        repository.save_wave(
            wave=_wave(wave_id=_new_wave_id(), correlation_id=correlation_id),
            idempotency_key=None,
            request_hash=None,
            tenant_id=tenant_a,
        )

    assert "idx_dpm_rebalance_waves_tenant_correlation" in str(duplicate.value)
