from __future__ import annotations

from src.api.request_models import RebalanceRequest
from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_request_models import DpmWaveSimulationRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.construction.repository import ConstructionRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmWaveRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def build_wave_simulation_item_inputs(
    request: DpmWaveSimulationRequest,
) -> dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput]:
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        simulation_input = wave_service.DpmWaveSimulationInput(
            stateless_input=item_input.stateless_input,
            authority_context=item_input.authority_context,
        )
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = simulation_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = simulation_input
    return item_inputs


def simulate_wave_response(
    *,
    wave_id: str,
    request: DpmWaveSimulationRequest,
    correlation_id: str,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
    risk_authority_client: LotusRiskAuthorityClient | None,
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.simulate_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            item_inputs=build_wave_simulation_item_inputs(request),
            methods=request.methods,
            construction_repository=construction_repository,
            run_service=run_service,
            wave_repository=wave_repository,
            risk_authority_client=risk_authority_client,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
