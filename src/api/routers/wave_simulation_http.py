from __future__ import annotations

from src.api.request_models import RebalanceRequest
from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_request_models import DpmWaveSimulationRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.api.services.wave_inputs.resolution import (
    freeze_wave_inputs,
    simulation_input_from_payload,
)
from src.api.services.rebalance_simulation_errors import DpmRebalanceEnvelopeError
from src.api.routers.rebalance_simulation_http import rebalance_envelope_http_exception
from src.api.services.wave_simulation_operations import _resolve_item_payloads
from src.core.integration_ports import RiskAuthorityClient
from src.core.construction.repository import ConstructionRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.rebalance.runtime_ports import RebalanceRuntime
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def build_wave_simulation_item_inputs(
    request: DpmWaveSimulationRequest,
    wave: DpmRebalanceWave | None = None,
    *,
    tenant_id: str | None = None,
    correlation_id: str = "",
    runtime: RebalanceRuntime | None = None,
) -> dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput]:
    if wave is not None:
        if wave.state != "SOURCE_CHECKED":
            return {}
        payloads = _resolve_item_payloads(
            wave=wave,
            item_payloads=[item.model_dump(mode="json") for item in request.item_inputs],
        )
        payloads = freeze_wave_inputs(
            runtime=runtime,
            wave=wave,
            item_inputs=payloads,
            tenant_id=tenant_id or "",
            correlation_id=correlation_id,
        )
        return {
            item_id: simulation_input_from_payload(payload) for item_id, payload in payloads.items()
        }
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        if item_input.stateless_input is None:
            raise wave_service.DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_SOURCE_SCOPE_REQUIRED",
                "Stateful input requires the persisted wave scope.",
            )
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
    tenant_id: str,
    risk_authority_client: RiskAuthorityClient | None,
    runtime: RebalanceRuntime | None = None,
) -> DpmWaveResponse:
    try:
        wave = wave_repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
        wave, replayed = wave_service.simulate_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            item_inputs=(
                build_wave_simulation_item_inputs(
                    request,
                    wave=wave,
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    runtime=runtime,
                )
                if wave is not None
                else {}
            ),
            methods=request.methods,
            construction_repository=construction_repository,
            run_service=run_service,
            wave_repository=wave_repository,
            tenant_id=tenant_id,
            risk_authority_client=risk_authority_client,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(
            exc,
            conflict_codes=(
                "DPM_WAVE_VERSION_CONFLICT",
                "DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT",
            ),
        ) from exc
    except DpmRebalanceEnvelopeError as exc:
        raise rebalance_envelope_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
