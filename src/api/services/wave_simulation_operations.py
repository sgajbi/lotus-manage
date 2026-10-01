"""Durable admission, worker execution, and recovery for wave simulation."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from src.api.request_models import RebalanceRequest
from src.api.observability import record_async_operation
from src.api.services.authority_client_service import RiskAuthorityClient
from src.api.services.wave_aggregate_metrics import aggregate_wave_items, simulation_result_state
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_simulation_item import DpmWaveSimulationInput, simulate_item
from src.core.common.canonical import hash_canonical_payload
from src.core.common.derived_identity import derived_identity
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, apply_wave_transition
from src.core.waves.repository import DpmWaveVersionConflictError
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemClaim,
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
)
from src.core.waves.simulation_repository import (
    DpmWaveSimulationOperationConflictError,
    DpmWaveSimulationRepository,
    wave_simulation_idempotency_key,
)


def admit_wave_simulation_operation(
    *,
    wave_id: str,
    tenant_id: str,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    item_payloads: list[dict[str, object]],
    methods: list[ConstructionMethod] | None,
    max_concurrency: int,
    max_attempts: int,
    repository: DpmWaveSimulationRepository,
) -> tuple[DpmWaveSimulationOperation, bool]:
    wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    resolved_inputs = _resolve_item_payloads(wave=wave, item_payloads=item_payloads)
    now = datetime.now(UTC)
    idempotency_hash = wave_simulation_idempotency_key(
        tenant_id=tenant_id, idempotency_key=idempotency_key
    )
    operation_id = derived_identity("wso", tenant_id, wave_id, idempotency_key)
    method_values = [] if methods is None else [method.value for method in methods]
    item_records = [
        _build_item_record(
            operation_id=operation_id,
            tenant_id=tenant_id,
            wave=wave,
            item=item,
            ordinal=ordinal,
            input_payload=resolved_inputs.get(item.wave_item_id, {}),
            now=now,
        )
        for ordinal, item in enumerate(wave.items)
    ]
    source_identity_hash = hash_canonical_payload(
        {
            "wave_id": wave.wave_id,
            "wave_version": wave.version,
            "as_of_date": wave.as_of_date,
            "trigger": wave.trigger.model_dump(mode="json"),
            "items": [
                {
                    "wave_item_id": item.wave_item_id,
                    "source_identity_hash": item.source_identity_hash,
                }
                for item in item_records
            ],
        }
    )
    request_hash = hash_canonical_payload(
        {
            "wave_id": wave_id,
            "actor_id": actor_id,
            "methods": method_values,
            "max_concurrency": max_concurrency,
            "max_attempts": max_attempts,
            "items": [
                {
                    "wave_item_id": item.wave_item_id,
                    "input_hash": item.input_hash,
                    "source_identity_hash": item.source_identity_hash,
                }
                for item in item_records
            ],
        }
    )
    existing = repository.get_simulation_operation_by_idempotency(
        tenant_id=tenant_id,
        idempotency_key_hash=idempotency_hash,
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            record_async_operation(event="submit", execution_mode="accept_only", outcome="conflict")
            raise DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT",
                "The idempotency key already owns different immutable simulation input.",
            )
        record_async_operation(event="submit", execution_mode="accept_only", outcome="accepted")
        return existing, True
    if wave.state != "SOURCE_CHECKED":
        record_async_operation(
            event="submit", execution_mode="accept_only", outcome="not_executable"
        )
        raise DpmWaveValidationError(
            "DPM_WAVE_SIMULATION_INVALID_STATE",
            f"Wave {wave_id} must be SOURCE_CHECKED before asynchronous simulation.",
        )
    operation = DpmWaveSimulationOperation(
        operation_id=operation_id,
        tenant_id=tenant_id,
        wave_id=wave_id,
        request_hash=request_hash,
        idempotency_key_hash=idempotency_hash,
        correlation_id=correlation_id,
        actor_id=actor_id,
        source_identity_hash=source_identity_hash,
        admitted_wave_version=wave.version,
        methods=method_values,
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
    )
    simulating_wave = apply_wave_transition(
        wave=wave,
        to_state="SIMULATING",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="SOURCE_CHECKED",
            to_state="SIMULATING",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_ASYNC_SIMULATION_ACCEPTED",
            metadata={
                "operation_id": operation_id,
                "item_count": len(item_records),
                "max_concurrency": max_concurrency,
                "max_attempts": max_attempts,
                "source_identity_hash": source_identity_hash,
            },
        ),
    )
    try:
        admitted = repository.admit_simulation_operation(
            operation=operation,
            items=item_records,
            simulating_wave=simulating_wave,
        )
        record_async_operation(event="submit", execution_mode="accept_only", outcome="accepted")
        return admitted
    except DpmWaveSimulationOperationConflictError as exc:
        record_async_operation(event="submit", execution_mode="accept_only", outcome="conflict")
        code = str(exc)
        raise DpmWaveValidationError(code, code) from exc


def execute_wave_simulation_work(
    *,
    tenant_id: str,
    operation_id: str,
    worker_id: str,
    max_items: int,
    lease_seconds: int,
    repository: DpmWaveSimulationRepository,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    risk_authority_client: RiskAuthorityClient | None,
) -> tuple[DpmWaveSimulationOperation, int, int, int]:
    admitted_operation = get_wave_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        repository=repository,
    )
    methods = (
        None
        if not admitted_operation.methods
        else [ConstructionMethod(method) for method in admitted_operation.methods]
    )
    claimed_at = datetime.now(UTC)
    claims = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        worker_id=worker_id,
        limit=max_items,
        claimed_at=claimed_at,
        lease_expires_at=claimed_at + timedelta(seconds=lease_seconds),
    )
    completed_count = 0
    failed_count = 0
    for claim in claims:
        if _execute_claim(
            claim=claim,
            repository=repository,
            construction_repository=construction_repository,
            run_service=run_service,
            risk_authority_client=risk_authority_client,
            methods=methods,
        ):
            completed_count += 1
        else:
            failed_count += 1
    reconcile_wave_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        repository=repository,
    )
    operation = get_wave_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        repository=repository,
    )
    record_async_operation(
        event="execute",
        execution_mode="manual",
        outcome=("not_executable" if not claims else "failed" if failed_count else "succeeded"),
    )
    return operation, len(claims), completed_count, failed_count


def get_wave_simulation_operation(
    *,
    tenant_id: str,
    operation_id: str,
    repository: DpmWaveSimulationRepository,
) -> DpmWaveSimulationOperation:
    operation = repository.get_simulation_operation(tenant_id=tenant_id, operation_id=operation_id)
    if operation is None:
        raise DpmWaveLookupError(
            "DPM_WAVE_SIMULATION_OPERATION_NOT_FOUND",
            f"Simulation operation {operation_id} was not found.",
        )
    return operation


def get_wave_simulation_results(
    *,
    tenant_id: str,
    operation_id: str,
    limit: int,
    offset: int,
    repository: DpmWaveSimulationRepository,
) -> tuple[DpmWaveSimulationOperation, DpmWaveSimulationItemPage]:
    operation = get_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    reconcile_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    operation = get_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    page = repository.list_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        limit=limit,
        offset=offset,
    )
    return operation, page


def retry_wave_simulation_operation(
    *,
    tenant_id: str,
    operation_id: str,
    wave_item_ids: list[str] | None,
    repository: DpmWaveSimulationRepository,
) -> tuple[DpmWaveSimulationOperation, int]:
    get_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    count = repository.retry_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        wave_item_ids=wave_item_ids,
        retried_at=datetime.now(UTC),
    )
    return (
        get_wave_simulation_operation(
            tenant_id=tenant_id, operation_id=operation_id, repository=repository
        ),
        count,
    )


def cancel_wave_simulation_operation(
    *,
    tenant_id: str,
    operation_id: str,
    reason_code: str,
    repository: DpmWaveSimulationRepository,
) -> DpmWaveSimulationOperation:
    operation = repository.cancel_simulation_operation(
        tenant_id=tenant_id,
        operation_id=operation_id,
        reason_code=reason_code,
        cancelled_at=datetime.now(UTC),
    )
    if operation is None:
        raise DpmWaveLookupError(
            "DPM_WAVE_SIMULATION_OPERATION_NOT_FOUND",
            f"Simulation operation {operation_id} was not found.",
        )
    reconcile_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    return get_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )


def operation_counts(items: list[DpmWaveSimulationItemRecord]) -> dict[str, int]:
    counts = Counter(item.status for item in items)
    return {
        status: counts.get(status, 0)
        for status in ("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED")
    }


def reconcile_wave_simulation_operation(
    *,
    tenant_id: str,
    operation_id: str,
    repository: DpmWaveSimulationRepository,
) -> DpmRebalanceWave:
    operation = get_wave_simulation_operation(
        tenant_id=tenant_id, operation_id=operation_id, repository=repository
    )
    records = _all_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation_id,
        repository=repository,
    )
    for _ in range(5):
        wave = repository.get_wave(wave_id=operation.wave_id, tenant_id=tenant_id)
        if wave is None:
            raise DpmWaveLookupError(
                "DPM_WAVE_NOT_FOUND", f"Wave {operation.wave_id} was not found."
            )
        if wave.state != "SIMULATING":
            return wave
        reconciled_items = _reconciled_wave_items(wave=wave, records=records)
        terminal = _operation_items_are_terminal(operation=operation, items=records)
        candidate = wave.model_copy(
            update={
                "items": reconciled_items,
                "aggregate_metrics": aggregate_wave_items(reconciled_items),
            },
            deep=True,
        )
        if terminal:
            final_state = simulation_result_state(reconciled_items)
            candidate = apply_wave_transition(
                wave=candidate,
                to_state=final_state,
                event=build_wave_event(
                    wave_id=wave.wave_id,
                    from_state="SIMULATING",
                    to_state=final_state,
                    actor_id=operation.actor_id,
                    correlation_id=operation.correlation_id,
                    reason_code="WAVE_ASYNC_SIMULATION_COMPLETED",
                    metadata={
                        "operation_id": operation.operation_id,
                        "operation_status": operation.status,
                        "state_counts": candidate.aggregate_metrics.state_counts,
                    },
                ),
            )
        elif reconciled_items != wave.items:
            candidate = candidate.model_copy(update={"version": wave.version + 1})
        else:
            return wave
        try:
            repository.update_wave(
                wave=candidate, expected_version=wave.version, tenant_id=tenant_id
            )
            return candidate
        except DpmWaveVersionConflictError:
            continue
    raise DpmWaveValidationError(
        "DPM_WAVE_SIMULATION_RECONCILIATION_CONFLICT",
        "Wave simulation checkpoints could not be reconciled after concurrent updates.",
    )


def _execute_claim(
    *,
    claim: DpmWaveSimulationItemClaim,
    repository: DpmWaveSimulationRepository,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    risk_authority_client: RiskAuthorityClient | None,
    methods: list[ConstructionMethod] | None,
) -> bool:
    completed_at = datetime.now(UTC)
    if claim.recovery_exhausted:
        repository.publish_simulation_item_failure(
            claim=claim,
            error_code="DPM_WAVE_SIMULATION_RETRY_EXHAUSTED",
            error_message="The prior worker lease expired after the maximum financial-work claims.",
            retryable=False,
            completed_at=completed_at,
        )
        return False
    wave = repository.get_wave(wave_id=claim.wave_id, tenant_id=claim.tenant_id)
    if wave is None:
        repository.publish_simulation_item_failure(
            claim=claim,
            error_code="DPM_WAVE_SIMULATION_ITEM_NOT_FOUND",
            error_message="The admitted wave is no longer available.",
            retryable=False,
            completed_at=completed_at,
        )
        return False
    item = next(
        (candidate for candidate in wave.items if candidate.wave_item_id == claim.wave_item_id),
        None,
    )
    if item is None:
        repository.publish_simulation_item_failure(
            claim=claim,
            error_code="DPM_WAVE_SIMULATION_ITEM_NOT_FOUND",
            error_message="The admitted wave item is no longer available.",
            retryable=False,
            completed_at=completed_at,
        )
        return False
    if _wave_item_source_identity_hash(wave=wave, item=item) != claim.source_identity_hash:
        repository.publish_simulation_item_failure(
            claim=claim,
            error_code="DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT",
            error_message="The wave item source identity changed after operation admission.",
            retryable=False,
            completed_at=completed_at,
        )
        return False
    try:
        inputs = _simulation_inputs_for_claim(claim)
        result_item = simulate_item(
            item=item,
            correlation_id=f"{claim.operation_id}:{claim.wave_item_id}",
            item_inputs=inputs,
            methods=methods,
            construction_repository=construction_repository,
            run_service=run_service,
            risk_authority_client=risk_authority_client,
            construction_idempotency_key=(
                f"wave-operation:{claim.operation_id}:{claim.wave_item_id}:simulate"
            ),
        )
    except Exception as exc:  # noqa: BLE001 - worker boundary persists typed failure before retry
        repository.publish_simulation_item_failure(
            claim=claim,
            error_code="DPM_WAVE_SIMULATION_WORKER_FAILURE",
            error_message=type(exc).__name__,
            retryable=True,
            completed_at=datetime.now(UTC),
        )
        return False
    published = repository.publish_simulation_item_result(
        claim=claim,
        result_item=result_item,
        completed_at=datetime.now(UTC),
    )
    return published


def _resolve_item_payloads(
    *, wave: DpmRebalanceWave, item_payloads: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    by_id = {item.wave_item_id: item for item in wave.items}
    by_portfolio: dict[str, list[DpmRebalanceWaveItem]] = {}
    for wave_item in wave.items:
        by_portfolio.setdefault(wave_item.portfolio_id, []).append(wave_item)
    resolved: dict[str, dict[str, object]] = {}
    for supplied in item_payloads:
        wave_item_id = supplied.get("wave_item_id")
        portfolio_id = supplied.get("portfolio_id")
        resolved_item = by_id.get(str(wave_item_id)) if wave_item_id else None
        if resolved_item is None and portfolio_id:
            matches = by_portfolio.get(str(portfolio_id), [])
            if len(matches) == 1:
                resolved_item = matches[0]
        if resolved_item is None:
            raise DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_INPUT_ITEM_NOT_FOUND",
                "Each simulation input must resolve to exactly one wave item.",
            )
        payload = {
            key: value
            for key, value in supplied.items()
            if key in {"stateless_input", "authority_context"} and value is not None
        }
        existing = resolved.get(resolved_item.wave_item_id)
        if existing is not None and existing != payload:
            raise DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_INPUT_CONFLICT",
                f"Conflicting inputs were supplied for wave item {resolved_item.wave_item_id}.",
            )
        resolved[resolved_item.wave_item_id] = payload
    return resolved


def _build_item_record(
    *,
    operation_id: str,
    tenant_id: str,
    wave: DpmRebalanceWave,
    item: DpmRebalanceWaveItem,
    ordinal: int,
    input_payload: dict[str, object],
    now: datetime,
) -> DpmWaveSimulationItemRecord:
    return DpmWaveSimulationItemRecord(
        operation_id=operation_id,
        tenant_id=tenant_id,
        wave_id=wave.wave_id,
        wave_item_id=item.wave_item_id,
        ordinal=ordinal,
        portfolio_id=item.portfolio_id,
        input_payload=input_payload,
        input_hash=hash_canonical_payload(input_payload),
        source_identity_hash=_wave_item_source_identity_hash(wave=wave, item=item),
        updated_at=now,
    )


def _wave_item_source_identity_hash(*, wave: DpmRebalanceWave, item: DpmRebalanceWaveItem) -> str:
    return hash_canonical_payload(
        {
            "wave_id": wave.wave_id,
            "as_of_date": wave.as_of_date,
            "wave_item_id": item.wave_item_id,
            "portfolio_id": item.portfolio_id,
            "mandate_id": item.mandate_id,
            "model_portfolio_id": item.model_portfolio_id,
            "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
        }
    )


def _simulation_inputs_for_claim(
    claim: DpmWaveSimulationItemClaim,
) -> dict[str, RebalanceRequest | DpmWaveSimulationInput]:
    stateless_payload = claim.input_payload.get("stateless_input")
    if not isinstance(stateless_payload, dict):
        return {}
    authority_payload = claim.input_payload.get("authority_context")
    authority_context = (
        ConstructionAuthorityContext.model_validate(authority_payload)
        if isinstance(authority_payload, dict)
        else None
    )
    return {
        claim.wave_item_id: DpmWaveSimulationInput(
            stateless_input=RebalanceRequest.model_validate(stateless_payload),
            authority_context=authority_context,
        )
    }


def _reconciled_wave_items(
    *, wave: DpmRebalanceWave, records: list[DpmWaveSimulationItemRecord]
) -> list[DpmRebalanceWaveItem]:
    by_id = {record.wave_item_id: record for record in records}
    reconciled: list[DpmRebalanceWaveItem] = []
    for item in wave.items:
        record = by_id.get(item.wave_item_id)
        if record is None:
            reconciled.append(item)
        elif record.result_item is not None:
            reconciled.append(record.result_item)
        elif record.status in {"FAILED", "CANCELLED"}:
            reconciled.append(
                item.model_copy(
                    update={
                        "state": "SIMULATION_BLOCKED",
                        "reason_codes": [
                            record.error_code
                            or (
                                "DPM_WAVE_SIMULATION_CANCELLED"
                                if record.status == "CANCELLED"
                                else "DPM_WAVE_SIMULATION_WORKER_FAILURE"
                            )
                        ],
                        "diagnostics": {
                            **item.diagnostics,
                            "simulation_operation_id": record.operation_id,
                            "simulation_attempt_count": record.attempt_count,
                            "simulation_error": record.error_message,
                        },
                    },
                    deep=True,
                )
            )
        else:
            reconciled.append(item)
    return reconciled


def _operation_items_are_terminal(
    *, operation: DpmWaveSimulationOperation, items: list[DpmWaveSimulationItemRecord]
) -> bool:
    return all(
        item.status in {"SUCCEEDED", "CANCELLED"}
        or (
            item.status == "FAILED"
            and (not item.retryable or item.attempt_count >= operation.max_attempts)
        )
        for item in items
    )


def _all_simulation_items(
    *,
    tenant_id: str,
    operation_id: str,
    repository: DpmWaveSimulationRepository,
) -> list[DpmWaveSimulationItemRecord]:
    records: list[DpmWaveSimulationItemRecord] = []
    offset = 0
    while True:
        page = repository.list_simulation_items(
            tenant_id=tenant_id,
            operation_id=operation_id,
            limit=500,
            offset=offset,
        )
        records.extend(page.items)
        if page.next_offset is None:
            return records
        offset = page.next_offset


__all__ = [
    "admit_wave_simulation_operation",
    "cancel_wave_simulation_operation",
    "execute_wave_simulation_work",
    "get_wave_simulation_operation",
    "get_wave_simulation_results",
    "operation_counts",
    "reconcile_wave_simulation_operation",
    "retry_wave_simulation_operation",
]
