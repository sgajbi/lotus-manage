from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.api.dependencies import (
    get_construction_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.api.routers.wave_request_models import (
    DpmWaveSimulationCancelRequest,
    DpmWaveSimulationOperationRequest,
    DpmWaveSimulationRetryRequest,
    DpmWaveSimulationWorkRequest,
)
from src.api.routers.wave_response_contracts import (
    DpmWaveSimulationOperationResponse,
    DpmWaveSimulationOperationResultsResponse,
    DpmWaveSimulationWorkResponse,
    DpmWaveOperationProblemResponse,
)
from src.api.routers.wave_route_parameters import (
    WaveCorrelationIdHeader,
    WaveIdPath,
    WaveSimulationIdempotencyKeyHeader,
    WaveTenantIdHeader,
)
from src.api.routers.wave_simulation_operation_http import (
    simulation_operation_response,
    simulation_results_response,
)
from src.api.services import wave_simulation_operations
from src.api.services.authority_client_service import RiskAuthorityClient
from src.core.construction.repository import ConstructionRepository
from src.core.common.derived_identity import derived_identity
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves.simulation_repository import DpmWaveSimulationRepository

router = APIRouter()

_NOT_FOUND_RESPONSE = {
    "model": DpmWaveOperationProblemResponse,
    "description": "Wave or tenant-scoped simulation operation was not found.",
}
_CONFLICT_RESPONSE = {
    "model": DpmWaveOperationProblemResponse,
    "description": "Idempotency, correlation, or immutable admission input conflicts.",
}

OperationIdPath = Annotated[
    str,
    Path(description="Durable asynchronous wave-simulation operation identifier."),
]
ResultsLimitQuery = Annotated[int, Query(ge=1, le=200)]
ResultsOffsetQuery = Annotated[int, Query(ge=0)]


@router.post(
    "/{wave_id}/simulation-operations",
    response_model=DpmWaveSimulationOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Admit durable asynchronous wave simulation",
    description=(
        "Persists immutable item inputs and source identities before acceptance. Exact retries "
        "return the existing operation; conflicting reuse fails. Financial work is performed only "
        "by separately fenced worker calls and remains bounded by the persisted concurrency limit."
    ),
    responses={404: _NOT_FOUND_RESPONSE, 409: _CONFLICT_RESPONSE},
)
def admit_simulation_operation(
    wave_id: WaveIdPath,
    request: DpmWaveSimulationOperationRequest,
    idempotency_key: WaveSimulationIdempotencyKeyHeader,
    x_tenant_id: WaveTenantIdHeader,
    x_correlation_id: WaveCorrelationIdHeader = None,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
) -> DpmWaveSimulationOperationResponse:
    try:
        operation, replayed = wave_simulation_operations.admit_wave_simulation_operation(
            wave_id=wave_id,
            tenant_id=x_tenant_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id
            or derived_identity("corr_wave_async", x_tenant_id, idempotency_key),
            idempotency_key=idempotency_key,
            item_payloads=[item.model_dump(mode="json") for item in request.item_inputs],
            methods=request.methods,
            max_concurrency=request.max_concurrency,
            max_attempts=request.max_attempts,
            repository=repository,
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except DpmWaveValidationError as exc:
        raise wave_validation_http_exception(
            exc,
            conflict_codes=(
                "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT",
                "DPM_WAVE_SIMULATION_CORRELATION_CONFLICT",
                "DPM_WAVE_SIMULATION_WAVE_VERSION_CONFLICT",
                "DPM_WAVE_SIMULATION_TRANSITION_CONFLICT",
            ),
        ) from exc
    return simulation_operation_response(
        operation=operation,
        repository=repository,
        idempotent_replay=replayed,
    )


@router.get(
    "/simulation-operations/{operation_id}",
    response_model=DpmWaveSimulationOperationResponse,
    summary="Read durable wave-simulation progress",
    responses={404: _NOT_FOUND_RESPONSE},
)
def get_simulation_operation(
    operation_id: OperationIdPath,
    x_tenant_id: WaveTenantIdHeader,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
) -> DpmWaveSimulationOperationResponse:
    try:
        operation = wave_simulation_operations.get_wave_simulation_operation(
            tenant_id=x_tenant_id,
            operation_id=operation_id,
            repository=repository,
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    return simulation_operation_response(operation=operation, repository=repository)


@router.get(
    "/simulation-operations/{operation_id}/results",
    response_model=DpmWaveSimulationOperationResultsResponse,
    summary="Page stable wave-simulation item results",
    responses={404: _NOT_FOUND_RESPONSE},
)
def get_simulation_results(
    operation_id: OperationIdPath,
    x_tenant_id: WaveTenantIdHeader,
    limit: ResultsLimitQuery = 50,
    offset: ResultsOffsetQuery = 0,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
) -> DpmWaveSimulationOperationResultsResponse:
    try:
        operation, page = wave_simulation_operations.get_wave_simulation_results(
            tenant_id=x_tenant_id,
            operation_id=operation_id,
            limit=limit,
            offset=offset,
            repository=repository,
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return simulation_results_response(
        operation=operation,
        page=page,
        repository=repository,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/simulation-operations/{operation_id}/work",
    response_model=DpmWaveSimulationWorkResponse,
    summary="Execute a bounded fenced wave-simulation worker claim",
    responses={404: _NOT_FOUND_RESPONSE},
)
def execute_simulation_work(
    operation_id: OperationIdPath,
    request: DpmWaveSimulationWorkRequest,
    x_tenant_id: WaveTenantIdHeader,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: RiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmWaveSimulationWorkResponse:
    try:
        operation, claimed, completed, failed = (
            wave_simulation_operations.execute_wave_simulation_work(
                tenant_id=x_tenant_id,
                operation_id=operation_id,
                worker_id=request.worker_id,
                max_items=request.max_items,
                lease_seconds=request.lease_seconds,
                repository=repository,
                construction_repository=construction_repository,
                run_service=run_service,
                risk_authority_client=risk_authority_client,
            )
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return DpmWaveSimulationWorkResponse(
        operation=simulation_operation_response(
            operation=operation,
            repository=repository,
        ),
        claimed_count=claimed,
        completed_count=completed,
        failed_count=failed,
    )


@router.post(
    "/simulation-operations/{operation_id}/retry",
    response_model=DpmWaveSimulationOperationResponse,
    summary="Retry eligible failed wave-simulation items",
    responses={404: _NOT_FOUND_RESPONSE},
)
def retry_simulation_operation(
    operation_id: OperationIdPath,
    request: DpmWaveSimulationRetryRequest,
    x_tenant_id: WaveTenantIdHeader,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
) -> DpmWaveSimulationOperationResponse:
    try:
        operation, _ = wave_simulation_operations.retry_wave_simulation_operation(
            tenant_id=x_tenant_id,
            operation_id=operation_id,
            wave_item_ids=request.wave_item_ids,
            repository=repository,
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    return simulation_operation_response(operation=operation, repository=repository)


@router.post(
    "/simulation-operations/{operation_id}/cancel",
    response_model=DpmWaveSimulationOperationResponse,
    summary="Cancel unclaimed wave-simulation work",
    description=(
        "Pending work is cancelled immediately. Already claimed work retains its fence and may "
        "publish before lease expiry; completed financial artifacts are never deleted or relabelled."
    ),
    responses={404: _NOT_FOUND_RESPONSE},
)
def cancel_simulation_operation(
    operation_id: OperationIdPath,
    request: DpmWaveSimulationCancelRequest,
    x_tenant_id: WaveTenantIdHeader,
    repository: DpmWaveSimulationRepository = Depends(get_wave_repository),
) -> DpmWaveSimulationOperationResponse:
    try:
        operation = wave_simulation_operations.cancel_wave_simulation_operation(
            tenant_id=x_tenant_id,
            operation_id=operation_id,
            reason_code=request.reason_code,
            repository=repository,
        )
    except DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return simulation_operation_response(operation=operation, repository=repository)


__all__ = ["router"]
