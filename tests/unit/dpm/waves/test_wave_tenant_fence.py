"""A wave belongs to one tenant, on every path that reads or writes it (#677).

Waves carried no tenant at all: every wave was addressable by wave_id alone, so
a wave created under one tenant could be read, listed, and - sharpest of the
three - source-checked or selected against by another. #676 added a tenant to
the MANDATE reads those paths perform, which made the mandate evidence look
correctly scoped while the wave itself was never that caller's to touch.

This is distinct from wave idempotency, which #676 closed by deriving the
stored mapping key from the tenant. That path is complete and is not
reimplemented here.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.api.services.wave_lookup import get_wave_or_raise
from src.api.services.wave_persistence import update_wave_or_raise
from src.api.services.wave_transition_execution import prepare_wave_transition
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.infrastructure.waves import InMemoryDpmWaveRepository

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


def _wave(*, wave_id: str = "dwv_001", state: str = "CREATED") -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id=wave_id,
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-wave-001",
            rationale="Tenant fence proof.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm-ops",
        correlation_id=f"corr-{wave_id}",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
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


def _repository_with_tenant_a_wave() -> InMemoryDpmWaveRepository:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_A)
    return repository


def test_another_tenant_cannot_read_a_wave() -> None:
    repository = _repository_with_tenant_a_wave()

    assert repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A) is not None
    assert repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_B) is None


def test_the_refusal_is_indistinguishable_from_an_absent_wave() -> None:
    """A distinct error would confirm the id exists and belongs to somebody.

    That confirmation is itself cross-tenant information, so both cases raise
    the same DPM_WAVE_NOT_FOUND code.

    The comparison is on the CODE, not the message: the message embeds the wave
    id the caller itself supplied, so it differs between the two cases without
    disclosing anything the caller did not already know. Comparing messages
    would fail for a reason that is not a leak - which is what it did on first
    run, and is worth keeping stated so nobody 'fixes' it by removing the id
    from the message.
    """

    repository = _repository_with_tenant_a_wave()

    with pytest.raises(DpmWaveLookupError) as foreign:
        get_wave_or_raise(wave_id="dwv_001", wave_repository=repository, tenant_id=TENANT_B)
    with pytest.raises(DpmWaveLookupError) as absent:
        get_wave_or_raise(
            wave_id="dwv_does_not_exist", wave_repository=repository, tenant_id=TENANT_B
        )

    assert foreign.value.code == absent.value.code == "DPM_WAVE_NOT_FOUND"


def test_another_tenant_cannot_list_a_wave() -> None:
    repository = _repository_with_tenant_a_wave()

    assert [wave.wave_id for wave in repository.list_waves(tenant_id=TENANT_A)] == ["dwv_001"]
    assert repository.list_waves(tenant_id=TENANT_B) == []


def test_the_tenant_filter_is_applied_before_paging_not_after() -> None:
    """Filtering a page would let another tenant's waves consume the limit.

    The caller would silently receive fewer of its own waves than the page it
    asked for - a correctness bug that presents as a short result rather than a
    leak, so a leak-only test would not catch it.
    """

    repository = InMemoryDpmWaveRepository()
    for index in range(3):
        repository.save_wave(
            wave=_wave(wave_id=f"dwv_b{index}"),
            idempotency_key=None,
            request_hash=None,
            tenant_id=TENANT_B,
        )
    repository.save_wave(
        wave=_wave(wave_id="dwv_a0"), idempotency_key=None, request_hash=None, tenant_id=TENANT_A
    )

    page = repository.list_waves(tenant_id=TENANT_A, limit=2)

    assert [wave.wave_id for wave in page] == ["dwv_a0"]


def test_another_tenant_cannot_transition_a_wave_and_is_refused_before_any_effect() -> None:
    """The sharpest of the three: an unfenced read here leads to an unfenced write."""

    repository = _repository_with_tenant_a_wave()

    with pytest.raises(DpmWaveLookupError):
        prepare_wave_transition(
            wave_id="dwv_001",
            wave_repository=repository,
            tenant_id=TENANT_B,
            replay_states=set(),
            allowed_states={"CREATED"},
            error_code="DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
            action_phrase="be source-checked",
        )

    survivor = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert survivor is not None
    assert survivor.state == "CREATED"
    assert survivor.version == 1


def test_the_replay_shortcut_cannot_return_another_tenants_wave() -> None:
    """Ordering proof: the fence sits before the idempotent-replay shortcut.

    If the replay check ran first, a foreign wave already in a replay state
    would be returned as a successful no-op. That is still a read, and it would
    pass a test that only exercised the state guard.
    """

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(state="SOURCE_CHECKED"),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_A,
    )

    with pytest.raises(DpmWaveLookupError):
        prepare_wave_transition(
            wave_id="dwv_001",
            wave_repository=repository,
            tenant_id=TENANT_B,
            replay_states={"SOURCE_CHECKED"},
            allowed_states={"CREATED"},
            error_code="DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
            action_phrase="be source-checked",
        )


def test_another_tenant_cannot_write_a_wave_even_holding_the_record() -> None:
    """Fencing only the read would leave the write reachable.

    The tenant travels to the UPDATE predicate rather than being trusted from
    an earlier load, so a caller that obtained the wave some other way still
    cannot persist over it.
    """

    repository = _repository_with_tenant_a_wave()
    stolen = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert stolen is not None
    tampered = stolen.model_copy(update={"state": "CANCELLED", "version": 2})

    with pytest.raises(DpmWaveValidationError):
        update_wave_or_raise(
            wave_repository=repository,
            wave=tampered,
            expected_version=1,
            tenant_id=TENANT_B,
        )

    survivor = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert survivor is not None
    assert survivor.state == "CREATED"


def test_the_foreign_write_refusal_matches_a_stale_version_refusal() -> None:
    """Indistinguishable on purpose, so the write path cannot be used to probe.

    A distinct "not your wave" error would let a caller enumerate which wave
    ids exist under other tenants by watching which error comes back.
    """

    repository = _repository_with_tenant_a_wave()
    wave = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert wave is not None

    with pytest.raises(DpmWaveValidationError) as foreign:
        update_wave_or_raise(
            wave_repository=repository, wave=wave, expected_version=1, tenant_id=TENANT_B
        )
    with pytest.raises(DpmWaveValidationError) as stale:
        update_wave_or_raise(
            wave_repository=repository, wave=wave, expected_version=99, tenant_id=TENANT_A
        )

    assert foreign.value.args[0] == stale.value.args[0]


def test_a_wave_persisted_before_the_fence_is_reachable_from_no_tenant() -> None:
    """Quarantine, not a default owner.

    Attributing unattributed rows to an assumed tenant is exactly what would
    hand one tenant waves it never created - including under a tenant literally
    named `default`, which is the value a backfill would most plausibly choose.
    """

    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_A)
    stored = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert stored is not None
    repository._waves["dwv_001"] = stored.model_copy(update={"tenant_id": None})  # noqa: SLF001

    for tenant in (TENANT_A, TENANT_B, "default", ""):
        assert repository.get_wave(wave_id="dwv_001", tenant_id=tenant) is None, tenant
        assert repository.list_waves(tenant_id=tenant) == [], tenant


def test_saving_stamps_the_tenant_so_the_record_cannot_disagree_with_the_claim() -> None:
    """A caller must not be able to persist a wave labelled as another tenant's."""

    repository = InMemoryDpmWaveRepository()
    mislabelled = _wave().model_copy(update={"tenant_id": TENANT_B})

    repository.save_wave(
        wave=mislabelled, idempotency_key=None, request_hash=None, tenant_id=TENANT_A
    )

    assert repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_B) is None
    owned = repository.get_wave(wave_id="dwv_001", tenant_id=TENANT_A)
    assert owned is not None and owned.tenant_id == TENANT_A
