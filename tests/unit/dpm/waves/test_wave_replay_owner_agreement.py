"""Replay requires caller, mapping and aggregate to agree on the tenant.

`get_wave_by_idempotency` checked the MAPPING's tenant and returned whatever
wave the mapping pointed at. Migration 0026 made mapping keys tenant-derived
and 0027 added the wave's own tenant column nullable with no backfill, so
between them a wave can carry no tenant at all while its tenant-scoped mapping
survives.

That left one path through the fence. Every direct read refuses a NULL-tenant
wave, because `NULL = 'anything'` is NULL rather than true - but creation with
the original idempotency key returned it as a successful replay. The caller
received an aggregate that officially nobody owns, and received it through the
one route that looks like success rather than like a leak.

The pairing in the first test is the point: same wave, same caller, one route
refusing and one returning. Testing the replay path alone would have passed
before this fix, because returning a wave IS what replay does.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.infrastructure.waves import InMemoryDpmWaveRepository

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"
KEY = "idem-shared-by-two-tenants"


def _wave(*, wave_id: str = "dwv_001", portfolio_id: str = "PB_A_001") -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="CREATED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"manual-{wave_id}",
            rationale="Replay ownership agreement proof.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm-ops",
        correlation_id=f"corr-{wave_id}",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id=f"dwi_{wave_id}",
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


def _quarantined_wave_with_a_live_mapping() -> InMemoryDpmWaveRepository:
    """A wave persisted before 0027 stamped owners, whose mapping survives."""

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(), idempotency_key=KEY, request_hash="hash-a", tenant_id=TENANT_A
    )
    stored = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert stored is not None
    repository._waves["dwv_001"] = stored.model_copy(  # noqa: SLF001
        update={"tenant_id": None}
    )
    return repository


def test_a_quarantined_wave_is_refused_by_replay_exactly_as_by_a_direct_read() -> None:
    repository = _quarantined_wave_with_a_live_mapping()

    direct = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    replayed = repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_A)

    assert direct is None
    assert replayed is None, (
        "the replay path returned a wave the direct read refuses - this is the "
        "defect, and asserting only the replay result cannot see it"
    )


def test_the_refused_replay_does_not_stamp_or_resurrect_the_row() -> None:
    """Quarantine means unowned, not 'owned by whoever asks next'.

    A fix that repaired the row by assigning the caller's tenant would make
    every test above pass while doing the one thing migration 0027 refuses to
    do: give a pre-fence wave an assumed owner.
    """

    repository = _quarantined_wave_with_a_live_mapping()

    repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_A)

    survivor = repository._waves["dwv_001"]  # noqa: SLF001
    assert survivor.tenant_id is None
    assert repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A) is None


def test_a_valid_replay_still_returns_the_wave() -> None:
    """The fence must not cost the behaviour idempotency exists for."""

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(), idempotency_key=KEY, request_hash="hash-a", tenant_id=TENANT_A
    )

    replayed = repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_A)

    assert replayed is not None
    assert replayed.wave_id == "dwv_001"
    assert replayed.tenant_id == TENANT_A


def test_two_tenants_may_reuse_one_caller_chosen_key_independently() -> None:
    """The property #676 delivered, re-asserted here because this change
    touches the same lookup and a tightening could have collapsed it."""

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(wave_id="dwv_a", portfolio_id="PB_A_001"),
        idempotency_key=KEY,
        request_hash="hash-a",
        tenant_id=TENANT_A,
    )
    repository.save_wave(
        wave=_wave(wave_id="dwv_b", portfolio_id="PB_B_001"),
        idempotency_key=KEY,
        request_hash="hash-b",
        tenant_id=TENANT_B,
    )

    replay_a = repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_A)
    replay_b = repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_B)

    assert replay_a is not None and replay_a.wave_id == "dwv_a"
    assert replay_b is not None and replay_b.wave_id == "dwv_b"
    assert replay_a.items[0].portfolio_id == "PB_A_001"
    assert replay_b.items[0].portfolio_id == "PB_B_001"


def test_a_mapping_pointing_at_another_tenants_wave_is_refused() -> None:
    """Mapping and aggregate can disagree without either being NULL.

    A restore, a partial migration or a hand-repaired row can leave a mapping
    resolving to a wave a different tenant owns. Checking the mapping alone
    accepts it.
    """

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(wave_id="dwv_b"),
        idempotency_key=KEY,
        request_hash="hash-b",
        tenant_id=TENANT_B,
    )
    # Tenant A's mapping now resolves to tenant B's wave.
    from src.core.waves.repository import wave_idempotency_mapping_key

    repository._idempotency_index[  # noqa: SLF001
        wave_idempotency_mapping_key(tenant_id=TENANT_A, idempotency_key=KEY)
    ] = ("dwv_b", "hash-a")

    assert repository.get_wave_by_idempotency(idempotency_key=KEY, tenant_id=TENANT_A) is None
    assert repository.get_wave(wave_id="dwv_b", tenant_id=TENANT_B) is not None
