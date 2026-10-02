"""Safe public projections for durable wave-simulation operations."""

from src.api.routers.wave_response_contracts import (
    DpmWaveSimulationOperationItemResponse,
    DpmWaveSimulationOperationResponse,
    DpmWaveSimulationOperationResultsResponse,
)
from src.core.waves.simulation_operations import (
    DpmWaveSimulationItemPage,
    DpmWaveSimulationItemRecord,
    DpmWaveSimulationOperation,
)
from src.core.waves.simulation_repository import DpmWaveSimulationRepository


def simulation_operation_response(
    *,
    operation: DpmWaveSimulationOperation,
    repository: DpmWaveSimulationRepository,
    idempotent_replay: bool = False,
) -> DpmWaveSimulationOperationResponse:
    counts = repository.simulation_item_counts(
        tenant_id=operation.tenant_id,
        operation_id=operation.operation_id,
    )
    return DpmWaveSimulationOperationResponse(
        operation_id=operation.operation_id,
        wave_id=operation.wave_id,
        correlation_id=operation.correlation_id,
        status=operation.status,
        request_hash=operation.request_hash,
        source_identity_hash=operation.source_identity_hash,
        admitted_wave_version=operation.admitted_wave_version,
        max_concurrency=operation.max_concurrency,
        max_attempts=operation.max_attempts,
        counts=counts,
        cancel_reason_code=operation.cancel_reason_code,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        idempotent_replay=idempotent_replay,
    )


def simulation_results_response(
    *,
    operation: DpmWaveSimulationOperation,
    page: DpmWaveSimulationItemPage,
    repository: DpmWaveSimulationRepository,
    limit: int,
    offset: int,
) -> DpmWaveSimulationOperationResultsResponse:
    return DpmWaveSimulationOperationResultsResponse(
        operation=simulation_operation_response(
            operation=operation,
            repository=repository,
        ),
        items=[_item_response(item) for item in page.items],
        limit=limit,
        offset=offset,
        returned_count=len(page.items),
        total_count=page.total_count,
        next_offset=page.next_offset,
    )


def _item_response(item: DpmWaveSimulationItemRecord) -> DpmWaveSimulationOperationItemResponse:
    result = item.result_item
    return DpmWaveSimulationOperationItemResponse(
        wave_item_id=item.wave_item_id,
        portfolio_id=item.portfolio_id,
        status=item.status,
        attempt_count=item.attempt_count,
        input_hash=item.input_hash,
        source_identity_hash=item.source_identity_hash,
        retryable=item.retryable,
        error_code=item.error_code,
        error_message=item.error_message,
        item_state=None if result is None else result.state,
        alternative_set_id=None if result is None else result.alternative_set_id,
    )


__all__ = ["simulation_operation_response", "simulation_results_response"]
