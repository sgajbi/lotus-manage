"""Real PostgreSQL proof for durable wave-operation claims and fencing."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest

from src.api.request_models import RebalanceRequest
from src.api.services import wave_simulation_operations
from src.api.services.wave_simulation_item import DpmWaveSimulationInput, simulate_item
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmRunSupportService
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
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository
from src.infrastructure.construction import (
    InMemoryConstructionRepository,
    PostgresConstructionRepository,
)
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "durable wave simulation operation proof"


@pytest.fixture
def dsn() -> str:
    return postgres_dsn_or_skip(_PROOF)


def _ids() -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:12]
    return f"tenant-{suffix}", f"dwv-{suffix}", f"wso-{suffix}"


def _wave(*, tenant_id: str, wave_id: str, item_count: int = 4) -> DpmRebalanceWave:
    items = [
        DpmRebalanceWaveItem(
            wave_item_id=f"{wave_id}-item-{index}",
            portfolio_id=f"portfolio-{index}",
            state="SOURCE_READY",
        )
        for index in range(item_count)
    ]
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"trigger-{wave_id}",
            rationale="Prove PostgreSQL worker ownership.",
        ),
        as_of_date="2026-10-01",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        created_by="integration-test",
        correlation_id=f"corr-wave-{wave_id}",
        tenant_id=tenant_id,
        items=items,
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=item_count,
            state_counts={"SOURCE_READY": item_count},
            ready_item_count=item_count,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def _financial_request(portfolio_id: str) -> dict[str, object]:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.80"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"target_method": "HEURISTIC"},
    }


def _admit_financial_operation(
    *,
    repository: PostgresDpmWaveRepository,
    tenant_id: str,
    wave_id: str,
    item_count: int,
    max_concurrency: int = 4,
    max_attempts: int = 3,
) -> DpmWaveSimulationOperation:
    wave = _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=item_count)
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id)
    operation, replayed = wave_simulation_operations.admit_wave_simulation_operation(
        wave_id=wave_id,
        tenant_id=tenant_id,
        actor_id="integration-test",
        correlation_id=f"corr-{wave_id}-async",
        idempotency_key=f"idem-{wave_id}",
        item_payloads=[
            {
                "wave_item_id": item.wave_item_id,
                "stateless_input": _financial_request(item.portfolio_id),
            }
            for item in wave.items
        ],
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        repository=repository,
    )
    assert replayed is False
    return operation


def _admit(
    *,
    repository: PostgresDpmWaveRepository,
    tenant_id: str,
    wave_id: str,
    operation_id: str,
    item_count: int = 4,
    max_concurrency: int = 2,
    max_attempts: int = 2,
) -> DpmWaveSimulationOperation:
    now = datetime(2026, 10, 1, tzinfo=UTC)
    wave = _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=item_count)
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id)
    operation = DpmWaveSimulationOperation(
        operation_id=operation_id,
        tenant_id=tenant_id,
        wave_id=wave_id,
        request_hash=f"sha256:request-{operation_id}",
        idempotency_key_hash=f"wsi-{operation_id}",
        correlation_id=f"corr-{operation_id}",
        actor_id="integration-test",
        source_identity_hash=f"sha256:source-{wave_id}",
        admitted_wave_version=wave.version,
        methods=["HEURISTIC_EXPLAINABLE"],
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
    )
    items = [
        DpmWaveSimulationItemRecord(
            operation_id=operation_id,
            tenant_id=tenant_id,
            wave_id=wave_id,
            wave_item_id=item.wave_item_id,
            ordinal=index,
            portfolio_id=item.portfolio_id,
            input_payload={"portfolio_id": item.portfolio_id},
            input_hash=f"sha256:input-{index}",
            source_identity_hash=f"sha256:item-source-{index}",
            updated_at=now,
        )
        for index, item in enumerate(wave.items)
    ]
    stored, replayed = repository.admit_simulation_operation(
        operation=operation,
        items=items,
        simulating_wave=wave.model_copy(update={"state": "SIMULATING", "version": 2}),
    )
    assert replayed is False
    assert stored == operation
    return operation


def test_competing_repository_instances_respect_the_shared_concurrency_budget(
    dsn: str,
) -> None:
    tenant_id, wave_id, operation_id = _ids()
    _admit(
        repository=PostgresDpmWaveRepository(dsn=dsn),
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        max_concurrency=2,
    )
    barrier = Barrier(2)
    now = datetime(2026, 10, 1, 1, tzinfo=UTC)

    def claim(worker_id: str) -> list[str]:
        repository = PostgresDpmWaveRepository(dsn=dsn)
        barrier.wait()
        return [
            item.wave_item_id
            for item in repository.claim_simulation_items(
                tenant_id=tenant_id,
                operation_id=operation_id,
                worker_id=worker_id,
                limit=2,
                claimed_at=now,
                lease_expires_at=now + timedelta(minutes=1),
            )
        ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        pages = list(executor.map(claim, ["worker-a", "worker-b"]))

    claimed = [item_id for page in pages for item_id in page]
    assert len(claimed) == 2
    assert len(set(claimed)) == 2
    assert sorted(len(page) for page in pages) in ([0, 2], [1, 1])


def test_restart_reclaims_expired_work_and_refuses_the_stale_owner(dsn: str) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    _admit(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        item_count=1,
        max_concurrency=1,
    )
    now = datetime(2026, 10, 1, 2, tzinfo=UTC)
    stale = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker-that-died",
        limit=1,
        claimed_at=now,
        lease_expires_at=now + timedelta(seconds=5),
    )[0]

    replacement_repository = PostgresDpmWaveRepository(dsn=dsn)
    replacement = replacement_repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="replacement-worker",
        limit=1,
        claimed_at=now + timedelta(seconds=6),
        lease_expires_at=now + timedelta(seconds=30),
    )[0]

    assert replacement.wave_item_id == stale.wave_item_id
    assert replacement.attempt_count == 2
    assert replacement.claim_generation == 2
    assert (
        replacement_repository.publish_simulation_item_failure(
            claim=stale,
            error_code="STALE_OWNER",
            error_message="must be fenced",
            retryable=True,
            completed_at=now + timedelta(seconds=7),
        )
        is False
    )
    result_item = (
        _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=1)
        .items[0]
        .model_copy(update={"state": "SIMULATED"})
    )
    assert replacement_repository.publish_simulation_item_result(
        claim=replacement,
        result_item=result_item,
        completed_at=now + timedelta(seconds=8),
    )
    stored = PostgresDpmWaveRepository(dsn=dsn).get_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id
    )
    assert stored is not None
    assert stored.status == "SUCCEEDED"


def test_cancellation_keeps_running_work_fenced_and_cancels_unclaimed_work(
    dsn: str,
) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    _admit(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        item_count=3,
        max_concurrency=1,
    )
    now = datetime(2026, 10, 1, 3, tzinfo=UTC)
    running = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker-a",
        limit=1,
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )[0]

    cancelled = PostgresDpmWaveRepository(dsn=dsn).cancel_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        reason_code="OPERATOR_CANCELLED",
        cancelled_at=now + timedelta(seconds=1),
    )
    assert cancelled is not None
    assert cancelled.status == "CANCEL_REQUESTED"
    assert cancelled.cancel_reason_code == "OPERATOR_CANCELLED"
    page = repository.list_simulation_items(
        tenant_id=tenant_id, operation_id=operation_id, limit=10, offset=0
    )
    assert [item.status for item in page.items].count("RUNNING") == 1
    assert [item.status for item in page.items].count("CANCELLED") == 2
    assert (
        repository.claim_simulation_items(
            tenant_id=tenant_id,
            operation_id=operation_id,
            worker_id="worker-b",
            limit=1,
            claimed_at=now + timedelta(seconds=2),
            lease_expires_at=now + timedelta(minutes=1),
        )
        == []
    )
    terminal = repository.cancel_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        reason_code="SECOND_CANCEL_IGNORED",
        cancelled_at=now + timedelta(seconds=5),
    )
    assert terminal is not None
    assert terminal.status == "CANCEL_REQUESTED"
    assert terminal.cancel_reason_code == "OPERATOR_CANCELLED"
    assert (
        repository.retry_simulation_items(
            tenant_id=tenant_id,
            operation_id=operation_id,
            wave_item_ids=None,
            retried_at=now + timedelta(seconds=6),
        )
        == 0
    )

    result_item = (
        _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=3)
        .items[0]
        .model_copy(update={"state": "SIMULATED"})
    )
    assert repository.publish_simulation_item_result(
        claim=running,
        result_item=result_item,
        completed_at=now + timedelta(seconds=3),
    )
    terminal = repository.get_simulation_operation(tenant_id=tenant_id, operation_id=operation_id)
    assert terminal is not None
    assert terminal.status == "CANCELLED"


def test_results_are_tenant_scoped_before_paging(dsn: str) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    _admit(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        item_count=3,
    )

    first = repository.list_simulation_items(
        tenant_id=tenant_id, operation_id=operation_id, limit=2, offset=0
    )
    foreign = repository.list_simulation_items(
        tenant_id="tenant-other", operation_id=operation_id, limit=2, offset=0
    )

    assert first.total_count == 3
    assert first.next_offset == 2
    assert [item.ordinal for item in first.items] == [0, 1]
    assert foreign.total_count == 0
    assert foreign.items == []


def test_postgres_retry_exhaustion_produces_one_non_retryable_terminal_disposition(
    dsn: str,
) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    _admit(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        item_count=1,
        max_concurrency=1,
        max_attempts=2,
    )
    first_at = datetime(2026, 10, 1, 3, 30, tzinfo=UTC)
    first = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker-1",
        limit=1,
        claimed_at=first_at,
        lease_expires_at=first_at + timedelta(seconds=5),
    )[0]
    second = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker-2",
        limit=1,
        claimed_at=first_at + timedelta(seconds=6),
        lease_expires_at=first_at + timedelta(seconds=11),
    )[0]
    exhausted = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker-3",
        limit=1,
        claimed_at=first_at + timedelta(seconds=12),
        lease_expires_at=first_at + timedelta(seconds=17),
    )[0]
    assert (first.attempt_count, second.attempt_count, exhausted.attempt_count) == (1, 2, 2)
    assert exhausted.recovery_exhausted is True
    assert repository.publish_simulation_item_failure(
        claim=exhausted,
        error_code="DPM_WAVE_SIMULATION_RETRY_EXHAUSTED",
        error_message="worker leases expired",
        retryable=False,
        completed_at=first_at + timedelta(seconds=13),
    )
    assert (
        repository.publish_simulation_item_failure(
            claim=second,
            error_code="STALE_OWNER",
            error_message="must remain fenced",
            retryable=True,
            completed_at=first_at + timedelta(seconds=13),
        )
        is False
    )
    page = repository.list_simulation_items(
        tenant_id=tenant_id, operation_id=operation_id, limit=10, offset=0
    )
    assert page.total_count == 1
    assert page.items[0].status == "FAILED"
    assert page.items[0].retryable is False
    assert page.items[0].error_code == "DPM_WAVE_SIMULATION_RETRY_EXHAUSTED"
    terminal = repository.get_simulation_operation(tenant_id=tenant_id, operation_id=operation_id)
    assert terminal is not None
    assert terminal.status == "FAILED"


def test_process_replacement_reuses_committed_financial_artifact_and_fences_stale_owner(
    dsn: str,
) -> None:
    tenant_id, wave_id, _ = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    construction_repository = PostgresConstructionRepository(dsn=dsn)
    operation = _admit_financial_operation(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        item_count=1,
        max_concurrency=1,
    )
    run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    claimed_at = datetime(2026, 10, 1, 4, tzinfo=UTC)
    stale = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        worker_id="worker-that-died",
        limit=1,
        claimed_at=claimed_at,
        lease_expires_at=claimed_at + timedelta(seconds=5),
    )[0]
    wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    assert wave is not None
    source_item = wave.items[0]
    request = RebalanceRequest.model_validate(stale.input_payload["stateless_input"])

    committed_before_death = simulate_item(
        item=source_item,
        correlation_id=f"{operation.operation_id}:{stale.wave_item_id}",
        item_inputs={
            stale.wave_item_id: DpmWaveSimulationInput(
                stateless_input=request,
                authority_context=None,
            )
        },
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        construction_repository=construction_repository,
        run_service=run_service,
        risk_authority_client=None,
        construction_idempotency_key=(
            f"wave-operation:{operation.operation_id}:{stale.wave_item_id}:simulate"
        ),
    )
    assert committed_before_death.alternative_set_id is not None

    replacement_repository = PostgresDpmWaveRepository(dsn=dsn)
    completed = wave_simulation_operations.execute_wave_simulation_work(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        worker_id="replacement-worker",
        max_items=1,
        lease_seconds=30,
        repository=replacement_repository,
        construction_repository=construction_repository,
        run_service=run_service,
        risk_authority_client=None,
    )
    assert completed[1:] == (1, 1, 0)
    assert completed[0].status == "SUCCEEDED"
    result = replacement_repository.list_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        limit=10,
        offset=0,
    ).items[0]
    assert result.result_item is not None
    assert result.result_item.alternative_set_id == committed_before_death.alternative_set_id
    assert result.attempt_count == 2
    assert (
        replacement_repository.publish_simulation_item_failure(
            claim=stale,
            error_code="STALE_OWNER",
            error_message="must remain fenced",
            retryable=True,
            completed_at=datetime.now(UTC),
        )
        is False
    )
    deterministic_key = f"wave-operation:{operation.operation_id}:{stale.wave_item_id}:simulate"
    replayed_artifact = construction_repository.get_alternative_set_by_idempotency(
        idempotency_key=deterministic_key
    )
    assert replayed_artifact is not None
    assert replayed_artifact.alternative_set_id == committed_before_death.alternative_set_id
    assert (
        sum(
            alternative.alternative_set_id == committed_before_death.alternative_set_id
            for alternative in construction_repository.list_alternative_sets(
                portfolio_id=source_item.portfolio_id, limit=100
            )
        )
        == 1
    )


def test_postgres_worker_fails_closed_on_source_revision_change(dsn: str) -> None:
    tenant_id, wave_id, _ = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    operation = _admit_financial_operation(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        item_count=1,
        max_concurrency=1,
    )
    wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    assert wave is not None
    changed_item = wave.items[0].model_copy(
        update={"model_portfolio_id": "MODEL_CHANGED_AFTER_ADMISSION"}, deep=True
    )
    repository.update_wave(
        wave=wave.model_copy(update={"items": [changed_item], "version": wave.version + 1}),
        expected_version=wave.version,
        tenant_id=tenant_id,
    )

    _, claimed, completed, failed = wave_simulation_operations.execute_wave_simulation_work(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        worker_id="worker-source-conflict",
        max_items=1,
        lease_seconds=30,
        repository=PostgresDpmWaveRepository(dsn=dsn),
        construction_repository=PostgresConstructionRepository(dsn=dsn),
        run_service=DpmRunSupportService(repository=InMemoryDpmRunRepository()),
        risk_authority_client=None,
    )
    assert (claimed, completed, failed) == (1, 0, 1)
    result = repository.list_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        limit=10,
        offset=0,
    ).items[0]
    assert result.status == "FAILED"
    assert result.retryable is False
    assert result.error_code == "DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT"
    final_wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    assert final_wave is not None
    assert final_wave.state == "SIMULATION_FAILED"


def test_deterministic_hundred_item_wave_resumes_with_four_horizontal_workers(
    dsn: str,
) -> None:
    tenant_id, wave_id, _ = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    construction_repository = PostgresConstructionRepository(dsn=dsn)
    operation = _admit_financial_operation(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        item_count=100,
        max_concurrency=4,
    )
    admitted_wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    assert admitted_wave is not None
    by_item_id = {item.wave_item_id: item for item in admitted_wave.items}

    interrupted_at = datetime(2026, 10, 1, tzinfo=UTC)
    interrupted_claims = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        worker_id="interrupted-worker",
        limit=4,
        claimed_at=interrupted_at,
        lease_expires_at=interrupted_at + timedelta(seconds=5),
    )
    assert len(interrupted_claims) == 4
    interrupted_run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    committed_ids: dict[str, str] = {}
    for claim in interrupted_claims:
        committed = simulate_item(
            item=by_item_id[claim.wave_item_id],
            correlation_id=f"{operation.operation_id}:{claim.wave_item_id}",
            item_inputs={
                claim.wave_item_id: DpmWaveSimulationInput(
                    stateless_input=RebalanceRequest.model_validate(
                        claim.input_payload["stateless_input"]
                    )
                )
            },
            methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
            construction_repository=construction_repository,
            run_service=interrupted_run_service,
            risk_authority_client=None,
            construction_idempotency_key=(
                f"wave-operation:{operation.operation_id}:{claim.wave_item_id}:simulate"
            ),
        )
        assert committed.alternative_set_id is not None
        committed_ids[claim.wave_item_id] = committed.alternative_set_id

    def drain(worker_index: int) -> int:
        worker_repository = PostgresDpmWaveRepository(dsn=dsn)
        worker_construction_repository = PostgresConstructionRepository(dsn=dsn)
        run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
        completed_count = 0
        while True:
            current = worker_repository.get_simulation_operation(
                tenant_id=tenant_id, operation_id=operation.operation_id
            )
            assert current is not None
            if current.status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return completed_count
            _, claimed, completed, _ = wave_simulation_operations.execute_wave_simulation_work(
                tenant_id=tenant_id,
                operation_id=operation.operation_id,
                worker_id=f"replacement-worker-{worker_index}",
                max_items=1,
                lease_seconds=60,
                repository=worker_repository,
                construction_repository=worker_construction_repository,
                run_service=run_service,
                risk_authority_client=None,
            )
            completed_count += completed
            if claimed == 0:
                continue

    with ThreadPoolExecutor(max_workers=4) as executor:
        completed_per_worker = list(executor.map(drain, range(4)))

    assert sum(completed_per_worker) == 100
    results = repository.list_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        limit=200,
        offset=0,
    )
    assert results.total_count == 100
    assert len(results.items) == 100
    assert all(item.status == "SUCCEEDED" for item in results.items)
    assert all(item.result_item is not None for item in results.items)
    assert len({item.wave_item_id for item in results.items}) == 100
    assert (
        len({item.result_item.alternative_set_id for item in results.items if item.result_item})
        == 100
    )
    for claim in interrupted_claims:
        result = next(item for item in results.items if item.wave_item_id == claim.wave_item_id)
        assert result.attempt_count == 2
        assert result.result_item is not None
        assert result.result_item.alternative_set_id == committed_ids[claim.wave_item_id]

    oracle_repository = InMemoryConstructionRepository()
    oracle_run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    for result in results.items:
        assert result.result_item is not None
        alternative_set_id = result.result_item.alternative_set_id
        assert alternative_set_id is not None
        async_set = construction_repository.get_alternative_set(
            alternative_set_id=alternative_set_id
        )
        assert async_set is not None
        oracle_item = simulate_item(
            item=by_item_id[result.wave_item_id],
            correlation_id=f"oracle:{result.wave_item_id}",
            item_inputs={
                result.wave_item_id: DpmWaveSimulationInput(
                    stateless_input=RebalanceRequest.model_validate(
                        result.input_payload["stateless_input"]
                    )
                )
            },
            methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
            construction_repository=oracle_repository,
            run_service=oracle_run_service,
            risk_authority_client=None,
        )
        assert oracle_item.alternative_set_id is not None
        oracle_set = oracle_repository.get_alternative_set(
            alternative_set_id=oracle_item.alternative_set_id
        )
        assert oracle_set is not None
        assert [
            alternative.comparison_metrics.model_dump(mode="json")
            for alternative in async_set.alternatives
        ] == [
            alternative.comparison_metrics.model_dump(mode="json")
            for alternative in oracle_set.alternatives
        ]

    final_wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    assert final_wave is not None
    assert final_wave.state == "SIMULATED"
    assert final_wave.aggregate_metrics.state_counts == {"SIMULATED": 100}


def test_postgres_operation_controls_are_tenant_fenced_and_retry_cancel_safe(dsn: str) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    operation = _admit(
        repository=repository,
        tenant_id=tenant_id,
        wave_id=wave_id,
        operation_id=operation_id,
        item_count=2,
    )
    now = datetime.now(UTC)
    assert repository.get_simulation_operation(tenant_id="other", operation_id=operation_id) is None
    assert (
        repository.claim_simulation_items(
            tenant_id=tenant_id,
            operation_id="missing",
            worker_id="worker",
            limit=1,
            claimed_at=now,
            lease_expires_at=now + timedelta(minutes=1),
        )
        == []
    )
    assert (
        repository.retry_simulation_items(
            tenant_id=tenant_id,
            operation_id="missing",
            wave_item_ids=None,
            retried_at=now,
        )
        == 0
    )
    assert (
        repository.cancel_simulation_operation(
            tenant_id=tenant_id,
            operation_id="missing",
            reason_code="OPERATOR_CANCELLED",
            cancelled_at=now,
        )
        is None
    )
    assert repository.simulation_item_counts(tenant_id=tenant_id, operation_id=operation_id) == {
        "PENDING": 2,
        "RUNNING": 0,
        "SUCCEEDED": 0,
        "FAILED": 0,
        "CANCELLED": 0,
    }
    claim = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id="worker",
        limit=1,
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )[0]
    assert repository.publish_simulation_item_failure(
        claim=claim,
        error_code="DEPENDENCY_TIMEOUT",
        error_message="retryable",
        retryable=True,
        completed_at=now + timedelta(seconds=1),
    )
    assert (
        repository.retry_simulation_items(
            tenant_id=tenant_id,
            operation_id=operation_id,
            wave_item_ids=[claim.wave_item_id],
            retried_at=now + timedelta(seconds=2),
        )
        == 1
    )
    cancelled = repository.cancel_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        reason_code="OPERATOR_CANCELLED",
        cancelled_at=now + timedelta(seconds=3),
    )
    assert cancelled is not None
    assert cancelled.cancel_reason_code == "OPERATOR_CANCELLED"
    assert (
        repository.claim_simulation_items(
            tenant_id=tenant_id,
            operation_id=operation_id,
            worker_id="worker",
            limit=1,
            claimed_at=now + timedelta(seconds=4),
            lease_expires_at=now + timedelta(minutes=1),
        )
        == []
    )


def test_postgres_admission_refuses_ambiguous_or_stale_durable_identity(dsn: str) -> None:
    tenant_id, wave_id, operation_id = _ids()
    repository = PostgresDpmWaveRepository(dsn=dsn)
    wave = _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=1)
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id)
    now = datetime(2026, 10, 1, tzinfo=UTC)
    operation = DpmWaveSimulationOperation(
        operation_id=operation_id,
        tenant_id=tenant_id,
        wave_id=wave_id,
        request_hash="sha256:request-original",
        idempotency_key_hash="wsi-durable-admission",
        correlation_id="corr-durable-admission",
        actor_id="integration-test",
        source_identity_hash="sha256:source-original",
        admitted_wave_version=wave.version,
        methods=["HEURISTIC_EXPLAINABLE"],
        max_concurrency=1,
        max_attempts=2,
        created_at=now,
        updated_at=now,
    )
    item = DpmWaveSimulationItemRecord(
        operation_id=operation_id,
        tenant_id=tenant_id,
        wave_id=wave_id,
        wave_item_id=wave.items[0].wave_item_id,
        ordinal=0,
        portfolio_id=wave.items[0].portfolio_id,
        input_payload={"portfolio_id": wave.items[0].portfolio_id},
        input_hash="sha256:input-original",
        source_identity_hash="sha256:item-source-original",
        updated_at=now,
    )
    simulating_wave = wave.model_copy(update={"state": "SIMULATING", "version": wave.version + 1})
    stored, replayed = repository.admit_simulation_operation(
        operation=operation, items=[item], simulating_wave=simulating_wave
    )
    assert stored == operation
    assert replayed is False
    replay, replayed = repository.admit_simulation_operation(
        operation=operation, items=[item], simulating_wave=simulating_wave
    )
    assert replay == operation
    assert replayed is True
    with pytest.raises(DpmWaveSimulationOperationConflictError, match="IDEMPOTENCY_CONFLICT"):
        repository.admit_simulation_operation(
            operation=operation.model_copy(update={"request_hash": "sha256:request-changed"}),
            items=[item],
            simulating_wave=simulating_wave,
        )

    stale_wave_id = f"{wave_id}-stale"
    stale_wave = _wave(tenant_id=tenant_id, wave_id=stale_wave_id, item_count=1)
    repository.save_wave(
        wave=stale_wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id
    )
    stale_operation = operation.model_copy(
        update={
            "operation_id": f"{operation_id}-stale",
            "wave_id": stale_wave_id,
            "idempotency_key_hash": "wsi-durable-admission-stale",
            "correlation_id": "corr-durable-admission-stale",
            "admitted_wave_version": stale_wave.version + 1,
        }
    )
    stale_item = item.model_copy(
        update={
            "operation_id": stale_operation.operation_id,
            "wave_id": stale_wave_id,
            "wave_item_id": stale_wave.items[0].wave_item_id,
            "portfolio_id": stale_wave.items[0].portfolio_id,
        }
    )
    with pytest.raises(DpmWaveSimulationOperationConflictError, match="WAVE_VERSION_CONFLICT"):
        repository.admit_simulation_operation(
            operation=stale_operation,
            items=[stale_item],
            simulating_wave=stale_wave.model_copy(
                update={"state": "SIMULATING", "version": stale_wave.version + 1}
            ),
        )
