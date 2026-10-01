from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pytest import MonkeyPatch

from src.api.services import wave_simulation_operations
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
    derive_wave_simulation_operation_status_from_counts,
)
from src.core.waves.repository import DpmWaveVersionConflictError
from src.core.waves.simulation_repository import DpmWaveSimulationOperationConflictError
from src.infrastructure.waves.in_memory import InMemoryDpmWaveRepository
from src.infrastructure.waves import simulation_postgres
from src.infrastructure.waves.simulation_postgres import (
    _constraint_name,
    _validate_admission_items as validate_postgres_admission_items,
)
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.api.services.wave_simulation_operations import (
    _execute_claim,
    _operation_items_are_terminal,
    _reconciled_wave_items,
    _resolve_item_payloads,
    _simulation_inputs_for_claim,
    operation_counts,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.core.rebalance_runs.service import DpmRunSupportService

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


def test_admission_rejects_stale_or_ambiguous_durable_identity() -> None:
    """Admission must not persist a simulation against a different durable wave identity."""

    def fresh_repository() -> InMemoryDpmWaveRepository:
        candidate = InMemoryDpmWaveRepository()
        candidate.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT)
        return candidate

    cases = [
        (
            _operation().model_copy(update={"wave_id": "missing-wave"}),
            _items(),
            _simulating_wave().model_copy(update={"wave_id": "missing-wave"}),
            "DPM_WAVE_SIMULATION_WAVE_NOT_FOUND",
        ),
        (
            _operation().model_copy(update={"admitted_wave_version": 0}),
            _items(),
            _simulating_wave(),
            "DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT",
        ),
        (
            _operation(),
            _items(),
            _simulating_wave().model_copy(update={"version": 1}),
            "DPM_WAVE_SIMULATION_TRANSITION_CONFLICT",
        ),
        (
            _operation(),
            [_items()[0], _items()[0]],
            _simulating_wave(),
            "DPM_WAVE_SIMULATION_DUPLICATE_ITEM",
        ),
        (
            _operation(),
            [
                _items()[0].model_copy(update={"ordinal": 1}),
                *_items()[1:],
            ],
            _simulating_wave(),
            "DPM_WAVE_SIMULATION_ITEM_ORDINAL_CONFLICT",
        ),
        (
            _operation(),
            [_items()[0].model_copy(update={"portfolio_id": "portfolio-foreign"}), *_items()[1:]],
            _simulating_wave(),
            "DPM_WAVE_SIMULATION_ITEM_IDENTITY_CONFLICT",
        ),
    ]

    for operation, items, simulating_wave, expected_code in cases:
        with pytest.raises(DpmWaveSimulationOperationConflictError) as conflict:
            fresh_repository().admit_simulation_operation(
                operation=operation, items=items, simulating_wave=simulating_wave
            )
        assert str(conflict.value) == expected_code

    repository = fresh_repository()
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    second_operation = _operation().model_copy(
        update={
            "operation_id": "wso_async_second",
            "idempotency_key_hash": "wsi_tenant_second_key",
            "request_hash": "sha256:second-request",
            "admitted_wave_version": 2,
        }
    )
    second_items = [
        item.model_copy(update={"operation_id": second_operation.operation_id}) for item in _items()
    ]
    with pytest.raises(DpmWaveSimulationOperationConflictError) as conflict:
        repository.admit_simulation_operation(
            operation=second_operation,
            items=second_items,
            simulating_wave=_simulating_wave().model_copy(update={"version": 3}),
        )
    assert str(conflict.value) == "DPM_WAVE_SIMULATION_CORRELATION_CONFLICT"


@pytest.mark.parametrize(
    ("items", "expected_code"),
    [
        ([_items()[0], _items()[0]], "DPM_WAVE_SIMULATION_DUPLICATE_ITEM"),
        (
            [_items()[0].model_copy(update={"ordinal": 1}), *_items()[1:]],
            "DPM_WAVE_SIMULATION_ITEM_ORDINAL_CONFLICT",
        ),
        (
            [
                _items()[0].model_copy(update={"portfolio_id": "portfolio-foreign"}),
                *_items()[1:],
            ],
            "DPM_WAVE_SIMULATION_ITEM_IDENTITY_CONFLICT",
        ),
    ],
)
def test_postgres_admission_item_validation_matches_durable_contract(
    items: list[DpmWaveSimulationItemRecord], expected_code: str
) -> None:
    """Validate malformed item batches before they can enter a PostgreSQL transaction."""

    with pytest.raises(DpmWaveSimulationOperationConflictError) as conflict:
        validate_postgres_admission_items(operation=_operation(), items=items, wave=_wave())

    assert str(conflict.value) == expected_code


def test_postgres_constraint_name_handles_driver_diagnostics_without_leaking_driver_types() -> None:
    class DriverError(Exception):
        def __init__(self, constraint_name: str | None) -> None:
            self.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()

    assert _constraint_name(DriverError("dpm_wave_simulation_idempotency_key_hash_key")) == (
        "dpm_wave_simulation_idempotency_key_hash_key"
    )
    assert _constraint_name(DriverError(None)) is None
    assert _constraint_name(Exception("unstructured")) is None


def test_postgres_admission_maps_unique_constraint_races_to_stable_conflicts(
    monkeypatch: MonkeyPatch,
) -> None:
    """Concurrent inserts surface public idempotency/correlation conflicts, never driver details."""

    class DriverError(Exception):
        def __init__(self, constraint_name: str) -> None:
            self.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()

    class Cursor:
        def fetchone(self) -> dict[str, object]:
            return {"version": 1, "wave_json": {}}

    class Connection:
        rolled_back = False

        def execute(self, *_: object) -> Cursor:
            return Cursor()

        def commit(self) -> None:
            raise AssertionError("a failed admission must not commit")

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            return None

    class Repository(simulation_postgres.PostgresDpmWaveSimulationMixin):
        def __init__(self, connection: Connection) -> None:
            self._connection = connection

        def _connect(self) -> Connection:
            return self._connection

    monkeypatch.setattr(simulation_postgres, "load_model_json", lambda *_: _wave())
    monkeypatch.setattr(simulation_postgres, "_select_operation_by_idempotency", lambda **_: None)
    monkeypatch.setattr(simulation_postgres, "_select_operation_by_correlation", lambda **_: None)

    for constraint_name, expected_code in [
        ("dpm_wave_simulation_idempotency_key_hash_key", "IDEMPOTENCY_CONFLICT"),
        ("dpm_wave_simulation_correlation_key", "CORRELATION_CONFLICT"),
    ]:
        connection = Connection()

        def fail_insert(**_: object) -> None:
            raise DriverError(constraint_name)

        monkeypatch.setattr(simulation_postgres, "_insert_operation", fail_insert)
        with pytest.raises(DpmWaveSimulationOperationConflictError, match=expected_code):
            Repository(connection).admit_simulation_operation(
                operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
            )
        assert connection.rolled_back is True

    connection = Connection()

    def fail_unknown_constraint(**_: object) -> None:
        raise DriverError("dpm_wave_simulation_unexpected_constraint")

    monkeypatch.setattr(simulation_postgres, "_insert_operation", fail_unknown_constraint)
    with pytest.raises(DriverError, match="unexpected_constraint"):
        Repository(connection).admit_simulation_operation(
            operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
        )
    assert connection.rolled_back is True


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
    repeated = repository.cancel_simulation_operation(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        reason_code="SECOND_CANCEL_IGNORED",
        cancelled_at=NOW + timedelta(seconds=8),
    )
    assert repeated is not None
    assert repeated.status == "CANCEL_REQUESTED"
    assert repeated.cancel_reason_code == "OPERATOR_CANCELLED"


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


def test_claim_and_retry_refuse_unknown_cancelled_and_exhausted_operations(
    repository: InMemoryDpmWaveRepository,
) -> None:
    """Bounded workers never claim or revive work outside a live retry budget."""

    assert repository.simulation_item_counts(tenant_id=TENANT, operation_id="missing") == {}
    assert (
        repository.claim_simulation_items(
            tenant_id=TENANT,
            operation_id="missing",
            worker_id="worker-missing",
            limit=1,
            claimed_at=NOW,
            lease_expires_at=NOW + timedelta(minutes=1),
        )
        == []
    )

    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-attempt-two",
        limit=1,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(seconds=1),
    )[0]
    assert repository.publish_simulation_item_failure(
        claim=claim,
        error_code="TRANSIENT",
        error_message="retryable before budget is exhausted",
        retryable=True,
        completed_at=NOW + timedelta(seconds=1),
    )
    assert (
        repository.retry_simulation_items(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            wave_item_ids=[claim.wave_item_id],
            retried_at=NOW + timedelta(seconds=1),
        )
        == 1
    )
    second_claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-attempt-two",
        limit=1,
        claimed_at=NOW + timedelta(seconds=2),
        lease_expires_at=NOW + timedelta(minutes=1),
    )[0]
    assert second_claim.attempt_count == 2
    assert repository.publish_simulation_item_failure(
        claim=second_claim,
        error_code="TRANSIENT",
        error_message="retry budget exhausted",
        retryable=True,
        completed_at=NOW + timedelta(seconds=3),
    )
    assert (
        repository.retry_simulation_items(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            wave_item_ids=[second_claim.wave_item_id],
            retried_at=NOW + timedelta(seconds=4),
        )
        == 0
    )

    assert (
        repository.cancel_simulation_operation(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            reason_code="OPERATOR_CANCELLED",
            cancelled_at=NOW + timedelta(seconds=5),
        )
        is not None
    )
    assert (
        repository.claim_simulation_items(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            worker_id="worker-after-cancel",
            limit=1,
            claimed_at=NOW + timedelta(seconds=6),
            lease_expires_at=NOW + timedelta(minutes=1),
        )
        == []
    )
    assert (
        repository.retry_simulation_items(
            tenant_id=TENANT,
            operation_id=OPERATION_ID,
            wave_item_ids=None,
            retried_at=NOW + timedelta(seconds=7),
        )
        == 0
    )


def test_simulation_input_resolution_and_terminal_policy_fail_closed() -> None:
    wave = _wave()
    valid_input = {"portfolio_snapshot": {"portfolio_id": "portfolio-0"}}
    assert _resolve_item_payloads(
        wave=wave,
        item_payloads=[{"portfolio_id": "portfolio-0", "stateless_input": valid_input}],
    ) == {"item-0": {"stateless_input": valid_input}}
    with pytest.raises(DpmWaveValidationError, match="resolve to exactly one wave item"):
        _resolve_item_payloads(wave=wave, item_payloads=[{"portfolio_id": "missing"}])
    with pytest.raises(DpmWaveValidationError, match="Conflicting inputs"):
        _resolve_item_payloads(
            wave=wave,
            item_payloads=[
                {"wave_item_id": "item-0", "stateless_input": valid_input},
                {
                    "wave_item_id": "item-0",
                    "stateless_input": {
                        "portfolio_snapshot": {"portfolio_id": "portfolio-0"},
                        "variant": "two",
                    },
                },
            ],
        )
    for invalid_payload in [
        {"stateless_input": valid_input},
        {"wave_item_id": "missing", "portfolio_id": "portfolio-0", "stateless_input": valid_input},
        {"wave_item_id": "item-0", "portfolio_id": "portfolio-1", "stateless_input": valid_input},
        {
            "wave_item_id": "item-0",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "foreign"}},
        },
    ]:
        with pytest.raises(DpmWaveValidationError) as conflict:
            _resolve_item_payloads(wave=wave, item_payloads=[invalid_payload])
        assert conflict.value.code in {
            "DPM_WAVE_SIMULATION_INPUT_IDENTITY_CONFLICT",
            "DPM_WAVE_SIMULATION_INPUT_ITEM_NOT_FOUND",
        }
    records = _items()
    records[0] = records[0].model_copy(update={"status": "FAILED", "retryable": True})
    assert _operation_items_are_terminal(operation=_operation(), items=records) is False
    records[0] = records[0].model_copy(update={"attempt_count": 2})
    for index in range(1, 4):
        records[index] = records[index].model_copy(update={"status": "SUCCEEDED"})
    assert _operation_items_are_terminal(operation=_operation(), items=records) is True
    assert operation_counts(records) == {
        "PENDING": 0,
        "RUNNING": 0,
        "SUCCEEDED": 3,
        "FAILED": 1,
        "CANCELLED": 0,
    }


def test_reconciliation_keeps_absent_record_and_blocks_failed_record() -> None:
    wave = _wave()
    failed = _items()[0].model_copy(
        update={
            "status": "FAILED",
            "error_code": "SOURCE_CONFLICT",
            "error_message": "source changed",
            "attempt_count": 2,
        }
    )
    reconciled = _reconciled_wave_items(wave=wave, records=[failed])
    assert reconciled[0].state == "SIMULATION_BLOCKED"
    assert reconciled[0].reason_codes == ["SOURCE_CONFLICT"]
    assert reconciled[1:] == wave.items[1:]
    claim = repository_claim_for_input_test()
    assert _simulation_inputs_for_claim(claim) == {}


def test_operation_admission_and_reconciliation_fail_closed_on_missing_or_contended_waves(
    repository: InMemoryDpmWaveRepository, monkeypatch: MonkeyPatch
) -> None:
    """Service boundaries translate missing and repeatedly contended durable waves deterministically."""

    with pytest.raises(DpmWaveLookupError, match="missing-wave"):
        wave_simulation_operations.admit_wave_simulation_operation(
            wave_id="missing-wave",
            tenant_id=TENANT,
            actor_id="test",
            correlation_id="missing-wave",
            idempotency_key="missing-wave",
            item_payloads=[],
            methods=None,
            max_concurrency=1,
            max_attempts=1,
            repository=repository,
        )

    def reject_admission(**_: object) -> None:
        raise DpmWaveSimulationOperationConflictError("DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT")

    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(repository, "admit_simulation_operation", reject_admission)
        with pytest.raises(DpmWaveValidationError) as conflict:
            wave_simulation_operations.admit_wave_simulation_operation(
                wave_id=WAVE_ID,
                tenant_id=TENANT,
                actor_id="test",
                correlation_id="conflicted-wave",
                idempotency_key="conflicted-wave",
                item_payloads=[],
                methods=None,
                max_concurrency=1,
                max_attempts=1,
                repository=repository,
            )
    assert conflict.value.code == "DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT"

    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    stored = repository._simulation_items[(OPERATION_ID, "item-0")]
    repository._simulation_items[(OPERATION_ID, "item-0")] = stored.model_copy(
        update={
            "status": "FAILED",
            "error_code": "DURABLE_SOURCE_FAILURE",
            "error_message": "requires terminal reconciliation",
        }
    )

    def reject_update(**_: object) -> None:
        raise DpmWaveVersionConflictError("DPM_WAVE_VERSION_CONFLICT")

    monkeypatch.setattr(repository, "update_wave", reject_update)
    with pytest.raises(DpmWaveValidationError) as conflict:
        wave_simulation_operations.reconcile_wave_simulation_operation(
            tenant_id=TENANT, operation_id=OPERATION_ID, repository=repository
        )
    assert conflict.value.code == "DPM_WAVE_SIMULATION_RECONCILIATION_CONFLICT"

    disappeared_repository = InMemoryDpmWaveRepository()
    disappeared_repository.save_wave(
        wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT
    )
    disappeared_repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    disappeared_repository._waves.pop(WAVE_ID)
    with pytest.raises(DpmWaveLookupError, match=WAVE_ID):
        wave_simulation_operations.reconcile_wave_simulation_operation(
            tenant_id=TENANT, operation_id=OPERATION_ID, repository=disappeared_repository
        )


def test_simulation_item_paging_and_terminal_count_state_are_complete() -> None:
    """A multi-page worker reconciliation retains all durable items and terminal dispositions."""

    first, second = _items()[:2]

    class PagedRepository:
        def list_simulation_items(
            self, *, tenant_id: str, operation_id: str, limit: int, offset: int
        ) -> DpmWaveSimulationItemPage:
            assert (tenant_id, operation_id, limit) == (TENANT, OPERATION_ID, 500)
            if offset == 0:
                return DpmWaveSimulationItemPage(items=[first], total_count=2, next_offset=1)
            return DpmWaveSimulationItemPage(items=[second], total_count=2, next_offset=None)

    assert wave_simulation_operations._all_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, repository=PagedRepository()
    ) == [first, second]
    operation = _operation()
    assert (
        derive_wave_simulation_operation_status_from_counts(
            operation=operation,
            total_count=2,
            pending_count=0,
            running_count=0,
            succeeded_count=1,
            failed_count=1,
            cancelled_count=0,
            retry_waiting_count=0,
        )
        == "PARTIALLY_COMPLETED"
    )
    assert (
        derive_wave_simulation_operation_status_from_counts(
            operation=operation,
            total_count=2,
            pending_count=0,
            running_count=0,
            succeeded_count=0,
            failed_count=0,
            cancelled_count=1,
            retry_waiting_count=0,
        )
        == "PENDING"
    )
    assert (
        derive_wave_simulation_operation_status_from_counts(
            operation=operation,
            total_count=2,
            pending_count=0,
            running_count=0,
            succeeded_count=2,
            failed_count=0,
            cancelled_count=0,
            retry_waiting_count=0,
        )
        == "SUCCEEDED"
    )
    assert (
        derive_wave_simulation_operation_status_from_counts(
            operation=operation,
            total_count=2,
            pending_count=0,
            running_count=0,
            succeeded_count=0,
            failed_count=2,
            cancelled_count=0,
            retry_waiting_count=0,
        )
        == "FAILED"
    )


def test_worker_persists_non_retryable_failures_when_admitted_wave_or_item_disappears(
    repository: InMemoryDpmWaveRepository,
) -> None:
    """A claimed item must become terminal rather than silently vanish during a wave mutation."""

    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claimed_at = datetime.now(UTC)
    wave_claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-missing-wave",
        limit=1,
        claimed_at=claimed_at,
        lease_expires_at=claimed_at + timedelta(minutes=1),
    )[0]
    repository._waves.pop(WAVE_ID)
    run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    assert not _execute_claim(
        claim=wave_claim,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=run_service,
        risk_authority_client=None,
        methods=None,
    )
    failed = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=10, offset=0
    ).items[0]
    assert (failed.status, failed.error_code, failed.retryable) == (
        "FAILED",
        "DPM_WAVE_SIMULATION_ITEM_NOT_FOUND",
        False,
    )

    item_repository = InMemoryDpmWaveRepository()
    item_repository.save_wave(
        wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT
    )
    item_repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claimed_at = datetime.now(UTC)
    item_claim = item_repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-missing-item",
        limit=1,
        claimed_at=claimed_at,
        lease_expires_at=claimed_at + timedelta(minutes=1),
    )[0]
    current_wave = item_repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT)
    assert current_wave is not None
    item_repository._waves[WAVE_ID] = current_wave.model_copy(
        update={"items": current_wave.items[1:]}
    )
    assert not _execute_claim(
        claim=item_claim,
        repository=item_repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=DpmRunSupportService(repository=InMemoryDpmRunRepository()),
        risk_authority_client=None,
        methods=None,
    )
    failed = item_repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=10, offset=0
    ).items[0]
    assert (failed.status, failed.error_code, failed.retryable) == (
        "FAILED",
        "DPM_WAVE_SIMULATION_ITEM_NOT_FOUND",
        False,
    )


def test_worker_persists_retryable_construction_exception(
    repository: InMemoryDpmWaveRepository, monkeypatch: MonkeyPatch
) -> None:
    """Transient construction exceptions remain visible and retryable to another worker."""

    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claimed_at = datetime.now(UTC)
    claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-construction-error",
        limit=1,
        claimed_at=claimed_at,
        lease_expires_at=claimed_at + timedelta(minutes=1),
    )[0]

    def fail_construction(**_: object) -> DpmRebalanceWaveItem:
        raise RuntimeError("temporary construction outage")

    monkeypatch.setattr(wave_simulation_operations, "simulate_item", fail_construction)
    monkeypatch.setattr(
        wave_simulation_operations,
        "_wave_item_source_identity_hash",
        lambda **_kwargs: claim.source_identity_hash,
    )
    assert not _execute_claim(
        claim=claim,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=DpmRunSupportService(repository=InMemoryDpmRunRepository()),
        risk_authority_client=None,
        methods=None,
    )
    failed = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=10, offset=0
    ).items[0]
    assert (failed.status, failed.error_code, failed.error_message, failed.retryable) == (
        "FAILED",
        "DPM_WAVE_SIMULATION_WORKER_FAILURE",
        "RuntimeError",
        True,
    )


def repository_claim_for_input_test():
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT)
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    return repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-input",
        limit=1,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(minutes=1),
    )[0]


def test_worker_persists_terminal_failure_for_recovery_and_disappearing_wave() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT)
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-a",
        limit=1,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(seconds=1),
    )[0]
    replacement = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-b",
        limit=1,
        claimed_at=NOW + timedelta(seconds=2),
        lease_expires_at=NOW + timedelta(seconds=3),
    )[0]
    exhausted = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-c",
        limit=1,
        claimed_at=NOW + timedelta(seconds=4),
        lease_expires_at=NOW + timedelta(seconds=5),
    )[0]
    assert replacement.recovery_exhausted is False
    assert exhausted.recovery_exhausted is True
    run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    assert not _execute_claim(
        claim=exhausted,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=run_service,
        risk_authority_client=None,
        methods=None,
    )
    next_claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-d",
        limit=1,
        claimed_at=NOW + timedelta(seconds=6),
        lease_expires_at=NOW + timedelta(minutes=1),
    )[0]
    repository._waves.pop(WAVE_ID)
    assert not _execute_claim(
        claim=next_claim,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=run_service,
        risk_authority_client=None,
        methods=None,
    )


def test_worker_refuses_identity_conflict_result_before_publishing_success(
    repository: InMemoryDpmWaveRepository, monkeypatch: MonkeyPatch
) -> None:
    repository.admit_simulation_operation(
        operation=_operation(), items=_items(), simulating_wave=_simulating_wave()
    )
    claim = repository.claim_simulation_items(
        tenant_id=TENANT,
        operation_id=OPERATION_ID,
        worker_id="worker-identity",
        limit=1,
        claimed_at=datetime.now(UTC),
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )[0]
    identity_blocked_item = (
        _wave()
        .items[0]
        .model_copy(
            update={
                "state": "SIMULATION_BLOCKED",
                "reason_codes": ["DPM_WAVE_SIMULATION_INPUT_IDENTITY_CONFLICT"],
            }
        )
    )
    monkeypatch.setattr(
        wave_simulation_operations, "simulate_item", lambda **_kwargs: identity_blocked_item
    )
    monkeypatch.setattr(
        wave_simulation_operations,
        "_wave_item_source_identity_hash",
        lambda **_kwargs: "sha256:source-0",
    )

    assert not _execute_claim(
        claim=claim,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=DpmRunSupportService(repository=InMemoryDpmRunRepository()),
        risk_authority_client=None,
        methods=None,
    )
    item = repository.list_simulation_items(
        tenant_id=TENANT, operation_id=OPERATION_ID, limit=1, offset=0
    ).items[0]
    assert item.status == "FAILED"
    assert item.retryable is False
    assert item.result_item is None
    assert item.error_code == "DPM_WAVE_SIMULATION_INPUT_IDENTITY_CONFLICT"
