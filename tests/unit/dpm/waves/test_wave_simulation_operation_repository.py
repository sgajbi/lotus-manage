from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
)
from src.core.waves.simulation_repository import DpmWaveSimulationOperationConflictError
from src.infrastructure.waves.in_memory import InMemoryDpmWaveRepository

NOW = datetime(2026, 10, 1, 1, tzinfo=UTC)
TENANT = "tenant-sg"
WAVE_ID = "dwv_async_001"
OPERATION_ID = "wso_async_001"


def _wave() -> DpmRebalanceWave:
    items = [
        DpmRebalanceWaveItem(
            wave_item_id=f"item-{index}",
            portfolio_id=f"portfolio-{index}",
            state="SOURCE_READY",
        )
        for index in range(4)
    ]
    return DpmRebalanceWave(
        wave_id=WAVE_ID,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="async-proof",
            rationale="Prove durable bounded claims.",
        ),
        as_of_date="2026-10-01",
        created_at=NOW,
        created_by="pm-ops",
        correlation_id="corr-wave-create",
        tenant_id=TENANT,
        items=items,
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=4,
            state_counts={"SOURCE_READY": 4},
            ready_item_count=4,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def _operation(*, request_hash: str = "sha256:request") -> DpmWaveSimulationOperation:
    return DpmWaveSimulationOperation(
        operation_id=OPERATION_ID,
        tenant_id=TENANT,
        wave_id=WAVE_ID,
        request_hash=request_hash,
        idempotency_key_hash="wsi_tenant_key",
        correlation_id="corr-async-simulate",
        actor_id="simulation-api",
        source_identity_hash="sha256:wave-source",
        admitted_wave_version=1,
        methods=["HEURISTIC_EXPLAINABLE"],
        max_concurrency=2,
        max_attempts=2,
        created_at=NOW,
        updated_at=NOW,
    )


def _items() -> list[DpmWaveSimulationItemRecord]:
    return [
        DpmWaveSimulationItemRecord(
            operation_id=OPERATION_ID,
            tenant_id=TENANT,
            wave_id=WAVE_ID,
            wave_item_id=f"item-{index}",
            ordinal=index,
            portfolio_id=f"portfolio-{index}",
            input_payload={"portfolio_id": f"portfolio-{index}"},
            input_hash=f"sha256:input-{index}",
            source_identity_hash=f"sha256:source-{index}",
            updated_at=NOW,
        )
        for index in range(4)
    ]


def _simulating_wave() -> DpmRebalanceWave:
    return _wave().model_copy(update={"state": "SIMULATING", "version": 2})


@pytest.fixture
def repository() -> InMemoryDpmWaveRepository:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT)
    return repository


def test_admission_is_exactly_idempotent_and_rejects_changed_payload(
    repository: InMemoryDpmWaveRepository,
) -> None:
    stored, replayed = repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    replay, exact_replay = repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )

    assert stored == replay
    assert replayed is False
    assert exact_replay is True

    with pytest.raises(DpmWaveSimulationOperationConflictError) as conflict:
        repository.admit_simulation_operation(
            operation=_operation(request_hash="sha256:changed"),
            items=_items(),
            simulating_wave=_simulating_wave(),
        )
    assert str(conflict.value) == "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT"


def test_two_workers_cannot_exceed_operation_concurrency(
    repository: InMemoryDpmWaveRepository,
) -> None:
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )

    first = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-a",
        limit=2,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(minutes=1),
    )
    competing = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-b",
        limit=2,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(minutes=1),
    )

    assert [claim.wave_item_id for claim in first] == ["item-0", "item-1"]
    assert competing == []

    result = _wave().items[0].model_copy(update={"state": "SIMULATED"})
    assert repository.publish_simulation_item_result(
        claim=first[0], result_item=result, completed_at=NOW + timedelta(seconds=5)
    )
    replacement = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-b",
        limit=2,
        claimed_at=NOW + timedelta(seconds=6),
        lease_expires_at=NOW + timedelta(minutes=1),
    )
    assert [claim.wave_item_id for claim in replacement] == ["item-2"]


def test_expired_claim_is_fenced_and_exhaustion_becomes_non_executing_claim(
    repository: InMemoryDpmWaveRepository,
) -> None:
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    first = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-a",
        limit=1,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(seconds=5),
    )[0]
    second = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-b",
        limit=1,
        claimed_at=NOW + timedelta(seconds=6),
        lease_expires_at=NOW + timedelta(seconds=11),
    )[0]

    assert second.wave_item_id == first.wave_item_id
    assert second.attempt_count == 2
    assert second.claim_generation == 2
    assert (
        repository.publish_simulation_item_failure(
            claim=first,
            error_code="STALE",
            error_message="old worker",
            retryable=True,
            completed_at=NOW + timedelta(seconds=7),
        )
        is False
    )

    exhausted = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-c",
        limit=1,
        claimed_at=NOW + timedelta(seconds=12),
        lease_expires_at=NOW + timedelta(seconds=17),
    )[0]
    assert exhausted.wave_item_id == first.wave_item_id
    assert exhausted.attempt_count == 2
    assert exhausted.claim_generation == 3
    assert exhausted.recovery_exhausted is True


def test_retry_preserves_attempt_count_and_cancel_preserves_in_flight_claim(
    repository: InMemoryDpmWaveRepository,
) -> None:
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claims = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-a",
        limit=2,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(minutes=1),
    )
    assert repository.publish_simulation_item_failure(
        claim=claims[0],
        error_code="DEPENDENCY_TIMEOUT",
        error_message="retry later",
        retryable=True,
        completed_at=NOW + timedelta(seconds=5),
    )

    assert (
        repository.retry_simulation_items(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            wave_item_ids=[claims[0].wave_item_id],
            retried_at=NOW + timedelta(seconds=6),
        )
        == 1
    )
    page = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=10, offset=0
    )
    retried = next(item for item in page.items if item.wave_item_id == claims[0].wave_item_id)
    assert retried.status == "PENDING"
    assert retried.attempt_count == 1

    cancelled = repository.cancel_simulation_operation(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        reason_code="OPERATOR_CANCELLED",
        cancelled_at=NOW + timedelta(seconds=7),
    )
    assert cancelled is not None
    assert cancelled.status == "CANCEL_REQUESTED"
    page = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=10, offset=0
    )
    states = {item.wave_item_id: item.status for item in page.items}
    assert states[claims[1].wave_item_id] == "RUNNING"
    assert states[claims[0].wave_item_id] == "CANCELLED"
    assert states["item-2"] == "CANCELLED"
    assert states["item-3"] == "CANCELLED"


def test_results_are_tenant_scoped_and_paged_before_projection(
    repository: InMemoryDpmWaveRepository,
) -> None:
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )

    first_page = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=2, offset=0
    )
    second_page = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=2, offset=2
    )
    foreign = repository.list_simulation_items(
        tenant_id="tenant-other", operation_id=OPERATION_ID, limit=100, offset=0
    )

    assert [item.wave_item_id for item in first_page.items] == ["item-0", "item-1"]
    assert first_page.total_count == 4
    assert first_page.next_offset == 2
    assert [item.wave_item_id for item in second_page.items] == ["item-2", "item-3"]
    assert second_page.next_offset is None
    assert foreign.items == []
    assert foreign.total_count == 0
